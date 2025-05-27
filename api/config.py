import jwt
import secrets
from datetime import datetime, UTC, timedelta
import logging
from typing import Dict, Optional
import json
from pathlib import Path

# Constants
API_VERSION = "1.0.0"
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"
KEYS_FILE = CONFIG_DIR / "api_keys.json"

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self._config = {}
        self._keys = {}
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Create config directory if not exists"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        """Load configuration from files"""
        try:
            # Load main config
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    self._config = json.load(f)
            else:
                self._config = {
                    "api": {
                        "version": API_VERSION,
                        "host": "0.0.0.0",
                        "port": 8080,
                        "debug": True
                    },
                    "auth": {
                        "token_expire_minutes": 30,
                        "max_token_expire_minutes": 1440,  # 24 hours
                        "min_token_expire_minutes": 5
                    },
                    "default_user": "fdygg",
                    "created_at": datetime.now(UTC).isoformat()
                }
                self.save()

            # Load API keys
            if KEYS_FILE.exists():
                with open(KEYS_FILE, 'r') as f:
                    self._keys = json.load(f)
            
            logger.info(f"""
            Configuration loaded:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Config File: {CONFIG_FILE}
            Keys File: {KEYS_FILE}
            Version: {self._config['api']['version']}
            """)

        except Exception as e:
            logger.error(f"""
            Error loading configuration:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Error: {str(e)}
            """)
            raise

    def save(self):
        """Save configuration to files"""
        try:
            # Save main config
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)

            # Save API keys
            with open(KEYS_FILE, 'w') as f:
                json.dump(self._keys, f, indent=2)

            logger.debug(f"""
            Configuration saved:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Config File: {CONFIG_FILE}
            Keys File: {KEYS_FILE}
            """)

        except Exception as e:
            logger.error(f"""
            Error saving configuration:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Error: {str(e)}
            """)
            raise

    def create_access_token(self, username: str, api_key: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        try:
            # Get API secret
            key_data = self.get_api_key(username)
            if not key_data:
                raise ValueError(f"No API key found for user {username}")

            if expires_delta:
                expire = datetime.now(UTC) + expires_delta
            else:
                expire = datetime.now(UTC) + timedelta(minutes=self.token_expire_minutes)

            to_encode = {
                "sub": username,
                "api_key": api_key,
                "type": "access_token",
                "exp": expire,
                "iat": datetime.now(UTC),
                "nbf": datetime.now(UTC),
                "jti": secrets.token_hex(16),
                "ver": API_VERSION
            }

            encoded_jwt = jwt.encode(
                to_encode,
                key_data["api_secret"],
                algorithm="HS256"
            )

            return encoded_jwt

        except Exception as e:
            logger.error(f"""
            Error creating access token:
            Username: {username}
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            """)
            raise

    def get_api_key(self, username: str) -> Optional[Dict]:
        """Get API key data for user"""
        return self._keys.get(username)

    def verify_api_key(self, api_key: str, username: str) -> bool:
        """Verify API key belongs to user"""
        try:
            key_data = self.get_api_key(username)
            if not key_data:
                return False

            is_valid = key_data["api_key"] == api_key
            if is_valid:
                # Update last used timestamp
                key_data["last_used"] = datetime.now(UTC).isoformat()
                self.save()

            return is_valid

        except Exception as e:
            logger.error(f"""
            Error verifying API key:
            Username: {username}
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            """)
            return False

    def create_api_key(self, username: str) -> Dict[str, str]:
        """Create new API key for user"""
        try:
            api_key = f"gt_{secrets.token_urlsafe(32)}"
            api_secret = secrets.token_urlsafe(48)

            self._keys[username] = {
                "api_key": api_key,
                "api_secret": api_secret,
                "created_at": datetime.now(UTC).isoformat(),
                "last_used": None
            }
            
            self.save()

            logger.info(f"""
            Generated API key for {username}:
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Key: {api_key[:10]}...
            """)

            return {
                "api_key": api_key,
                "api_secret": api_secret
            }

        except Exception as e:
            logger.error(f"""
            Error creating API key:
            User: {username}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Error: {str(e)}
            """)
            raise

    @property
    def token_expire_minutes(self) -> int:
        return self._config["auth"]["token_expire_minutes"]

    @property
    def max_token_expire_minutes(self) -> int:
        return self._config["auth"]["max_token_expire_minutes"]

    @property
    def min_token_expire_minutes(self) -> int:
        return self._config["auth"]["min_token_expire_minutes"]

# Create global config instance
config = Config()

# Export config and API_VERSION
__all__ = ["config", "API_VERSION"]