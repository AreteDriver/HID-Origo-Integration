"""
Part 2: User Management API
===========================
HID Origo User Management using SCIM v2 standard

This module handles creating, reading, updating, and deleting users
that will be associated with mobile credentials.

Key Concepts:
- SCIM v2 (System for Cross-domain Identity Management)
- Users are required before passes can be issued
- External ID links corporate identity to Origo user
"""
import uuid
import time
import requests
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..utils.config import config
from .auth import OrigoAuth, MockOrigoAuth


@dataclass
class User:
    """
    HID Origo User model (SCIM v2 format)

    Required fields:
    - externalId: Your corporate user identifier (e.g., employee ID)
    - emails: At least one email address

    Optional fields:
    - displayName: Full name for display
    - name: Structured name (givenName, familyName)
    """
    external_id: str
    email: str
    display_name: str = ""
    given_name: str = ""
    family_name: str = ""

    # Set by API response
    id: Optional[str] = None
    created: Optional[datetime] = None
    last_modified: Optional[datetime] = None

    def to_scim_dict(self) -> Dict[str, Any]:
        """Convert to SCIM v2 request format"""
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "externalId": self.external_id,
            "displayName": self.display_name or f"{self.given_name} {self.family_name}".strip(),
            "name": {
                "givenName": self.given_name,
                "familyName": self.family_name
            },
            "emails": [
                {
                    "value": self.email,
                    "type": "work",
                    "primary": True
                }
            ]
        }

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "User":
        """Create User from API response"""
        emails = data.get("emails", [])
        email = emails[0]["value"] if emails else ""
        name = data.get("name", {})

        return cls(
            id=data.get("id"),
            external_id=data.get("externalId", ""),
            email=email,
            display_name=data.get("displayName", ""),
            given_name=name.get("givenName", ""),
            family_name=name.get("familyName", "")
        )


class UserManagementAPI:
    """
    HID Origo User Management API Client

    Task 1 from Part 2: Create a user with User Management API

    Usage:
        auth = OrigoAuth()
        auth.authenticate()
        users_api = UserManagementAPI(auth)
        user = users_api.create_user(User(...))
    """

    def __init__(self, auth: OrigoAuth, base_url: str = None):
        self.auth = auth
        self.base_url = (base_url or config.base_url).rstrip("/")

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/user"

    def create_user(self, user: User) -> User:
        """
        Create a new user in HID Origo

        POST /user
        Content-Type: application/json

        This is STEP 1 of the provisioning flow - you need a user
        before you can create a pass/credential for them.
        """
        print(f"\n{'='*60}")
        print("STEP 2: Create User (User Management API)")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.endpoint}")

        payload = user.to_scim_dict()
        print(f"\nRequest Body (SCIM v2 format):")
        print(f"  externalId: {user.external_id}")
        print(f"  displayName: {user.display_name}")
        print(f"  email: {user.email}")
        print(f"  givenName: {user.given_name}")
        print(f"  familyName: {user.family_name}")

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=self.auth.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            created_user = User.from_api_response(data)
            print(f"\n✓ User Created Successfully!")
            print(f"  User ID: {created_user.id}")
            print(f"  External ID: {created_user.external_id}")

            return created_user

        except requests.exceptions.RequestException as e:
            print(f"\n✗ User Creation Failed: {e}")
            raise

    def get_user(self, user_id: str) -> User:
        """
        Get user details by ID

        GET /user/{id}
        """
        print(f"\nGetting user: {user_id}")

        response = requests.get(
            f"{self.endpoint}/{user_id}",
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()
        return User.from_api_response(response.json())

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user (lifecycle operation)

        DELETE /user/{id}

        This will also invalidate any passes associated with the user.
        """
        print(f"\nDeleting user: {user_id}")

        response = requests.delete(
            f"{self.endpoint}/{user_id}",
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()
        print(f"✓ User deleted successfully")
        return True


# =============================================================================
# MOCK: Simulated API for Testing
# =============================================================================

class MockUserManagementAPI(UserManagementAPI):
    """Mock User Management API for testing without real credentials"""

    def __init__(self, auth: MockOrigoAuth = None):
        self.auth = auth or MockOrigoAuth()
        self.base_url = "https://api.origo.hidglobal.com"
        self._users: Dict[str, User] = {}

    def create_user(self, user: User) -> User:
        """Simulate user creation"""
        print(f"\n{'='*60}")
        print("STEP 2: Create User (User Management API) - SIMULATED")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.endpoint}")

        payload = user.to_scim_dict()
        print(f"\nRequest Body (SCIM v2 format):")
        print(f"  schemas: {payload['schemas']}")
        print(f"  externalId: {user.external_id}")
        print(f"  displayName: {user.display_name}")
        print(f"  email: {user.email}")
        print(f"  name.givenName: {user.given_name}")
        print(f"  name.familyName: {user.family_name}")

        # Simulate network delay
        time.sleep(0.3)

        # Generate mock ID
        user.id = f"usr-{uuid.uuid4().hex[:12]}"
        user.created = datetime.utcnow()
        user.last_modified = datetime.utcnow()

        self._users[user.id] = user

        print(f"\n✓ User Created Successfully! (SIMULATED)")
        print(f"  User ID: {user.id}")
        print(f"  External ID: {user.external_id}")
        print(f"\nResponse (simulated):")
        print(f"  {{")
        print(f'    "id": "{user.id}",')
        print(f'    "externalId": "{user.external_id}",')
        print(f'    "displayName": "{user.display_name}",')
        print(f'    "emails": [{{"value": "{user.email}", "primary": true}}]')
        print(f"  }}")

        return user

    def get_user(self, user_id: str) -> User:
        """Simulate getting user"""
        if user_id in self._users:
            return self._users[user_id]
        raise ValueError(f"User not found: {user_id}")

    def delete_user(self, user_id: str) -> bool:
        """Simulate user deletion"""
        print(f"\n{'='*60}")
        print("DELETE User (SIMULATED)")
        print(f"{'='*60}")
        print(f"Endpoint: DELETE {self.endpoint}/{user_id}")

        time.sleep(0.2)

        if user_id in self._users:
            del self._users[user_id]

        print(f"\n✓ User deleted successfully (SIMULATED)")
        return True


if __name__ == "__main__":
    # Demo the user management flow
    print("\n" + "="*70)
    print("HID ORIGO USER MANAGEMENT DEMO")
    print("="*70)

    # Create mock auth
    auth = MockOrigoAuth(
        organization_id="demo-org-123",
        client_id="demo-client-id",
        client_secret="demo-secret"
    )
    auth.authenticate()

    # Create mock user API
    users_api = MockUserManagementAPI(auth)

    # Create a test user
    new_user = User(
        external_id="EMP-12345",
        email="john.doe@acme.com",
        display_name="John Doe",
        given_name="John",
        family_name="Doe"
    )

    created_user = users_api.create_user(new_user)
    print(f"\nCreated user with ID: {created_user.id}")
