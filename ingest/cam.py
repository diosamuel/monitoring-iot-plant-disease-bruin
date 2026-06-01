import os
import sys
import requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
from index import run_from_bytes

CAPTURE_URL = "http://192.168.1.30/capture"
resp = requests.get(CAPTURE_URL, timeout=30)
resp.raise_for_status()
temp = resp.content
print(f"Captured {len(temp)} bytes from {CAPTURE_URL}")
result = run_from_bytes(temp)
print(f"Done: {result.get('status')} - {result.get('filename')}")
