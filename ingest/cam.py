# Run this twice a day
import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
from index import runFromBinary

# CAPTURE_URL = "http://192.168.1.30/capture"
CAPTURE_URL = "http://localhost:3030/capture"

try:
    resp = requests.get(CAPTURE_URL, timeout=30)
    resp.raise_for_status()
    temp = resp.content
    if not temp:
        print(f"ERROR: Empty image received from {CAPTURE_URL}")
        sys.exit(0)
    print(f"Captured {len(temp)} bytes from {CAPTURE_URL}")
    result = runFromBinary(temp)
    print(
        f"Done: {result.get('status', 'unknown')} - "
        f"{result.get('filename', 'unknown')}"
    )

except requests.exceptions.Timeout:
    print(f"ERROR: Timeout while connecting to {CAPTURE_URL}")

except requests.exceptions.ConnectionError:
    print(f"ERROR: Cannot connect to {CAPTURE_URL}")

except requests.exceptions.HTTPError as e:
    print(f"ERROR: HTTP {e.response.status_code} from {CAPTURE_URL}")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(0)