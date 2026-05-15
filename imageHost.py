from fastapi import FastAPI, UploadFile, File
from datetime import datetime
import os
import uuid

app = FastAPI()

IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex
    filename = f"{timestamp}_{unique_id}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)
    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)
    print("Saved:", filepath)
    # TODO:
    # TensorFlow Lite inference here
    return {
        "status": "success",
        "filename": filename
    }

@app.get("/")
async def root():
    return {"message": "Hello World"}