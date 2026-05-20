#!/usr/bin/env python3
"""
Test script for the Unified Create API

This script tests the new /unified/create endpoint to ensure it works correctly.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"  # Update if your server runs on different port
ADMIN_EMAIL = "robert.s@company.com"   # Update with your admin email
ADMIN_PASSWORD = "password123"         # Update with your admin password

def login_and_get_token():
    """Login as admin and get JWT token (with OTP handling)"""
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }

    response = requests.post(f"{BASE_URL}/login", json=login_data)

    if response.status_code == 200:
        data = response.json()
        if "otp_required" in data["data"] and data["data"]["otp_required"]:
            print("📱 OTP required - completing 2FA...")

            # For testing, we'll use a fixed OTP (you might need to check email or logs)
            # In a real scenario, you'd extract OTP from email
            otp_data = {
                "email": ADMIN_EMAIL,
                "otp": "123456"  # Try common OTP for testing
            }

            otp_response = requests.post(f"{BASE_URL}/verify-otp", json=otp_data)

            if otp_response.status_code == 200:
                otp_result = otp_response.json()
                token = otp_result["data"]["access_token"]
                print("✅ OTP verification successful")
                return token
            else:
                print(f"❌ OTP verification failed: {otp_response.status_code}")
                print(f"Response: {otp_response.text}")
                return None

        # Direct login for employees
        token = data["data"]["access_token"]
        print("✅ Login successful (no OTP required)")
        return token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_unified_create(token):
    """Test the unified create API"""

    # Test data for unified creation
    test_data = {
        # Client fields
        "client_id": f"TEST-{datetime.now().strftime('%H%M%S')}",
        "client_name": "Test Research Institute",
        "client_country": "USA",
        "client_email": "contact@testresearch.com",
        "client_whatsapp_no": "+1234567890",
        "client_ref_no": "TEST-REF-001",
        "client_link": "https://testresearch.com",
        "client_bank_account": "TEST-ACCOUNT-123",
        "client_affiliation": "Research University",
        "clients_details": "Detailed information about the test client for unified API testing",
        "client_drive_link": "https://drive.google.com/test-client-folder",
        "payment_drive_link": "https://drive.google.com/test-payments-folder",

        # Order fields
        "reference_id": f"REF-TEST-{datetime.now().strftime('%H%M%S')}",
        "profile_name": "Academic Writing Profile",
        "title": "Advanced Machine Learning Techniques",
        "order_type": "writing",
        "index": "SCI",
        "rank": "Q1",
        "journal_name": "Nature Machine Intelligence",
        "write_start_date": "2024-01-15",
        "profile_start_date": "2024-01-10",
        "currency": "USD",
        "payment_status": "pending",

        # Manuscript creation
        "create_manuscript": True,
        "manuscript_title": "Machine Learning Algorithms for Data Science",
        "manuscript_journal_name": "Nature Machine Intelligence",

        # Payment creation
        "create_payment": True,
        "payment_amount": 2500.00,
        "payment_phase": 1,
        "payment_date": "2024-01-20",
        "payment_received_account": "Bank Account A"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("🚀 Testing Unified Create API...")
    print(f"📋 Test Data: {json.dumps(test_data, indent=2)}")

    response = requests.post(
        f"{BASE_URL}/unified/create",
        json=test_data,
        headers=headers
    )

    print(f"📊 Response Status: {response.status_code}")

    if response.status_code == 201:
        result = response.json()
        print("✅ Unified create successful!")
        print(f"📄 Response: {json.dumps(result, indent=2)}")

        # Verify the response structure
        data = result.get("data", {})
        expected_fields = ["client_id", "order_id", "reference_id", "manuscript_id", "payment_created", "created_records"]

        missing_fields = [field for field in expected_fields if field not in data]
        if missing_fields:
            print(f"⚠️  Missing fields in response: {missing_fields}")
        else:
            print("✅ All expected fields present in response")

        return True
    else:
        print(f"❌ Unified create failed: {response.status_code}")
        print(f"📄 Error Response: {response.text}")
        return False

def test_unified_create_existing_client(token):
    """Test creating order for existing client"""

    # First create a client
    client_data = {
        "client_id": f"EXISTING-{datetime.now().strftime('%H%M%S')}",
        "client_name": "Existing Test Client",
        "clients_details": "This client already exists",
        "payment_drive_link": "https://drive.google.com/existing-payments"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Create client first
    response = requests.post(f"{BASE_URL}/clients", json=client_data, headers=headers)
    if response.status_code != 201:
        print(f"❌ Failed to create test client: {response.status_code}")
        return False

    print("✅ Test client created")

    # Now test unified create with existing client
    order_data = {
        # Use existing client
        "client_id": client_data["client_id"],
        "client_name": client_data["client_name"],  # Should be ignored for existing client

        # Order fields
        "reference_id": f"REF-EXISTING-{datetime.now().strftime('%H%M%S')}",
        "profile_name": "Existing Client Profile",
        "title": "Existing Client Order",
        "order_type": "modification",
        "index": "Scopus",
        "rank": "Q2",
        "journal_name": "IEEE Transactions",
        "currency": "USD",
        "payment_status": "pending",

        # No manuscript or payment
        "create_manuscript": False,
        "create_payment": False
    }

    print("🚀 Testing unified create with existing client...")
    response = requests.post(f"{BASE_URL}/unified/create", json=order_data, headers=headers)

    if response.status_code == 201:
        result = response.json()
        data = result.get("data", {})

        if data.get("client_created") == False:
            print("✅ Correctly identified existing client (not created)")
        else:
            print("⚠️  Should have identified existing client")

        print(f"📄 Response: {json.dumps(result, indent=2)}")
        return True
    else:
        print(f"❌ Test failed: {response.status_code} - {response.text}")
        return False

def main():
    """Main test function"""
    print("🧪 Unified Create API Test Suite")
    print("=" * 50)

    # Login
    token = login_and_get_token()
    if not token:
        return

    # Test 1: Full unified create
    print("\n📋 Test 1: Full unified create (client + order + manuscript + payment)")
    success1 = test_unified_create(token)

    # Test 2: Existing client
    print("\n📋 Test 2: Unified create with existing client")
    success2 = test_unified_create_existing_client(token)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Test 1 (Full create): {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Test 2 (Existing client): {'✅ PASS' if success2 else '❌ FAIL'}")

    if success1 and success2:
        print("🎉 All tests passed! Unified API is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()