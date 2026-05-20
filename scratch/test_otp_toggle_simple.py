import requests

BASE_URL = "http://127.0.0.1:8002"
login_data = {"email": "admin@dashboard.com", "password": "Admin@123"}

try:
    print("Testing with OTP Enabled...")
    # Enable OTP
    res = requests.post(f"{BASE_URL}/toggle-otp?enabled=true")
    print("Toggle OTP True:", res.json())
    
    # Check status
    res = requests.get(f"{BASE_URL}/otp-status")
    print("OTP Status:", res.json())
    
    # Attempt login
    res = requests.post(f"{BASE_URL}/login", json=login_data)
    login_res = res.json()
    print("Login response when OTP is True:", login_res)
    
    # Verify that otp_required is True
    assert login_res.get("data", {}).get("otp_required") is True, "Failed: OTP should be required!"
    print("Passed: OTP required matches expected behavior")
    
    print("\nTesting with OTP Disabled...")
    # Disable OTP
    res = requests.post(f"{BASE_URL}/toggle-otp?enabled=false")
    print("Toggle OTP False:", res.json())
    
    # Check status
    res = requests.get(f"{BASE_URL}/otp-status")
    print("OTP Status:", res.json())
    
    # Attempt login
    res = requests.post(f"{BASE_URL}/login", json=login_data)
    login_res = res.json()
    print("Login response when OTP is False:", login_res)
    
    # Verify that access_token is present and otp_required is False
    assert login_res.get("data", {}).get("otp_required") is False, "Failed: OTP should not be required!"
    assert login_res.get("data", {}).get("access_token") is not None, "Failed: access_token should be present!"
    print("Passed: Bypassed OTP and generated token successfully")
    print("ALL TESTS PASSED SUCCESSFULLY!")

except Exception as e:
    print("Test failed with exception:", str(e))
