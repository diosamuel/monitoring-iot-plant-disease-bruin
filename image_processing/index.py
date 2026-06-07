# capture image on localhost:3001
# save to images/ folder
# save to google cloud bucket

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
from google.cloud import storage
from google.oauth2 import service_account

# Config
IMAGE_DIR = "image_processing/images"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
WIDTH_SIZE = 1024
HEIGHT_SIZE = 1024
IMAGE_LOG_PATH = f"sources/image-log.jsonl"
IMAGE_ANALYTICS_PATH = f"sources/image-analytics.jsonl"
GCS_BUCKET = os.getenv("GCS_BUCKET")
GCP_SERVICE_ACCOUNT_FILE = os.getenv("GCP_SERVICE_ACCOUNT_FILE")
creds = service_account.Credentials.from_service_account_file(
    GCP_SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
client = storage.Client(credentials=creds)


def uploadToGCS(filename: str, filepath: str):
    if not GCS_BUCKET:
        return None

    gcs_uri = f"gs://{GCS_BUCKET}/{filename}"
    try:
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(filename)
        blob.upload_from_filename(filepath, content_type="image/jpeg")
        print(f"[GCS] Uploaded: {gcs_uri}")
        return gcs_uri
    except Exception as exc:
        print(f"[GCS] Upload failed for {filename}: {exc}", file=sys.stderr)
        return None


def saveImage(raw_bytes: bytes):
    processed = preprocessImage(raw_bytes)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex
    filename = f"{timestamp}_{unique_id}.jpg"
    filepath = f"{IMAGE_DIR}/{filename}"
    os.makedirs(IMAGE_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(processed)
    print(f"Saved: {filepath} ({len(processed)} bytes)")
    return filename, filepath


def loggingImage(filename: str, event_time: datetime, gcs_uri: str | None = None):
    row = {
        "filename": filename,
        "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if gcs_uri:
        row["gcs_uri"] = gcs_uri
    with open(IMAGE_LOG_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"Logged to {IMAGE_LOG_PATH}")


def predict(filename: str, filepath: str):
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY not set")
        return {"status": "error", "detail": "GEMINI_API_KEY not set"}

    with open(filepath, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=GEMINI_API_KEY)
    with open("image_processing/system_prompt.txt", "r") as f:
        PREDICT_PROMPT = f.read()
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

    print(f"Prediction saved to {IMAGE_ANALYTICS_PATH}")
    return result


def run(image_path: str):
    with open(image_path, "rb") as f:
        raw = f.read()

    filename, filepath = saveImage(raw)
    gcs_uri = uploadToGCS(filename, filepath)
    event_time = datetime.now()
    loggingImage(filename, event_time, gcs_uri)
    result = predict(filename, filepath)
    return result


def runFromBinary(raw: bytes):
    filename, filepath = saveImage(raw)
    gcs_uri = uploadToGCS(filename, filepath)
    event_time = datetime.now()
    loggingImage(filename, event_time, gcs_uri)
    result = predict(filename, filepath)
    return result
