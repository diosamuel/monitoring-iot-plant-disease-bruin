"""
System Architecture Flow

Services:

* `localhost:5000` -> FastAPI backend API
  * Endpoint:
    * `/predict` -> run prediction/inference
* `localhost:5173/capture` -> image capture source
  * returns camera image in JPG format

Pipeline Flow:

1. Request image from `localhost:5173/capture`.
2. Preprocess image using `api.preprocess.image`.
3. Save the processed image into the `images/` directory.
4. Send the saved image to `localhost:5000/predict`.
5. Prediction endpoint performs inference and returns prediction result.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime

import requests

# Make `from preprocess.image import preprocessImage` resolvable from this
# script (the api/ folder is not a Python package, so we put it on sys.path).
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_DIR = os.path.join(ROOT_DIR, "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from preprocess.image import preprocessImage  # noqa: E402

# --- configuration ----------------------------------------------------------
CAPTURE_URL = os.getenv("CAPTURE_URL", "http://localhost:5173/capture")
PREDICT_URL = os.getenv("PREDICT_URL", "http://localhost:5000/predict")

# The /predict endpoint reads files from `<api>/images/<filename>`, so we
# write the processed image into that exact directory.
IMAGE_DIR = os.getenv("IMAGE_DIR", os.path.join(API_DIR, "images"))

REQUEST_TIMEOUT = float(os.getenv("PIPELINE_TIMEOUT", "30"))


def captureImage() -> bytes:
    """Fetch a JPG frame from the capture service."""
    print(f"[1/4] GET {CAPTURE_URL}")
    resp = requests.get(CAPTURE_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    if not resp.content:
        raise RuntimeError("Capture service returned an empty body.")
    return resp.content


def saveImage(processed: bytes) -> tuple[str, str]:
    """Persist the processed image into IMAGE_DIR. Returns (filename, filepath)."""
    os.makedirs(IMAGE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex
    filename = f"{timestamp}_{unique_id}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(processed)
    print(f"[3/4] Saved {len(processed)} bytes -> {filepath}")
    return filename, filepath


def requestPrediction(filename: str) -> dict:
    """Call the FastAPI /predict endpoint with the saved filename."""
    print(f"[4/4] POST {PREDICT_URL}?payload={filename}")
    resp = requests.post(
        PREDICT_URL,
        params={"payload": filename},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def runPipeline() -> dict:
    raw = captureImage()
    print(f"[2/4] Preprocessing {len(raw)} bytes...")
    processed = preprocessImage(raw)
    filename, filepath = saveImage(processed)
    result = requestPrediction(filename)
    return {
        "filename": filename,
        "path": filepath,
        "bytes": len(processed),
        "prediction": result,
    }


if __name__ == "__main__":
    try:
        output = runPipeline()
        print(json.dumps(output, indent=2, ensure_ascii=False))
    except requests.HTTPError as exc:
        print(f"[ERROR] HTTP {exc.response.status_code}: {exc.response.text}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        sys.exit(1)
