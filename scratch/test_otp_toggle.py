import subprocess
import time
import requests
import sys

# Start the uvicorn server in a subprocess
server_process = subprocess.Popen(
    [r".venv\Scripts\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(3) # Wait for server to start

try:
    print("Testing with OTP Enabled...")
    # Enable OTP
    res = requests.post("http://127.0.0.1:8001/toggle-otp?enabled=true")
    print("Toggle OTP True:", res.json())
    
    # Check status
    res = requests.get("http://127.0.0.1:8001/otp-status")
    print("OTP Status:", res.json())
    
    # Attempt login
    login_data = {"email": "admin@dashboard.com", "password": "Admin@123"}
    res = requests.post("http://127.0.0.1:8001/login", json=login_data)
    login_res = res.json()
    print("Login response when OTP is True:", login_res)
    
    # Verify that otp_required is True
    assert login_res.get("data", {}).get("otp_required") is True, "Failed: OTP should be required!"
    print("✅ Passed: OTP required matches expected behavior")
    
    print("\nTesting with OTP Disabled...")
    # Disable OTP
    res = requests.post("http://127.0.0.1:8001/toggle-otp?enabled=false")
    print("Toggle OTP False:", res.json())
    
    # Check status
    res = requests.get("http://127.0.0.1:8001/otp-status")
    print("OTP Status:", res.json())
    
    # Attempt login
    res = requests.post("http://127.0.0.1:8001/login", json=login_data)
    login_res = res.json()
    print("Login response when OTP is False:", login_res)
    
    # Verify that access_token is present and otp_required is False
    assert login_res.get("data", {}).get("otp_required") is False, "Failed: OTP should not be required!"
    assert login_res.get("data", {}).get("access_token") is not None, "Failed: access_token should be present!"
    print("✅ Passed: Bypassed OTP and generated token successfully")
    
finally:
    # Terminate the server
    server_process.terminate()
    server_process.wait()
    print("Test server terminated.")
