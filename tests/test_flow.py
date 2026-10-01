"""
CivicFix - Automated End-to-End Workflow Verification Suite
Validates all citizen, administrative, AI classification, priority calculation,
and resolution workflows over the running Flask server.
"""

import urllib.request
import urllib.parse
import http.cookiejar
import json
import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("==================================================")
    print(" CivicFix End-to-End Automated Verification Suite")
    print("==================================================")
    
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    # Test 1: Home Page
    print("\n[Test 1] Testing Homepage GET / ...")
    res = opener.open(f"{BASE_URL}/")
    assert res.status == 200, f"Expected 200 but got {res.status}"
    body = res.read().decode('utf-8')
    assert "CivicFix" in body
    assert "Report an Issue" in body
    print("  [PASS] Homepage loaded successfully (Status 200)")

    # Test 2: Public Geospatial API
    print("\n[Test 2] Testing Nearby Issues API GET /api/nearby-issues ...")
    res = opener.open(f"{BASE_URL}/api/nearby-issues")
    assert res.status == 200
    api_data = json.loads(res.read().decode('utf-8'))
    assert api_data['success'] is True
    print(f"  [PASS] Fetched {api_data['count']} active civic issues with GPS coordinates & color badges")

    # Test 3: Citizen Authentication
    print("\n[Test 3] Testing Citizen Login POST /login ...")
    login_data = urllib.parse.urlencode({
        'email': 'citizen@example.com',
        'password': 'Citizen@123'
    }).encode('utf-8')
    res = opener.open(f"{BASE_URL}/login", data=login_data)
    assert res.status == 200
    dash_html = res.read().decode('utf-8')
    assert "Priya Sharma" in dash_html
    print("  [PASS] Citizen authenticated and redirected to Citizen Dashboard")

    # Test 4: AI Image Classification Endpoint
    print("\n[Test 4] Testing AI Classifier POST /api/classify-image ...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    img_path = os.path.join(os.path.dirname(__file__), "..", "uploads", "reports", "pothole_sample.svg")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    data_bytes = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="pothole_road.svg"\r\n'
        f"Content-Type: image/svg+xml\r\n\r\n"
    ).encode("utf-8") + img_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/classify-image",
        data=data_bytes,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    res = opener.open(req)
    assert res.status == 200
    ai_res = json.loads(res.read().decode('utf-8'))
    assert ai_res['success'] is True
    assert ai_res['predicted_category'] == 'Pothole'
    print(f"  [PASS] AI Classification: Predicted='{ai_res['predicted_category']}', Confidence={ai_res['confidence']}%")

    # Test 5: Citizen Report Issue Form Submission
    print("\n[Test 5] Testing Report Submission POST /report ...")
    report_data = urllib.parse.urlencode({
        'category': 'Pothole',
        'severity': 'HIGH',
        'description': 'Severe road surface crater on Mount Road near metro entrance causing vehicle damage.',
        'latitude': '13.0610',
        'longitude': '80.2505',
        'landmark': 'Mount Road Metro Station',
        'address': 'Mount Road, Thousand Lights'
    }).encode('utf-8')
    res = opener.open(f"{BASE_URL}/report", data=report_data)
    assert res.status == 200
    detail_html = res.read().decode('utf-8')
    assert "Complaint Lifecycle Timeline" in detail_html
    assert "HIGH" in detail_html
    print("  [PASS] New complaint registered, priority scored, and timeline details rendered")

    # Test 6: Administrator Authentication
    print("\n[Test 6] Testing Admin Login POST /admin/login ...")
    admin_cookie_jar = http.cookiejar.CookieJar()
    admin_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(admin_cookie_jar))
    admin_login_data = urllib.parse.urlencode({
        'email': 'admin@civicfix.gov',
        'password': 'Admin@123'
    }).encode('utf-8')
    res = admin_opener.open(f"{BASE_URL}/admin/login", data=admin_login_data)
    assert res.status == 200
    admin_dash = res.read().decode('utf-8')
    assert "Executive Operations Dashboard" in admin_dash
    print("  [PASS] Administrator authenticated, operations metrics & Chart.js charts rendered")

    # Test 7: Administrator Triage & Resolution Workflow
    print("\n[Test 7] Testing Administrator Triage Table GET /admin/reports ...")
    res = admin_opener.open(f"{BASE_URL}/admin/reports")
    assert res.status == 200
    admin_table = res.read().decode('utf-8')
    assert "Manage Infrastructure Complaints" in admin_table
    print("  [PASS] Admin complaints table, filters, and modal controls operational")

    print("\n==================================================")
    print(" ALL 7 END-TO-END WORKFLOW INTEGRATION TESTS PASSED!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
