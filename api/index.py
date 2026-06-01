"""
Plant image processing and prediction pipeline.
Flow:
1. Read image from disk (or receive as bytes)
2. Preprocess (resize, compress)
3. Save processed image to api/images/
4. Upload to GCS bucket (if GCS_BUCKET is configured)
5. Log to sources/image-log.jsonl
6. Send to Gemini for prediction
7. Save result to sources/image-analytics.jsonl
"""

import json
import os
import sys
import uuid
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv
from google import genai
from google.genai import types
from preprocess.image import preprocessImage

load_dotenv()

# Config
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "images")
SOURCES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "sources"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
WIDTH_SIZE = 1024
HEIGHT_SIZE = 1024
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
with open(PROMPT_PATH, "r") as f:
    PREDICT_PROMPT = f.read()
IMAGE_LOG_PATH = os.path.join(SOURCES_DIR, "image-log.jsonl")
IMAGE_ANALYTICS_PATH = os.path.join(SOURCES_DIR, "image-analytics.jsonl")

# GCS config — upload is skipped when GCS_BUCKET is not set
GCS_BUCKET = os.getenv("GCS_BUCKET", "")
GCS_PREFIX = os.getenv("GCS_PREFIX", "plant-images").rstrip("/")
GCP_SERVICE_ACCOUNT_FILE = os.getenv(
    "GCP_SERVICE_ACCOUNT_FILE",
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "secrets", "gcp-secrets.json")),
)


@lru_cache(maxsize=1)
def _gcs_client():
    """Lazy-initialise a GCS client using the service account file."""
    from google.cloud import storage
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        GCP_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return storage.Client(credentials=creds)


def upload_to_gcs(filename: str, filepath: str) -> str | None:
    """Upload a local image file to GCS.

    Returns the public GCS URI (`gs://bucket/prefix/filename`) on success,
    or `None` if GCS_BUCKET is not configured or the upload fails.
    """
    if not GCS_BUCKET:
        return None

    blob_name = f"{GCS_PREFIX}/{filename}" if GCS_PREFIX else filename
    gcs_uri = f"gs://{GCS_BUCKET}/{blob_name}"

    try:
        client = _gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(filepath, content_type="image/jpeg")
        print(f"[GCS] Uploaded: {gcs_uri}")
        return gcs_uri
    except Exception as exc:
        print(f"[GCS] Upload failed for {filename}: {exc}", file=sys.stderr)
        return None


def save_image(raw_bytes: bytes) -> tuple[str, str]:
    """Preprocess and save image. Returns (filename, filepath)."""
    processed = preprocessImage(raw_bytes)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex
    filename = f"{timestamp}_{unique_id}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    os.makedirs(IMAGE_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(processed)
    print(f"[1/4] Saved: {filepath} ({len(processed)} bytes)")
    return filename, filepath


def log_image(filename: str, event_time: datetime, gcs_uri: str | None = None):
    """Append image log entry to JSONL."""
    row = {
        "filename": filename,
        "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if gcs_uri:
        row["gcs_uri"] = gcs_uri
    with open(IMAGE_LOG_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[3/4] Logged to {IMAGE_LOG_PATH}")


def predict(filename: str, filepath: str) -> dict:
    """Send image to Gemini and return prediction result."""
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY not set")
        return {"status": "error", "detail": "GEMINI_API_KEY not set"}

    with open(filepath, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            PREDICT_PROMPT.format(x=WIDTH_SIZE, y=HEIGHT_SIZE),
        ],
    )

    result = {
        "status": "success",
        "filename": filename,
        "model": GEMINI_MODEL,
        "bytes": len(image_bytes),
        "response": response.text,
    }

    with open(IMAGE_ANALYTICS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")

    print(f"[4/4] Prediction saved to {IMAGE_ANALYTICS_PATH}")
    return result


def run(image_path: str):
    """Full pipeline: preprocess → upload → log → predict."""
    with open(image_path, "rb") as f:
        raw = f.read()

    filename, filepath = save_image(raw)
    gcs_uri = upload_to_gcs(filename, filepath)
    event_time = datetime.now()
    log_image(filename, event_time, gcs_uri)
    result = predict(filename, filepath)
    print(json.dumps(result, indent=2))
    return result


def run_from_bytes(raw: bytes):
    """Full pipeline from raw bytes (used by ingest/cam.py)."""
    filename, filepath = save_image(raw)
    gcs_uri = upload_to_gcs(filename, filepath)
    event_time = datetime.now()
    log_image(filename, event_time, gcs_uri)
    result = predict(filename, filepath)
    return result
