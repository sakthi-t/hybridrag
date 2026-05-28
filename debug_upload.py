"""
Debug upload - test presign and confirm flow
"""
import requests

BASE_URL = "http://localhost:5000"

# Login as admin
session = requests.Session()
resp = session.post(f"{BASE_URL}/auth/login", json={
    "email": "t.shakthi@gmail.com",
    "password": "adminpassword123"
})
print(f"Login: {resp.status_code}")
if resp.status_code != 200:
    print(f"Login failed: {resp.text}")
    exit(1)

# Test presign endpoint
print("\nTesting presign...")
resp = session.post(f"{BASE_URL}/api/uploads/presign", json={
    "filename": "test.pdf",
    "content_type": "application/pdf",
    "size_bytes": 1000000
})
print(f"Presign status: {resp.status_code}")
print(f"Response: {resp.text[:500] if resp.text else 'empty'}")

if resp.status_code == 200:
    data = resp.json()
    print(f"\n  upload_url: {data.get('upload_url', 'MISSING')[:80]}...")
    print(f"  object_key: {data.get('object_key', 'MISSING')}")
else:
    print(f"Presign failed!")
