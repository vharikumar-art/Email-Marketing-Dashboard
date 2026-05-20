import requests
import os
from datetime import datetime, timedelta
from typing import Optional

EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/INR"

def get_inr_to_usd_rate() -> Optional[float]:
    """
    Fetch the current INR to USD exchange rate.
    
    Returns:
        float: The exchange rate (1 INR = ? USD)
        None: If the API call fails
    """
    try:
        print("[Currency] Fetching current INR to USD exchange rate...")
        response = requests.get(EXCHANGE_RATE_API_URL, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        rate = data.get("rates", {}).get("USD")
        
        if rate is None:
            print("❌ USD rate not found in API response")
            return None
        
        print(f"✅ Exchange rate fetched: 1 INR = {rate} USD")
        return rate
        
    except requests.exceptions.Timeout:
        print("❌ Exchange rate API timeout (5s)")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ Exchange rate API connection error")
        return None
    except Exception as e:
        print(f"❌ Error fetching exchange rate: {e}")
        return None


def convert_inr_to_usd(amount_inr: float) -> Optional[dict]:
    """
    Convert an amount from INR to USD using the current exchange rate.
    
    Args:
        amount_inr (float): Amount in Indian Rupees
        
    Returns:
        dict: {
            "amount_inr": float,
            "amount_usd": float,
            "rate": float,
            "timestamp": str
        }
        None: If exchange rate fetch fails
    """
    if amount_inr < 0:
        return None
    
    rate = get_inr_to_usd_rate()
    if rate is None:
        print(f"⚠️  Could not convert {amount_inr} INR to USD - rate unavailable")
        return None
    
    amount_usd = round(amount_inr * rate, 2)
    
    return {
        "amount_inr": amount_inr,
        "amount_usd": amount_usd,
        "rate": rate,
        "timestamp": datetime.utcnow().isoformat()
    }


def convert_usd_to_inr(amount_usd: float) -> Optional[dict]:
    """
    Convert an amount from USD to INR using the current exchange rate.
    
    Args:
        amount_usd (float): Amount in US Dollars
        
    Returns:
        dict: {
            "amount_usd": float,
            "amount_inr": float,
            "rate": float,
            "timestamp": str
        }
        None: If exchange rate fetch fails
    """
    if amount_usd < 0:
        return None
    
    rate = get_inr_to_usd_rate()
    if rate is None:
        print(f"⚠️  Could not convert {amount_usd} USD to INR - rate unavailable")
        return None
    
    amount_inr = round(amount_usd / rate, 2)
    
    return {
        "amount_usd": amount_usd,
        "amount_inr": amount_inr,
        "rate": rate,
        "timestamp": datetime.utcnow().isoformat()
    }


def get_current_rate_info() -> Optional[dict]:
    """
    Get current exchange rate information without conversion.
    
    Returns:
        dict: {
            "rate": float,
            "from_currency": "INR",
            "to_currency": "USD",
            "timestamp": str
        }
    """
    rate = get_inr_to_usd_rate()
    if rate is None:
        return None
    
    return {
        "rate": rate,
        "from_currency": "INR",
        "to_currency": "USD",
        "timestamp": datetime.utcnow().isoformat()
    }
