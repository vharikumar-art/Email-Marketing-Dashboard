# Testing the Unified Create API

## 🚀 Quick Start

1. **Start the server:**
   ```bash
   cd "d:\Email Dashboard"
   uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Get JWT Token (Login):**
   - Use Postman or curl to login first
   - Admin credentials: `robert.s@company.com` / `password123`
   - Copy the JWT token from the response

3. **Test the Unified API:**
   - Use the sample data from `sample_unified_api_request.json`
   - Or import the Postman collection: `postman_collection_unified_api.json`
   - Or use the curl examples in `curl_examples_unified_api.md`

## 📋 API Endpoint
```
POST /unified/create
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

## 📄 Sample Request Body
```json
{
  "client_id": "CL-TEST-001",
  "client_name": "Global Research Institute",
  "client_country": "USA",
  "client_email": "contact@globalresearch.edu",
  "clients_details": "Leading research institute...",
  "payment_drive_link": "https://drive.google.com/payments",

  "reference_id": "REF-GRI-2024-001",
  "profile_name": "Academic Writing Profile",
  "title": "Advanced Machine Learning Techniques",
  "order_type": "writing",
  "index": "SCI",
  "rank": "Q1",
  "journal_name": "Nature Machine Intelligence",
  "currency": "USD",
  "payment_status": "pending",

  "create_manuscript": true,
  "manuscript_title": "Machine Learning Algorithms",

  "create_payment": true,
  "payment_amount": 2500.00,
  "payment_phase": 1
}
```

## ✅ What Gets Created
- **Client record** (if client_id doesn't exist)
- **Order record** (always created)
- **Manuscript record** (if create_manuscript: true)
- **Payment record** (if create_payment: true)
- **Automatic relationships** maintained
- **payment_drive_link** flows from client to order

## 🔍 Response Example
```json
{
  "status_code": 201,
  "status": "success",
  "message": "Unified record created successfully",
  "data": {
    "client_id": "CL-TEST-001",
    "order_id": "ORD-2024-001",
    "reference_id": "REF-GRI-2024-001",
    "manuscript_id": "MS-CL-TEST-001-REF-GRI-2024-001",
    "payment_created": true,
    "client_created": true,
    "created_records": {
      "client": true,
      "order": true,
      "manuscript": true,
      "payment": true
    }
  }
}
```

## 🧪 Test Scenarios
1. **Full create**: Client + Order + Manuscript + Payment
2. **Existing client**: Order only for existing client
3. **Minimal**: Just client and basic order
4. **Error cases**: Duplicate reference_id, invalid client_id

## 📁 Files for Testing
- `sample_unified_api_request.json` - Single sample request
- `postman_collection_unified_api.json` - Postman collection
- `curl_examples_unified_api.md` - Curl command examples
- `test_unified_api.py` - Automated test script

Happy testing! 🎉