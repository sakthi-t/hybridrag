"""
Test the frontend pages and basic flow
"""
import requests

BASE_URL = "http://localhost:5000"

print("\n" + "="*60)
print("  FRONTEND TEST")
print("="*60)

# Test 1: Login page loads
print("\n1. Testing login page...")
try:
    resp = requests.get(f"{BASE_URL}/login")
    print(f"   Status: {resp.status_code}")
    if "RAG Threads" in resp.text and "Sign In" in resp.text:
        print("   [OK] Login page loads with expected content")
    else:
        print("   [WARN] Page loaded but expected content not found")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 2: Root redirects to login
print("\n2. Testing root redirect...")
try:
    resp = requests.get(f"{BASE_URL}/", allow_redirects=False)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 302:
        print(f"   [OK] Root redirects to: {resp.headers.get('Location')}")
    else:
        print("   [WARN] Expected redirect")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 3: Chat page requires auth
print("\n3. Testing chat page without auth...")
try:
    resp = requests.get(f"{BASE_URL}/chat", allow_redirects=False)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 302:
        print(f"   [OK] Chat redirects to login when not authenticated")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 4: Admin page requires auth
print("\n4. Testing admin page without auth...")
try:
    resp = requests.get(f"{BASE_URL}/admin", allow_redirects=False)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 302:
        print(f"   [OK] Admin redirects to login when not authenticated")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 5: Register test user
print("\n5. Registering test user (test@example.com)...")
session = requests.Session()
try:
    resp = session.post(f"{BASE_URL}/auth/register", json={
        "email": "test@example.com",
        "password": "mypassword123"
    })
    print(f"   Status: {resp.status_code}")
    data = resp.json()
    if resp.status_code == 201:
        print(f"   [OK] User registered: {data.get('user', {}).get('email')}")
    elif resp.status_code == 409:
        print("   [OK] User already exists (expected on re-run)")
        # Login instead
        resp = session.post(f"{BASE_URL}/auth/login", json={
            "email": "test@example.com",
            "password": "mypassword123"
        })
        if resp.status_code == 200:
            print("   [OK] Logged in instead")
    else:
        print(f"   [WARN] {data}")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 6: Access chat page when authenticated
print("\n6. Testing chat page with auth...")
try:
    resp = session.get(f"{BASE_URL}/chat")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200 and "chat-container" in resp.text:
        print("   [OK] Chat page loads for authenticated user")
    else:
        print("   [WARN] Chat page did not load as expected")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 7: Test user cannot access admin
print("\n7. Testing admin access for regular user...")
try:
    resp = session.get(f"{BASE_URL}/admin", allow_redirects=False)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 302:
        print("   [OK] Regular user redirected away from admin")
    elif resp.status_code == 200:
        print("   [WARN] Regular user could access admin page")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 8: Register admin user
print("\n8. Registering admin user (t.shakthi@gmail.com)...")
admin_session = requests.Session()
try:
    resp = admin_session.post(f"{BASE_URL}/auth/register", json={
        "email": "t.shakthi@gmail.com",
        "password": "adminpassword123"
    })
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 201:
        print("   [OK] Admin user registered")
    elif resp.status_code == 409:
        resp = admin_session.post(f"{BASE_URL}/auth/login", json={
            "email": "t.shakthi@gmail.com",
            "password": "adminpassword123"
        })
        if resp.status_code == 200:
            print("   [OK] Admin user logged in")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 9: Admin can access admin page
print("\n9. Testing admin access for admin user...")
try:
    resp = admin_session.get(f"{BASE_URL}/admin")
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200 and "admin-container" in resp.text:
        print("   [OK] Admin can access admin page")
    else:
        print("   [WARN] Admin could not access admin page")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 10: Admin API works
print("\n10. Testing admin API...")
try:
    resp = admin_session.get(f"{BASE_URL}/api/admin/users")
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"    [OK] Admin API works - {len(data.get('users', []))} users found")
except Exception as e:
    print(f"    [ERROR] {e}")

print("\n" + "="*60)
print("  TESTS COMPLETE")
print("="*60 + "\n")
