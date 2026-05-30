"""
Plant image processing and prediction pipeline.
Flow:
1. Read image from disk (or receive as bytes)
2. Preprocess (resize, compress)
3. Save processed image to api/images/
4. Log to sources/image-log.jsonl
5. Send to Gemini for prediction
6. Save result to sources/image-analytics.jsonl
"""

import json
import os
import sys
import uuid
from datetime import datetime
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
    print(f"[1/3] Saved: {filepath} ({len(processed)} bytes)")
    return filename, filepath


def log_image(filename: str, event_time: datetime):
    """Append image log entry to JSONL."""
    row = {
        "filename": filename,
        "event_time": event_time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(IMAGE_LOG_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[2/3] Logged to {IMAGE_LOG_PATH}")


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
        "path": filepath,
        "model": GEMINI_MODEL,
        "bytes": len(image_bytes),
        "response": response.text,
    }

    with open(IMAGE_ANALYTICS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")

    print(f"[3/3] Prediction saved to {IMAGE_ANALYTICS_PATH}")
    return result


def run(image_path: str):
    """Full pipeline: preprocess → log → predict."""
    with open(image_path, "rb") as f:
        raw = f.read()

    filename, filepath = save_image(raw)
    event_time = datetime.now()
    log_image(filename, event_time)
    result = predict(filename, filepath)
    print(json.dumps(result, indent=2))
    return result


def run_from_bytes(raw: bytes):
    """Full pipeline from raw bytes (used by ingest/cam.py)."""
    filename, filepath = save_image(raw)
    event_time = datetime.now()
    log_image(filename, event_time)
    result = predict(filename, filepath)
    return result
