"""
Part 2: Authentication API
==========================
HID Origo OAuth2 Client Credentials Flow

This module handles obtaining and managing Bearer tokens for API access.

Key Concepts:
- OAuth2 client_credentials grant type
- Tokens expire after 3600 seconds (1 hour)
- Tokens become invalid after 5 minutes of inactivity
- All API calls require: Authorization, Application-ID, Application-Version headers
"""
import time
import requests
from dataclasses import dataclass
from typing import Optional

from ..utils.config import config


@dataclass
class TokenResponse:
    """OAuth2 token response from HID Origo"""
    access_token: str
    token_type: str
    expires_in: int
    id_token: Optional[str] = None
    obtained_at: float = 0

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expired (with buffer for safety)"""
        if not self.obtained_at:
            return True
        elapsed = time.time() - self.obtained_at
        return elapsed >= (self.expires_in - buffer_seconds)


class OrigoAuth:
    """
    HID Origo Authentication Client

    Usage:
        auth = OrigoAuth()
        auth.authenticate()
        headers = auth.get_headers()
    """

    def __init__(
        self,
        organization_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        base_url: str = None
    ):
        self.organization_id = organization_id or config.organization_id
        self.client_id = client_id or config.client_id
        self.client_secret = client_secret or config.client_secret
        self.base_url = base_url or config.base_url
        self._token: Optional[TokenResponse] = None

    @property
    def token_endpoint(self) -> str:
        """Construct the OAuth2 token endpoint URL"""
        return f"{self.base_url}/authentication/customer/{self.organization_id}/token"

    def authenticate(self) -> TokenResponse:
        """
        Authenticate using OAuth2 Client Credentials flow

        POST /authentication/customer/{organization_id}/token
        Content-Type: application/x-www-form-urlencoded

        Body:
            client_id: System Account identifier
            client_secret: System Account credential
            grant_type: client_credentials

        Returns:
            TokenResponse with access_token, token_type, expires_in
        """
        print(f"\n{'='*60}")
        print("STEP 1: OAuth2 Authentication")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.token_endpoint}")

        # Request body - form-urlencoded (NOT JSON!)
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }

        print(f"\nRequest Body (form-urlencoded):")
        print(f"  client_id: {self.client_id[:10]}..." if self.client_id else "  client_id: NOT SET")
        print(f"  client_secret: ********")
        print(f"  grant_type: client_credentials")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = requests.post(
                self.token_endpoint,
                data=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            self._token = TokenResponse(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
                id_token=data.get("id_token"),
                obtained_at=time.time()
            )

            print(f"\n✓ Authentication Successful!")
            print(f"  Token Type: {self._token.token_type}")
            print(f"  Expires In: {self._token.expires_in} seconds")
            print(f"  Access Token: {self._token.access_token[:20]}...")

            return self._token

        except requests.exceptions.RequestException as e:
            print(f"\n✗ Authentication Failed: {e}")
            raise

    def get_token(self) -> str:
        """Get current access token, refreshing if expired"""
        if not self._token or self._token.is_expired():
            self.authenticate()
        return self._token.access_token

    def get_headers(self, app_id: str = "acme-mobile-access", app_version: str = "1.0.0") -> dict:
        """
        Get headers required for all HID Origo API calls

        Required headers:
        - Authorization: Bearer {access_token}
        - Application-ID: Identifies your application
        - Application-Version: Your app version
        """
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Application-ID": app_id,
            "Application-Version": app_version,
            "Content-Type": "application/json"
        }


# =============================================================================
# DEMO: Simulated Authentication for Testing
# =============================================================================

class MockOrigoAuth(OrigoAuth):
    """
    Mock authentication for testing without real API credentials

    Use this when you don't have actual HID Origo credentials.
    """

    def authenticate(self) -> TokenResponse:
        """Simulate successful authentication"""
        print(f"\n{'='*60}")
        print("STEP 1: OAuth2 Authentication (SIMULATED)")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.token_endpoint}")

        print(f"\nRequest Body (form-urlencoded):")
        print(f"  client_id: demo-client-id")
        print(f"  client_secret: ********")
        print(f"  grant_type: client_credentials")

        # Simulate network delay
        time.sleep(0.5)

        # Create mock token
        self._token = TokenResponse(
            access_token="mock_access_token_" + "x" * 40,
            token_type="Bearer",
            expires_in=3600,
            id_token="mock_id_token_" + "y" * 40,
            obtained_at=time.time()
        )

        print(f"\n✓ Authentication Successful! (SIMULATED)")
        print(f"  Token Type: {self._token.token_type}")
        print(f"  Expires In: {self._token.expires_in} seconds")
        print(f"  Access Token: {self._token.access_token[:30]}...")

        return self._token


if __name__ == "__main__":
    # Demo the authentication flow
    print("\n" + "="*70)
    print("HID ORIGO AUTHENTICATION DEMO")
    print("="*70)

    auth = MockOrigoAuth(
        organization_id="demo-org-123",
        client_id="demo-client-id",
        client_secret="demo-secret"
    )
    auth.authenticate()

    headers = auth.get_headers()
    print(f"\nGenerated API Headers:")
    for key, value in headers.items():
        if "token" in value.lower() or "bearer" in value.lower():
            print(f"  {key}: {value[:40]}...")
        else:
            print(f"  {key}: {value}")
