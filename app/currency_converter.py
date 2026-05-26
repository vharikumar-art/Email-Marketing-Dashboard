import requests
import os
from datetime import datetime, timedelta
from typing import Optional
from app.cache import cache_manager

EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/INR"

DEFAULT_RATES = {
    "INR": 1.0,
    "USD": 0.0105,
    "CNY": 0.076,
    "AED": 0.039,
    "SAR": 0.039
}

def get_all_inr_rates() -> dict:
    """
    Fetch rates for USD, CNY, AED, SAR relative to INR.
    Uses caching (1 hour) to avoid unnecessary external API requests.
    """
    # Try to get from cache first
    cached_rates = cache_manager.get("exchange_rates:inr")
    if cached_rates:
        return cached_rates

    try:
        print("[Currency] Fetching current exchange rates from API...")
        response = requests.get(EXCHANGE_RATE_API_URL, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        rates = data.get("rates", {})
        
        result = {
            "INR": 1.0,
            "USD": rates.get("USD", DEFAULT_RATES["USD"]),
            "CNY": rates.get("CNY", DEFAULT_RATES["CNY"]),
            "AED": rates.get("AED", DEFAULT_RATES["AED"]),
            "SAR": rates.get("SAR", DEFAULT_RATES["SAR"]),
        }
        
        # Cache the fetched rates for 1 hour (3600 seconds)
        cache_manager.set("exchange_rates:inr", result, ttl=3600)
        print(f"[Currency] Exchange rates fetched and cached: {result}")
        return result
        
    except Exception as e:
        print(f"[Currency] Error fetching rates: {e}. Using fallback rates.")
        return DEFAULT_RATES

def get_inr_to_usd_rate() -> Optional[float]:
    """
    Fetch the current INR to USD exchange rate.
    
    Returns:
        float: The exchange rate (1 INR = ? USD)
    """
    rates = get_all_inr_rates()
    return rates.get("USD")

def convert_currency(amount: float, from_curr: str, to_curr: str) -> Optional[dict]:
    """
    Convert amount from from_curr to to_curr using the current exchange rate.
    
    Args:
        amount (float): Amount to convert
        from_curr (str): Currency code to convert from (e.g. 'CNY')
        to_curr (str): Currency code to convert to (e.g. 'USD')
        
    Returns:
        dict: Conversion result details or None
    """
    if amount < 0:
        return None
        
    from_curr = from_curr.upper()
    to_curr = to_curr.upper()
    
    rates = get_all_inr_rates()
    if from_curr not in rates or to_curr not in rates:
        print(f"[Currency] Unsupported conversion: {from_curr} -> {to_curr}")
        return None
        
    rate_from = rates[from_curr]
    rate_to = rates[to_curr]
    
    # Calculate conversion rate: 1 from_curr = ? to_curr
    # 1 INR = rate_from from_curr => 1 from_curr = 1 / rate_from INR
    # 1 INR = rate_to to_curr => (1 / rate_from) INR = (1 / rate_from) * rate_to to_curr
    conversion_rate = rate_to / rate_from
    converted_amount = round(amount * conversion_rate, 2)
    
    return {
        "amount": amount,
        "from_currency": from_curr,
        "to_currency": to_curr,
        "converted_amount": converted_amount,
        "rate": round(conversion_rate, 6),
        "timestamp": datetime.utcnow().isoformat()
    }

def convert_inr_to_usd(amount_inr: float) -> Optional[dict]:
    """
    Convert an amount from INR to USD.
    """
    res = convert_currency(amount_inr, "INR", "USD")
    if not res:
        return None
    return {
        "amount_inr": amount_inr,
        "amount_usd": res["converted_amount"],
        "rate": res["rate"],
        "timestamp": res["timestamp"]
    }

def convert_usd_to_inr(amount_usd: float) -> Optional[dict]:
    """
    Convert an amount from USD to INR.
    """
    res = convert_currency(amount_usd, "USD", "INR")
    if not res:
        return None
    return {
        "amount_usd": amount_usd,
        "amount_inr": res["converted_amount"],
        "rate": res["rate"],
        "timestamp": res["timestamp"]
    }

def convert_cny_to_usd(amount_cny: float) -> Optional[dict]:
    """
    Convert CNY to USD.
    """
    return convert_currency(amount_cny, "CNY", "USD")

def convert_aed_to_usd(amount_aed: float) -> Optional[dict]:
    """
    Convert AED to USD.
    """
    return convert_currency(amount_aed, "AED", "USD")

def convert_sar_to_usd(amount_sar: float) -> Optional[dict]:
    """
    Convert SAR to USD.
    """
    return convert_currency(amount_sar, "SAR", "USD")

def get_current_rate_info() -> Optional[dict]:
    """
    Get current exchange rate information without conversion.
    """
    rates = get_all_inr_rates()
    usd_rate = rates.get("USD")
    if usd_rate is None:
        return None
    
    return {
        "rate": usd_rate,
        "from_currency": "INR",
        "to_currency": "USD",
        "rates": rates,
        "timestamp": datetime.utcnow().isoformat()
    }

