"""
Configuration management for HID Origo Integration
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class OrigoConfig:
    """HID Origo API Configuration"""
    base_url: str = os.getenv("ORIGO_BASE_URL", "https://api.origo.hidglobal.com")
    organization_id: str = os.getenv("ORIGO_ORGANIZATION_ID", "")
    client_id: str = os.getenv("ORIGO_CLIENT_ID", "")
    client_secret: str = os.getenv("ORIGO_CLIENT_SECRET", "")

    # Callback settings
    callback_url: str = os.getenv("CALLBACK_URL", "")
    callback_secret: str = os.getenv("CALLBACK_SECRET", "")

    @property
    def auth_endpoint(self) -> str:
        """OAuth2 token endpoint"""
        return f"{self.base_url}/authentication/customer/{self.organization_id}/token"

    @property
    def user_endpoint(self) -> str:
        """User management base endpoint"""
        return f"{self.base_url}/user"

    @property
    def pass_endpoint(self) -> str:
        """Credential management (pass) base endpoint"""
        return f"{self.base_url}/pass"

    @property
    def callback_endpoint(self) -> str:
        """Callback registration endpoint"""
        return f"{self.base_url}/callback"


# Global config instance
config = OrigoConfig()
