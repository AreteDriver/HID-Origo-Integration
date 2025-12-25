"""
Part 2: Credential Management API
=================================
HID Origo Pass and Credential Management

This module handles creating passes, generating issuance tokens,
and managing credential lifecycle (suspend, resume, delete).

Key Concepts:
- Pass: A digital badge container holding one or more credentials
- Pass Template: Defines credential types, artwork, platform settings
- Issuance Token: One-time password for secure provisioning to wallet
- Lifecycle: PENDING → ACTIVE → SUSPENDED → ACTIVE (or DELETED)
"""
import uuid
import time
import requests
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from ..utils.config import config
from .auth import OrigoAuth, MockOrigoAuth
from .users import User


class PassStatus(Enum):
    """Pass lifecycle states"""
    PENDING = "PENDING"           # Created, not yet provisioned
    PROVISIONING = "PROVISIONING" # Provisioning in progress
    ACTIVE = "ACTIVE"             # Successfully provisioned
    SUSPENDED = "SUSPENDED"       # Temporarily disabled
    CANCELLED = "CANCELLED"       # Deleted before activation
    DELETED = "DELETED"           # Removed after activation


@dataclass
class Pass:
    """
    HID Origo Pass model

    A Pass represents a digital badge that can be provisioned
    to Apple Wallet or Google Wallet.
    """
    user_id: str
    pass_template_id: str

    # Set by API response
    id: Optional[str] = None
    status: PassStatus = PassStatus.PENDING
    created: Optional[datetime] = None
    platform: Optional[str] = None  # "APPLE" or "GOOGLE"

    # Credential info
    credentials: List[Dict[str, Any]] = field(default_factory=list)

    def to_create_dict(self) -> Dict[str, Any]:
        """Convert to API request format for pass creation"""
        return {
            "userId": self.user_id,
            "passTemplateId": self.pass_template_id
        }

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Pass":
        """Create Pass from API response"""
        return cls(
            id=data.get("id"),
            user_id=data.get("userId", ""),
            pass_template_id=data.get("passTemplateId", ""),
            status=PassStatus(data.get("status", "PENDING")),
            platform=data.get("platform"),
            credentials=data.get("credentials", [])
        )


@dataclass
class IssuanceToken:
    """
    Issuance Token for wallet provisioning

    This is the one-time password that the mobile app/SDK uses
    to securely provision the credential to the wallet.

    CRITICAL SECURITY NOTE:
    - One-time use only
    - Short-lived (typically minutes)
    - Never log or store this token
    - Transmit only over secure channels
    """
    token: str
    expires_at: Optional[datetime] = None
    pass_id: Optional[str] = None

    def to_provisioning_dict(self) -> Dict[str, Any]:
        """Format for SDK initialization"""
        return {
            "issuanceToken": self.token,
            "passId": self.pass_id
        }


class CredentialManagementAPI:
    """
    HID Origo Credential Management API Client

    Tasks from Part 2:
    - Task 2: Create a pass with Credential Management API
    - Task 3: Generate the issuanceToken for the pass

    Usage:
        auth = OrigoAuth()
        auth.authenticate()
        creds_api = CredentialManagementAPI(auth)
        pass_obj = creds_api.create_pass(user_id, template_id)
        token = creds_api.get_issuance_token(pass_obj.id)
    """

    def __init__(self, auth: OrigoAuth, base_url: str = None):
        self.auth = auth
        self.base_url = (base_url or config.base_url).rstrip("/")

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/pass"

    def create_pass(self, user_id: str, pass_template_id: str) -> Pass:
        """
        Create a new pass for a user

        POST /pass
        Content-Type: application/json

        Body:
        {
            "userId": "<user-id>",
            "passTemplateId": "<template-id>"
        }

        This creates the pass and allocates credentials based on
        the pass template configuration.
        """
        print(f"\n{'='*60}")
        print("STEP 3: Create Pass (Credential Management API)")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.endpoint}")

        pass_obj = Pass(user_id=user_id, pass_template_id=pass_template_id)
        payload = pass_obj.to_create_dict()

        print(f"\nRequest Body:")
        print(f"  userId: {user_id}")
        print(f"  passTemplateId: {pass_template_id}")

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=self.auth.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            created_pass = Pass.from_api_response(data)
            print(f"\n✓ Pass Created Successfully!")
            print(f"  Pass ID: {created_pass.id}")
            print(f"  Status: {created_pass.status.value}")
            print(f"  User ID: {created_pass.user_id}")

            return created_pass

        except requests.exceptions.RequestException as e:
            print(f"\n✗ Pass Creation Failed: {e}")
            raise

    def get_pass(self, pass_id: str) -> Pass:
        """
        Get pass details

        GET /pass/{id}
        """
        response = requests.get(
            f"{self.endpoint}/{pass_id}",
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()
        return Pass.from_api_response(response.json())

    def get_issuance_token(self, pass_id: str) -> IssuanceToken:
        """
        Generate an issuance token for wallet provisioning

        GET /pass/{id}/issuanceToken

        This is the KEY step for mobile provisioning!

        The issuance token is:
        1. A one-time password
        2. Used by HID Mobile Access SDK
        3. Allows secure retrieval of provisioning data
        4. Short-lived - use immediately

        How it works in the provisioning flow:
        1. Backend calls this API to get token
        2. Token is sent to mobile app (via push, QR, deep link, etc.)
        3. Mobile app initializes HID SDK with the token
        4. SDK contacts Origo, retrieves credential data
        5. Credential is provisioned to Secure Element
        6. Pass appears in Apple/Google Wallet
        """
        print(f"\n{'='*60}")
        print("STEP 4: Generate Issuance Token (Credential Management API)")
        print(f"{'='*60}")
        print(f"Endpoint: GET {self.endpoint}/{pass_id}/issuanceToken")

        try:
            response = requests.get(
                f"{self.endpoint}/{pass_id}/issuanceToken",
                headers=self.auth.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            token = IssuanceToken(
                token=data.get("issuanceToken", data.get("token", "")),
                pass_id=pass_id
            )

            print(f"\n✓ Issuance Token Generated!")
            print(f"  Token: {token.token[:20]}... (truncated for security)")
            print(f"  Pass ID: {pass_id}")
            print(f"\n  ⚠️  IMPORTANT: This token is ONE-TIME USE ONLY!")
            print(f"  ⚠️  Do not log, store, or transmit insecurely!")

            return token

        except requests.exceptions.RequestException as e:
            print(f"\n✗ Token Generation Failed: {e}")
            raise

    # =========================================================================
    # Lifecycle Operations (Suspend, Resume, Delete)
    # =========================================================================

    def suspend_pass(self, pass_id: str) -> Pass:
        """
        Suspend a pass (temporarily disable)

        PATCH /pass/{id}
        Body: {"status": "SUSPENDED"}

        Use case: Employee on leave, lost device, security incident
        """
        print(f"\n{'='*60}")
        print("LIFECYCLE: Suspend Pass")
        print(f"{'='*60}")
        print(f"Endpoint: PATCH {self.endpoint}/{pass_id}")

        payload = {"status": "SUSPENDED"}

        response = requests.patch(
            f"{self.endpoint}/{pass_id}",
            json=payload,
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()

        print(f"✓ Pass suspended successfully")
        return Pass.from_api_response(response.json())

    def resume_pass(self, pass_id: str) -> Pass:
        """
        Resume a suspended pass

        PATCH /pass/{id}
        Body: {"status": "ACTIVE"}

        Use case: Employee returns from leave, device found
        """
        print(f"\n{'='*60}")
        print("LIFECYCLE: Resume Pass")
        print(f"{'='*60}")
        print(f"Endpoint: PATCH {self.endpoint}/{pass_id}")

        payload = {"status": "ACTIVE"}

        response = requests.patch(
            f"{self.endpoint}/{pass_id}",
            json=payload,
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()

        print(f"✓ Pass resumed successfully")
        return Pass.from_api_response(response.json())

    def delete_pass(self, pass_id: str) -> bool:
        """
        Delete a pass permanently

        DELETE /pass/{id}

        Use case: Employee termination, credential replacement
        """
        print(f"\n{'='*60}")
        print("LIFECYCLE: Delete Pass")
        print(f"{'='*60}")
        print(f"Endpoint: DELETE {self.endpoint}/{pass_id}")

        response = requests.delete(
            f"{self.endpoint}/{pass_id}",
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()

        print(f"✓ Pass deleted successfully")
        return True


# =============================================================================
# MOCK: Simulated API for Testing
# =============================================================================

class MockCredentialManagementAPI(CredentialManagementAPI):
    """Mock Credential Management API for testing"""

    def __init__(self, auth: MockOrigoAuth = None):
        self.auth = auth or MockOrigoAuth()
        self.base_url = "https://api.origo.hidglobal.com"
        self._passes: Dict[str, Pass] = {}

    def create_pass(self, user_id: str, pass_template_id: str) -> Pass:
        """Simulate pass creation"""
        print(f"\n{'='*60}")
        print("STEP 3: Create Pass (Credential Management API) - SIMULATED")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.endpoint}")

        print(f"\nRequest Body:")
        print(f"  {{")
        print(f'    "userId": "{user_id}",')
        print(f'    "passTemplateId": "{pass_template_id}"')
        print(f"  }}")

        time.sleep(0.3)

        # Generate mock pass
        pass_obj = Pass(
            id=f"pass-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            pass_template_id=pass_template_id,
            status=PassStatus.PENDING,
            created=datetime.utcnow(),
            credentials=[
                {
                    "type": "SEOS",
                    "id": f"cred-{uuid.uuid4().hex[:8]}"
                }
            ]
        )

        self._passes[pass_obj.id] = pass_obj

        print(f"\n✓ Pass Created Successfully! (SIMULATED)")
        print(f"  Pass ID: {pass_obj.id}")
        print(f"  Status: {pass_obj.status.value}")
        print(f"  User ID: {pass_obj.user_id}")
        print(f"  Template: {pass_obj.pass_template_id}")
        print(f"\nResponse (simulated):")
        print(f"  {{")
        print(f'    "id": "{pass_obj.id}",')
        print(f'    "userId": "{user_id}",')
        print(f'    "passTemplateId": "{pass_template_id}",')
        print(f'    "status": "PENDING",')
        print(f'    "credentials": [{{"type": "SEOS", "id": "..."}}]')
        print(f"  }}")

        return pass_obj

    def get_issuance_token(self, pass_id: str) -> IssuanceToken:
        """Simulate issuance token generation"""
        print(f"\n{'='*60}")
        print("STEP 4: Generate Issuance Token - SIMULATED")
        print(f"{'='*60}")
        print(f"Endpoint: GET {self.endpoint}/{pass_id}/issuanceToken")

        time.sleep(0.3)

        # Generate mock token (in reality, this is a cryptographically secure token)
        mock_token = f"IT_{uuid.uuid4().hex}"

        token = IssuanceToken(
            token=mock_token,
            pass_id=pass_id
        )

        print(f"\n✓ Issuance Token Generated! (SIMULATED)")
        print(f"\nResponse (simulated):")
        print(f"  {{")
        print(f'    "issuanceToken": "{token.token[:30]}..."')
        print(f"  }}")
        print(f"\n  ⚠️  IMPORTANT: This token is ONE-TIME USE ONLY!")
        print(f"\n" + "="*60)
        print("HOW THE ISSUANCE TOKEN IS USED:")
        print("="*60)
        print("""
        1. Backend generates this token via GET /pass/{id}/issuanceToken

        2. Token is sent to employee's mobile device via:
           - Push notification
           - QR code scan
           - Deep link / Universal link
           - Email (less secure)

        3. Mobile app (using HID Mobile Access SDK) initializes with token:

           // iOS (Swift)
           let manager = OrigoKeysManager.shared
           manager.provision(issuanceToken: "{token}") { result in
               switch result {
               case .success(let credential):
                   print("Credential provisioned!")
               case .failure(let error):
                   print("Provisioning failed: \\(error)")
               }
           }

           // Android (Kotlin)
           origoKeysManager.provision(issuanceToken) { result ->
               result.onSuccess { credential ->
                   Log.d("Origo", "Credential provisioned!")
               }
               result.onFailure { error ->
                   Log.e("Origo", "Failed: $error")
               }
           }

        4. SDK securely contacts HID Origo cloud to retrieve credential data

        5. Credential is written to device's Secure Element (SE)

        6. Pass appears in Apple Wallet / Google Wallet!

        7. Employee can now tap phone on NFC reader for building access
        """)

        return token

    def suspend_pass(self, pass_id: str) -> Pass:
        """Simulate pass suspension"""
        print(f"\n{'='*60}")
        print("LIFECYCLE: Suspend Pass - SIMULATED")
        print(f"{'='*60}")

        if pass_id in self._passes:
            self._passes[pass_id].status = PassStatus.SUSPENDED
            print(f"✓ Pass {pass_id} suspended")
            return self._passes[pass_id]
        raise ValueError(f"Pass not found: {pass_id}")

    def resume_pass(self, pass_id: str) -> Pass:
        """Simulate pass resume"""
        print(f"\n{'='*60}")
        print("LIFECYCLE: Resume Pass - SIMULATED")
        print(f"{'='*60}")

        if pass_id in self._passes:
            self._passes[pass_id].status = PassStatus.ACTIVE
            print(f"✓ Pass {pass_id} resumed")
            return self._passes[pass_id]
        raise ValueError(f"Pass not found: {pass_id}")

    def delete_pass(self, pass_id: str) -> bool:
        """Simulate pass deletion"""
        print(f"\n{'='*60}")
        print("LIFECYCLE: Delete Pass - SIMULATED")
        print(f"{'='*60}")

        if pass_id in self._passes:
            del self._passes[pass_id]
        print(f"✓ Pass {pass_id} deleted")
        return True


if __name__ == "__main__":
    # Demo the credential management flow
    print("\n" + "="*70)
    print("HID ORIGO CREDENTIAL MANAGEMENT DEMO")
    print("="*70)

    # Mock auth
    auth = MockOrigoAuth(
        organization_id="demo-org-123",
        client_id="demo-client-id",
        client_secret="demo-secret"
    )
    auth.authenticate()

    # Mock credential API
    creds_api = MockCredentialManagementAPI(auth)

    # Create a pass
    user_id = "usr-abc123"
    template_id = "tmpl-employee-badge-001"

    pass_obj = creds_api.create_pass(user_id, template_id)

    # Generate issuance token
    token = creds_api.get_issuance_token(pass_obj.id)

    # Demo lifecycle operations
    print("\n" + "="*70)
    print("LIFECYCLE OPERATIONS DEMO")
    print("="*70)

    creds_api.suspend_pass(pass_obj.id)
    creds_api.resume_pass(pass_obj.id)
    creds_api.delete_pass(pass_obj.id)
