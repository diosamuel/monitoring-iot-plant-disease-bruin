import os
import uuid
import duckdb
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from preprocess.image import preprocessImage

load_dotenv()
app = FastAPI()

# check folder
IMAGE_DIR = "images"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# DuckDB staging file that holds the image_log / image_analytics tables.
DEFAULT_DUCKDB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "sources", "stg_image.duckdb")
)
DUCKDB_PATH = os.getenv("STG_IMAGE_DUCKDB_PATH", DEFAULT_DUCKDB_PATH)

WIDTH_SIZE = 1024
HEIGHT_SIZE = 1024

with open("./system_prompt.txt","r") as f:
    PREDICT_PROMPT = f.read()

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def connectDuckDB():
    return duckdb.connect(DUCKDB_PATH)

def storeImage(filename, event_time):
    """Insert a new image entry into the image_log table in stg_image.duckdb."""
    try:
        con = connectDuckDB()
    except Exception as exc:
        print("[WARN] Could not open DuckDB at", DUCKDB_PATH, ":", exc)
        return {
            "status": "error",
            "detail": str(exc),
        }

    try:
        con.execute(
            """
            INSERT INTO image_log (filename, event_time)
            VALUES (?, ?);
            """,
            [filename, event_time],
        )
        return {
            "status": "success",
            "filename": filename,
            "event_time": event_time.isoformat(),
        }
    finally:
        con.close()

@app.get("/")
async def root():
    return {
        "message": "Hello from RaspberryPI 3B",
    }

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        processed = preprocessImage(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    upload_time = datetime.now()
    timestamp = upload_time.strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex
    filename = f"{timestamp}_{unique_id}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(processed)
    print("[OK] Saved:", filepath)

    log_result = storeImage(filename, upload_time)

    return {
        "status": "success",
        "filename": filename,
        "path": filepath,
        "bytes": len(processed),
        "image_log": log_result,
    }

@app.post("/predict")
async def predict(payload):
    if client is None:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set on the server."
        )

    filepath = os.path.join(IMAGE_DIR, payload)
    if not os.path.isfile(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"Image '{payload}' not found in {IMAGE_DIR}/"
        )

    with open(filepath, "rb") as f:
        processed = f.read()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=processed, mime_type="image/jpeg"),
                PREDICT_PROMPT.format(x=WIDTH_SIZE,y=HEIGHT_SIZE),
            ],
        )
        return {
            "status": "success",
            "filename": payload,
            "path": filepath,
            "model": GEMINI_MODEL,
            "bytes": len(processed),
            "response": response.text,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
