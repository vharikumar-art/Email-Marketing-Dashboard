import requests

url = "https://api.exchangerate-api.com/v4/latest/INR"
response = requests.get(url)
data = response.json()
print("Base:", data.get("base"))
print("CNY:", data.get("rates", {}).get("CNY"))
print("AED:", data.get("rates", {}).get("AED"))
print("SAR:", data.get("rates", {}).get("SAR"))
print("USD:", data.get("rates", {}).get("USD"))
