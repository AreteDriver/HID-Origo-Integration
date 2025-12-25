#!/usr/bin/env python3
"""
HID Origo Integration - Complete Demo
=====================================

This demo walks through the entire ACME Corporate mobile badge integration:

Part 2 - API Exercise:
1. Authenticate with OAuth2
2. Create a user
3. Create a pass
4. Generate issuance token

Part 4 - Callbacks:
5. Register a webhook callback
6. Demonstrate event handling

Run: python -m src.demo
"""

import json
from datetime import datetime

# Import our mock APIs (use real APIs in production)
from .api.auth import MockOrigoAuth
from .api.users import MockUserManagementAPI, User
from .api.credentials import MockCredentialManagementAPI
from .api.callbacks import (
    MockCallbackAPI,
    CallbackRegistration,
    EventFilter,
    CloudEvent,
    CallbackRecovery
)


def print_banner(text: str):
    """Print a section banner"""
    width = 70
    print("\n" + "=" * width)
    print(f" {text}")
    print("=" * width)


def main():
    print_banner("HID ORIGO INTEGRATION - COMPLETE DEMO")
    print("""
    Scenario: ACME Corporate Mobile Badge Provisioning

    This demo simulates the complete flow of:
    1. Authenticating to HID Origo API
    2. Creating a user (employee)
    3. Creating a pass (digital badge)
    4. Generating an issuance token for wallet provisioning
    5. Registering webhooks for event notifications

    NOTE: This uses MOCK APIs for demonstration.
          In production, use the real API classes with actual credentials.
    """)

    # =========================================================================
    # PART 2: API Exercise
    # =========================================================================

    print_banner("PART 2: API EXERCISE")

    # -------------------------------------------------------------------------
    # Step 1: Authentication
    # -------------------------------------------------------------------------
    print("\n>>> STEP 1: OAuth2 Authentication")
    print("-" * 50)

    auth = MockOrigoAuth(
        organization_id="acme-corp-7521464",
        client_id="ACME-OSRV-12345678",
        client_secret="K5bkps7mtnq7VDQr_secret"
    )
    auth.authenticate()

    print("\n✓ Authentication complete. We now have a Bearer token for API calls.")
    print("  Token is valid for 3600 seconds (1 hour).")
    print("  All subsequent API calls will include: Authorization: Bearer <token>")

    # -------------------------------------------------------------------------
    # Step 2: Create User
    # -------------------------------------------------------------------------
    print("\n>>> STEP 2: Create User (User Management API)")
    print("-" * 50)

    users_api = MockUserManagementAPI(auth)

    # Create an employee
    employee = User(
        external_id="EMP-2025-001",           # ACME's internal employee ID
        email="john.doe@acme.com",
        display_name="John Doe",
        given_name="John",
        family_name="Doe"
    )

    created_user = users_api.create_user(employee)

    print(f"\n✓ User created in HID Origo.")
    print(f"  Now we have a user_id ({created_user.id}) to associate with a pass.")

    # -------------------------------------------------------------------------
    # Step 3: Create Pass
    # -------------------------------------------------------------------------
    print("\n>>> STEP 3: Create Pass (Credential Management API)")
    print("-" * 50)

    creds_api = MockCredentialManagementAPI(auth)

    # Pass template would be pre-configured in HID Origo portal
    # It defines: credential type (SEOS, iCLASS), artwork, platform settings
    PASS_TEMPLATE_ID = "tmpl-acme-employee-badge-v1"

    pass_obj = creds_api.create_pass(
        user_id=created_user.id,
        pass_template_id=PASS_TEMPLATE_ID
    )

    print(f"\n✓ Pass created with status: {pass_obj.status.value}")
    print(f"  The pass is in PENDING state until provisioned to a wallet.")

    # -------------------------------------------------------------------------
    # Step 4: Generate Issuance Token
    # -------------------------------------------------------------------------
    print("\n>>> STEP 4: Generate Issuance Token")
    print("-" * 50)

    issuance_token = creds_api.get_issuance_token(pass_obj.id)

    print("\n✓ Issuance token generated!")
    print("\n" + "="*60)
    print("WHAT HAPPENS NEXT (in production):")
    print("="*60)
    print("""
    1. Send token to employee's phone via:
       - Push notification (recommended)
       - QR code displayed on enrollment kiosk
       - Deep link in email (less secure)

    2. Employee opens HID Mobile Access app or your company app

    3. App uses HID SDK to provision with the token:

       // iOS Swift
       OrigoKeysManager.shared.provision(issuanceToken: token)

       // Android Kotlin
       origoKeysManager.provision(token)

    4. SDK securely retrieves credential from HID Origo cloud

    5. Credential is stored in device's Secure Element

    6. Badge appears in Apple Wallet / Google Wallet!

    7. Employee can now tap phone on door reader for access
    """)

    # =========================================================================
    # PART 4: Callbacks and Events
    # =========================================================================

    print_banner("PART 4: CALLBACKS AND EVENTS")

    # -------------------------------------------------------------------------
    # Step 5: Register Callback
    # -------------------------------------------------------------------------
    print("\n>>> STEP 5: Register Webhook Callback")
    print("-" * 50)

    callback_api = MockCallbackAPI(auth)

    # Create a callback registration with event filter
    webhook_registration = CallbackRegistration(
        url="https://api.acme.com/webhooks/hid-origo",
        filter=EventFilter(event_types=[
            "PASS_CREATED",
            "PASS_UPDATED",
            "PASS_DELETED",
            "USER_DELETED"
        ]),
        http_header="Authorization",
        secret="Bearer acme-webhook-secret-xyz"
    )

    callback_api.register_callback(webhook_registration)

    print("\n✓ Webhook registered!")
    print("  HID Origo will now POST events to: https://api.acme.com/webhooks/hid-origo")
    print("  Events will be filtered to only: PASS_*, USER_DELETED")

    # -------------------------------------------------------------------------
    # Step 6: Event Handling Example
    # -------------------------------------------------------------------------
    print("\n>>> STEP 6: Event Handling Example")
    print("-" * 50)

    # Simulate receiving an event
    example_event_payload = {
        "type": "PASS_UPDATED",
        "subject": f"pass/{pass_obj.id}",
        "time": datetime.utcnow().isoformat() + "Z",
        "data": {
            "status": "COMPLETED",
            "userId": created_user.id,
            "organizationId": "7521464"
        }
    }

    print("\nSimulated incoming webhook event:")
    print(json.dumps(example_event_payload, indent=2))

    # Parse and interpret
    event = CloudEvent.from_dict(example_event_payload)
    print("\nEvent interpretation:")
    print(event.interpret())

    # =========================================================================
    # Summary
    # =========================================================================

    print_banner("EXERCISE COMPLETE - SUMMARY")

    print("""
    PART 2 - API Exercise (Completed):
    ──────────────────────────────────
    ✓ Step 1: OAuth2 authentication - obtained Bearer token
    ✓ Step 2: Created user via User Management API (SCIM v2)
    ✓ Step 3: Created pass via Credential Management API
    ✓ Step 4: Generated issuance token for wallet provisioning

    PART 4 - Callbacks (Completed):
    ───────────────────────────────
    ✓ Step 5: Registered webhook callback with event filter
    ✓ Step 6: Demonstrated event parsing and interpretation

    Key Learnings:
    ──────────────
    • OAuth2 client_credentials flow for machine-to-machine auth
    • User must exist before pass can be created
    • Issuance token is the bridge between backend and mobile SDK
    • Webhooks enable real-time event-driven architecture
    • CloudEvents format standardizes event payloads

    Production Checklist:
    ─────────────────────
    □ Configure actual HID Origo credentials in .env
    □ Set up pass templates in HID Origo portal
    □ Deploy webhook endpoint (HTTPS, returns 200 OK)
    □ Implement HID Mobile Access SDK in mobile app
    □ Set up monitoring for API and webhook health
    □ Configure access control system integration (LenelS2)
    """)


if __name__ == "__main__":
    main()
