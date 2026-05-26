import pytest
from unittest.mock import patch, MagicMock
from app.currency_converter import get_all_inr_rates, convert_currency, convert_cny_to_usd, convert_aed_to_usd, convert_sar_to_usd
from app.schemas import OrderBase, DashboardUpdate, UnifiedCreateRequest, CurrencyConvertRequest
from pydantic import ValidationError

def test_fallback_rates():
    # Force requests to raise an exception to test fallback behavior
    with patch("requests.get", side_effect=Exception("API Error")):
        rates = get_all_inr_rates()
        assert rates["USD"] == 0.012
        assert rates["CNY"] == 0.087
        assert rates["AED"] == 0.044
        assert rates["SAR"] == 0.045
        assert rates["INR"] == 1.0

def test_convert_currency():
    # Mock rates dictionary
    mock_rates = {
        "INR": 1.0,
        "USD": 0.012,
        "CNY": 0.087,
        "AED": 0.044,
        "SAR": 0.045
    }
    with patch("app.currency_converter.get_all_inr_rates", return_value=mock_rates):
        # Test CNY to USD conversion: 100 CNY
        # conversion_rate = rate_to / rate_from = 0.012 / 0.087 = 0.137931
        # converted = 100 * 0.137931 = 13.79
        res = convert_currency(100.0, "CNY", "USD")
        assert res is not None
        assert res["converted_amount"] == 13.79
        assert res["from_currency"] == "CNY"
        assert res["to_currency"] == "USD"

        # Test AED to USD: 100 AED
        # conversion_rate = 0.012 / 0.044 = 0.272727
        # converted = 100 * 0.272727 = 27.27
        res_aed = convert_aed_to_usd(100.0)
        assert res_aed is not None
        assert res_aed["converted_amount"] == 27.27

        # Test SAR to USD: 100 SAR
        # conversion_rate = 0.012 / 0.045 = 0.266667
        # converted = 100 * 0.266667 = 26.67
        res_sar = convert_sar_to_usd(100.0)
        assert res_sar is not None
        assert res_sar["converted_amount"] == 26.67

        # Test invalid currency
        assert convert_currency(100.0, "CAD", "USD") is None

def test_schema_validation():
    # Test valid currencies
    for curr in ["USD", "INR", "CNY", "AED", "SAR", "usd", "inr"]:
        req = CurrencyConvertRequest(amount=10.0, from_currency=curr, to_currency="USD")
        assert req.from_currency == curr.upper()

    # Test invalid currencies
    with pytest.raises(ValidationError):
        CurrencyConvertRequest(amount=10.0, from_currency="CAD", to_currency="USD")

    with pytest.raises(ValidationError):
        OrderBase(
            order_id="ORD-1",
            client_id="CL-1",
            currency="EURO"
        )
