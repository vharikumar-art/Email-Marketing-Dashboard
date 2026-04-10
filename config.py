import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 600))

# SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

# CORS Origins - Production Ready
# Comma-separated list. Strips trailing slashes to avoid common CORS errors.
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,https://marketing-dashboard-one-zeta.vercel.app")
ALLOWED_ORIGINS = [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]