import pytest
from unittest.mock import patch, MagicMock
from app.main import get_dashboard_orders

# 1. Mock dependency user
def mock_get_current_user():
    return {
        "email": "employee@company.com",
        "role": "employee",
        "full_name": "Jane Doe",
        "profile_names": ["Profile_A"]
    }

def test_dashboard_orders_usd_conversion():
    # 2. Mock exchange rates (1 INR = 0.012 USD, etc.)
    mock_rates = {
        "INR": 1.0,
        "USD": 0.012,
        "CNY": 0.087,
        "AED": 0.044,
        "SAR": 0.045
    }
    
    # 3. Mock MongoDB aggregation result
    mock_aggregation_data = [
        {
            "client_id": "CL-2026-0100",
            "name": "Test Client INR",
            "country": "India",
            "email": "inr@client.com",
            "whatsapp_no": "+919876543210",
            "currency": "INR",
            "total_amount": 1000.0,
            "paid_amount": 500.0,
            "order_id": "ORD-2026-001",
            "client_handler": "employee@company.com"
        },
        {
            "client_id": "CL-2026-0101",
            "name": "Test Client USD",
            "country": "USA",
            "email": "usd@client.com",
            "whatsapp_no": "+19876543210",
            "currency": "USD",
            "total_amount": 100.0,
            "paid_amount": 100.0,
            "order_id": "ORD-2026-002",
            "client_handler": "employee@company.com"
        }
    ]

    with patch("app.currency_converter.get_all_inr_rates", return_value=mock_rates), \
         patch("app.database.clients_collection.aggregate", return_value=mock_aggregation_data), \
         patch("app.database.users_collection.find", return_value=[]), \
         patch("app.database.clients_collection.find", return_value=[]):
        
        # Call the endpoint function directly
        result = get_dashboard_orders(current_user=mock_get_current_user())
        
        assert result["status_code"] == 200
        assert result["status"] == "success"
        
        orders = result["data"]
        assert len(orders) == 2
        
        # Verify first order (INR conversion: multiplier = 0.012)
        # total_amount_usd = 1000 * 0.012 = 12.0
        # paid_amount_usd = 500 * 0.012 = 6.0
        inr_order = next(o for o in orders if o["currency"] == "INR")
        assert inr_order["total_amount_usd"] == 12.0
        assert inr_order["paid_amount_usd"] == 6.0
        
        # Verify second order (USD conversion: multiplier = 1.0)
        # total_amount_usd = 100.0
        # paid_amount_usd = 100.0
        usd_order = next(o for o in orders if o["currency"] == "USD")
        assert usd_order["total_amount_usd"] == 100.0
        assert usd_order["paid_amount_usd"] == 100.0
