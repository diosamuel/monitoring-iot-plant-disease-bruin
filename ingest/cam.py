import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
from index import run_from_bytes

CAPTURE_URL = "https://earthsally.com/wp-content/uploads/2021/03/diseasebanner.jpg"

# Capture image as binary from ESP32-CAM
resp = requests.get(CAPTURE_URL, timeout=30)
resp.raise_for_status()
temp = resp.content

print(f"Captured {len(temp)} bytes from {CAPTURE_URL}")

# Process and predict
result = run_from_bytes(temp)
print(f"Done: {result.get('status')} - {result.get('filename')}")
