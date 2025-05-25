# api/config.py
import os
import hashlib
from datetime import datetime, UTC

def generate_permanent_keys(username: str, created_time: str):
    """Generate permanent API key dan secret yang unik"""
    base = f"{username}_{created_time}"
    
    # Generate API Key (hash pertama)
    api_key_hash = hashlib.sha256(base.encode()).hexdigest()
    api_key = f"{username}_" + api_key_hash[:8]
    
    # Generate Secret (hash kedua dengan salt khusus)
    salt = f"{username}_salt_{created_time[:4]}"  # Salt dari username dan tahun
    secret_hash = hashlib.sha256(f"{base}{salt}".encode()).hexdigest()
    secret_key = f"sk_{username}_" + secret_hash[:16]
    
    return api_key, secret_key

# Current settings
CURRENT_TIME = "2025-05-25 15:02:35"  # Sesuai waktu yang diberikan
CURRENT_USER = "fdyyuk"  # Sesuai login yang diberikan

# Generate API credentials
API_KEY, API_SECRET_KEY = generate_permanent_keys(CURRENT_USER, CURRENT_TIME)

class APIConfig:
    # Basic Info
    CURRENT_TIME = CURRENT_TIME
    CURRENT_USER = CURRENT_USER
    
    # API Credentials
    API_KEY = API_KEY
    API_SECRET_KEY = API_SECRET_KEY
    
    # Token Settings
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 jam untuk token akses
    JWT_ALGORITHM = "HS256"
    
    # API Version
    VERSION = "1.0.0"
    API_V1_PREFIX = "/api/v1"
    
    # Security Settings
    ALLOWED_HOSTS = ["*"]
    CORS_ORIGINS = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    
    # Rate Limiting
    RATE_LIMIT = 100  # requests per minute
    
    @classmethod
    def get_credentials(cls):
        """Method untuk melihat credentials (hanya untuk pemilik)"""
        return {
            "api_key": cls.API_KEY,
            "secret_key": cls.API_SECRET_KEY,
            "created_at": cls.CURRENT_TIME,
            "owner": cls.CURRENT_USER,
            "expires": "Never (Permanent Access)"
        }
    
    @classmethod
    def print_credentials(cls):
        """Print credentials dalam format yang mudah dibaca"""
        creds = cls.get_credentials()
        print("\n=== API Credentials ===")
        print(f"Owner: {creds['owner']}")
        print(f"Created: {creds['created_at']}")
        print(f"API Key: {creds['api_key']}")
        print(f"Secret Key: {creds['secret_key']}")
        print(f"Expires: {creds['expires']}")
        print("=====================\n")

# Inisialisasi config
config = APIConfig()

# Export variables yang dibutuhkan
__all__ = [
    "API_KEY",
    "API_SECRET_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "config"
]

if __name__ == "__main__":
    # Print credentials saat file dijalankan langsung
    config.print_credentials()