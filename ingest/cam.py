import requests

CAPTURE_URL = "http://localhost:3000/capture"
UPLOAD_URL = "http://localhost:8000/upload"

# Capture image as binary
resp = requests.get(CAPTURE_URL, timeout=30)
resp.raise_for_status()
temp = resp.content

# Post binary image to upload endpoint
upload_resp = requests.post(
    UPLOAD_URL,
    files={"file": ("capture.jpg", temp, "image/jpeg")},
    timeout=30,
)
upload_resp.raise_for_status()

print(f"Captured {len(temp)} bytes, uploaded: {upload_resp.status_code}")
