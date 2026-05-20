# Unified API Testing Examples

## 1. Login First (Get JWT Token)
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "robert.s@company.com",
    "password": "password123"
  }'
```

**Note**: If OTP is required, you'll need to complete the OTP verification first.

## 2. Full Unified Create (Client + Order + Manuscript + Payment)
```bash
curl -X POST "http://localhost:8000/unified/create" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "CL-TEST-001",
    "client_name": "Global Research Institute",
    "client_country": "USA",
    "client_email": "contact@globalresearch.edu",
    "client_whatsapp_no": "+1-555-0123",
    "client_ref_no": "GRI-2024-001",
    "client_link": "https://www.globalresearch.edu",
    "client_bank_account": "GRI-ACCOUNT-001",
    "client_affiliation": "International Research University",
    "clients_details": "Leading research institute specializing in AI and machine learning. Requires high-quality academic writing services for journal publications.",
    "client_drive_link": "https://drive.google.com/drive/folders/global-research-client",
    "payment_drive_link": "https://drive.google.com/drive/folders/global-research-payments",

    "reference_id": "REF-GRI-2024-001",
    "profile_name": "Academic Writing Profile - Dr. Smith",
    "title": "Advanced Machine Learning Techniques for Medical Diagnosis",
    "order_type": "writing",
    "index": "SCI",
    "rank": "Q1",
    "journal_name": "Nature Machine Intelligence",
    "write_start_date": "2024-01-15",
    "profile_start_date": "2024-01-10",
    "currency": "USD",
    "payment_status": "pending",

    "create_manuscript": true,
    "manuscript_title": "Machine Learning Algorithms for Healthcare Applications",
    "manuscript_journal_name": "Nature Machine Intelligence",

    "create_payment": true,
    "payment_amount": 2500.00,
    "payment_phase": 1,
    "payment_date": "2024-01-20",
    "payment_received_account": "Primary Bank Account"
  }'
```

## 3. Order Only for Existing Client
```bash
curl -X POST "http://localhost:8000/unified/create" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "CL-EXISTING-001",
    "client_name": "Existing Client Name",
    "reference_id": "REF-EXISTING-2024-002",
    "profile_name": "Standard Academic Profile",
    "title": "Data Analysis Methods in Social Sciences",
    "order_type": "modification",
    "index": "Scopus",
    "rank": "Q2",
    "journal_name": "Journal of Social Research",
    "currency": "USD",
    "payment_status": "pending",
    "create_manuscript": false,
    "create_payment": false
  }'
```

## 4. Minimal Order Creation
```bash
curl -X POST "http://localhost:8000/unified/create" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "CL-MINIMAL-001",
    "client_name": "Minimal Test Client",
    "reference_id": "REF-MINIMAL-001",
    "title": "Test Paper Title",
    "order_type": "writing",
    "journal_name": "Test Journal",
    "currency": "USD",
    "payment_status": "pending"
  }'
```

## Expected Response Format
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
    },
    "payment_drive_link_used": "https://drive.google.com/drive/folders/global-research-payments"
  }
}
```

## Key Features Tested:
- ✅ Client creation (if doesn't exist)
- ✅ Client update (if exists)
- ✅ Order creation with unique reference_id
- ✅ Manuscript creation (optional)
- ✅ Payment creation (optional)
- ✅ Automatic payment_drive_link inheritance from client
- ✅ Proper relationship management
- ✅ Error handling for duplicate reference_ids

## Files Created:
- `sample_unified_api_request.json` - Single sample request
- `postman_collection_unified_api.json` - Postman collection with multiple examples
- `curl_examples_unified_api.md` - This file with curl commands