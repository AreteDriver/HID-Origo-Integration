"""
Part 4: Callbacks and Events API
================================
HID Origo Event Subscription and Webhook Management

This module handles:
- Registering callback webhooks
- Event filtering
- Processing CloudEvents payloads
- Retry and recovery mechanisms

Key Concepts:
- CloudEvents specification for event payloads
- Event filters to subscribe to specific event types
- Webhook authentication via httpHeader + secret
- Failed callbacks are stored and recoverable
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


class EventType(Enum):
    """HID Origo Event Types"""
    # User events
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DELETED = "USER_DELETED"

    # Pass/Credential events
    PASS_CREATED = "PASS_CREATED"
    PASS_UPDATED = "PASS_UPDATED"
    PASS_DELETED = "PASS_DELETED"
    PASS_PROVISIONED = "PASS_PROVISIONED"

    # Credential lifecycle
    CREDENTIAL_SUSPENDED = "CREDENTIAL_SUSPENDED"
    CREDENTIAL_RESUMED = "CREDENTIAL_RESUMED"


@dataclass
class EventFilter:
    """
    Event Filter for callback registration

    Filters allow you to subscribe to specific event types
    rather than receiving all events.

    Question 3 from Part 4: What is an event filter?
    - Filters specify which event types to receive
    - Can filter by event type groups (e.g., all USER_* events)
    - Reduces noise and processing overhead
    """
    event_types: List[str] = field(default_factory=list)
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventTypes": self.event_types
        }

    @classmethod
    def user_events_only(cls) -> "EventFilter":
        """
        Question 3 Answer: Filter for only user management events
        """
        return cls(event_types=[
            "USER_CREATED",
            "USER_UPDATED",
            "USER_DELETED"
        ])

    @classmethod
    def pass_events_only(cls) -> "EventFilter":
        """Filter for only pass/credential events"""
        return cls(event_types=[
            "PASS_CREATED",
            "PASS_UPDATED",
            "PASS_DELETED",
            "PASS_PROVISIONED"
        ])

    @classmethod
    def all_events(cls) -> "EventFilter":
        """No filter - receive all events"""
        return cls(event_types=[])


@dataclass
class CallbackRegistration:
    """
    Callback (Webhook) Registration

    Question 1 from Part 4: What does Callback Registration API do?
    - Registers your webhook endpoint with HID Origo
    - Allows Origo to push events to your system in real-time
    - Required for wallet integrations to know when provisioning completes
    - Enables real-time synchronization of credential lifecycle
    """
    url: str
    filter: EventFilter = field(default_factory=EventFilter)

    # Authentication (both required if either is set)
    http_header: Optional[str] = None  # e.g., "Authorization"
    secret: Optional[str] = None       # e.g., "Basic base64encoded" or API key

    # Set by API response
    id: Optional[str] = None
    created: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request format"""
        data = {
            "url": self.url,
            "filter": self.filter.to_dict()
        }

        # Both httpHeader and secret must be provided together
        if self.http_header and self.secret:
            data["httpHeader"] = self.http_header
            data["secret"] = self.secret

        return data


@dataclass
class CloudEvent:
    """
    CloudEvents specification payload

    Question 5 from Part 4: Event Payload Interpretation

    HID Origo sends events in CloudEvents format:
    - type: Event type (e.g., "PASS_UPDATED")
    - subject: Resource identifier (e.g., "pass/45d3d21e-xxxx")
    - time: ISO 8601 timestamp
    - data: Event-specific payload
    """
    type: str
    subject: str
    time: datetime
    data: Dict[str, Any]

    # CloudEvents metadata
    id: Optional[str] = None
    source: Optional[str] = None
    specversion: str = "1.0"

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CloudEvent":
        """Parse CloudEvent from webhook payload"""
        return cls(
            id=payload.get("id"),
            type=payload.get("type", ""),
            subject=payload.get("subject", ""),
            time=datetime.fromisoformat(payload.get("time", "").replace("Z", "+00:00")),
            data=payload.get("data", {}),
            source=payload.get("source"),
            specversion=payload.get("specversion", "1.0")
        )

    def interpret(self) -> str:
        """
        Question 5 Answer: Interpret what this event means

        Example event:
        {
            "type": "PASS_UPDATED",
            "subject": "pass/45d3d21e-xxxx",
            "time": "2025-11-10T14:05:00Z",
            "data": {
                "status": "COMPLETED",
                "userId": "b47d-56f8-8bcd",
                "organizationId": "7521464"
            }
        }
        """
        interpretations = {
            "PASS_UPDATED": self._interpret_pass_updated,
            "PASS_CREATED": self._interpret_pass_created,
            "USER_CREATED": self._interpret_user_created,
            "USER_DELETED": self._interpret_user_deleted,
        }

        interpreter = interpretations.get(self.type, self._interpret_generic)
        return interpreter()

    def _interpret_pass_updated(self) -> str:
        status = self.data.get("status", "UNKNOWN")
        if status == "COMPLETED":
            return (
                f"Pass {self.subject} provisioning COMPLETED successfully.\n"
                f"User {self.data.get('userId')} now has an active credential.\n"
                f"Action: Update internal database to mark user's badge as ACTIVE.\n"
                f"         Send confirmation notification to user.\n"
                f"         Update access control system if needed."
            )
        elif status == "SUSPENDED":
            return (
                f"Pass {self.subject} has been SUSPENDED.\n"
                f"Action: Disable user's physical access in LenelS2.\n"
                f"         Log the suspension event for audit."
            )
        return f"Pass {self.subject} updated to status: {status}"

    def _interpret_pass_created(self) -> str:
        return (
            f"New pass {self.subject} created for user {self.data.get('userId')}.\n"
            f"Action: Generate issuance token and send to user for provisioning."
        )

    def _interpret_user_created(self) -> str:
        return (
            f"User {self.subject} created in HID Origo.\n"
            f"Action: Proceed with pass creation for this user."
        )

    def _interpret_user_deleted(self) -> str:
        return (
            f"User {self.subject} deleted from HID Origo.\n"
            f"Action: Cleanup any local references.\n"
            f"         Revoke access in physical access control system."
        )

    def _interpret_generic(self) -> str:
        return f"Event {self.type} received for {self.subject}"


class CallbackAPI:
    """
    HID Origo Callback/Events API Client

    Part 4 Questions:
    - Q1: What does Callback Registration API do?
    - Q2: Steps for setting up callback registration
    - Q3: Event filtering
    - Q4: Troubleshooting failed callbacks
    - Q5: Event payload interpretation
    """

    def __init__(self, auth: OrigoAuth, base_url: str = None):
        self.auth = auth
        self.base_url = (base_url or config.base_url).rstrip("/")

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/callback"

    def register_callback(self, registration: CallbackRegistration) -> CallbackRegistration:
        """
        Question 2: Register a new callback (webhook)

        POST /callback
        Content-Type: application/json

        Steps:
        1. Define your webhook endpoint URL (must accept POST, return 200 OK)
        2. Create an EventFilter for specific events (or all events)
        3. Set authentication (httpHeader + secret) for security
        4. Call this API to register

        Required parameters:
        - url: Your webhook endpoint
        - filter: Event filter specification

        Optional parameters:
        - httpHeader: Header name for authentication (e.g., "Authorization")
        - secret: Header value (e.g., "Bearer token123" or "Basic base64...")
        """
        print(f"\n{'='*60}")
        print("CALLBACK REGISTRATION")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.endpoint}")

        payload = registration.to_dict()
        print(f"\nRequest Body:")
        print(f"  url: {registration.url}")
        print(f"  filter.eventTypes: {registration.filter.event_types or 'ALL'}")
        if registration.http_header:
            print(f"  httpHeader: {registration.http_header}")
            print(f"  secret: ******** (hidden)")

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=self.auth.get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            registration.id = data.get("id")
            print(f"\n✓ Callback Registered!")
            print(f"  Registration ID: {registration.id}")

            return registration

        except requests.exceptions.RequestException as e:
            print(f"\n✗ Callback Registration Failed: {e}")
            raise

    def list_callbacks(self) -> List[CallbackRegistration]:
        """List all registered callbacks"""
        response = requests.get(
            self.endpoint,
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()
        # Note: httpHeader and secret are NOT returned for security
        return response.json()

    def delete_callback(self, callback_id: str) -> bool:
        """Remove a callback registration"""
        response = requests.delete(
            f"{self.endpoint}/{callback_id}",
            headers=self.auth.get_headers(),
            timeout=30
        )
        response.raise_for_status()
        print(f"✓ Callback {callback_id} deleted")
        return True


# =============================================================================
# Question 4: Troubleshooting Failed Callbacks
# =============================================================================

class CallbackRecovery:
    """
    Question 4 Answer: How to recover missed callbacks

    When a partner's webhook endpoint is unavailable, events are stored
    by HID Origo and can be recovered.

    Recovery strategies:
    1. Events are NOT lost - HID Origo stores failed deliveries
    2. Use Event Management API to query missed events
    3. Implement idempotent event handlers (same event can be processed multiple times)
    4. Register multiple callback endpoints for redundancy
    """

    @staticmethod
    def explain_recovery() -> str:
        return """
        RECOVERING MISSED CALLBACKS
        ===========================

        Scenario: Webhook endpoint was down for several hours

        Step 1: Check event delivery status
        -----------------------------------
        - HID Origo marks failed deliveries as "failed"
        - Events are stored and recoverable via Event Management API

        Step 2: Query missed events
        ---------------------------
        GET /events?status=failed&since=2025-11-10T00:00:00Z

        This returns all events that failed delivery since the specified time.

        Step 3: Replay events manually
        ------------------------------
        For each missed event:
        1. Parse the event payload
        2. Process it through your normal event handler
        3. Mark as processed in your system

        Step 4: Ensure endpoint is back online
        --------------------------------------
        - Fix the underlying issue (server, firewall, SSL, etc.)
        - Verify endpoint responds with HTTP 200 OK
        - Test with a manual webhook delivery

        Step 5: Request replay from Origo
        ---------------------------------
        Some events may be automatically retried by Origo.
        Contact HID support if automatic retries are not occurring.

        BEST PRACTICES:
        ===============
        1. Implement health checks for your webhook endpoint
        2. Use multiple endpoints for redundancy
        3. Store events in your own queue for processing
        4. Make event handlers idempotent (safe to process twice)
        5. Set up monitoring/alerting for webhook failures
        6. Log all incoming events before processing
        """


# =============================================================================
# MOCK: Simulated API for Testing
# =============================================================================

class MockCallbackAPI(CallbackAPI):
    """Mock Callback API for testing"""

    def __init__(self, auth: MockOrigoAuth = None):
        self.auth = auth or MockOrigoAuth()
        self.base_url = "https://api.origo.hidglobal.com"
        self._registrations: Dict[str, CallbackRegistration] = {}

    def register_callback(self, registration: CallbackRegistration) -> CallbackRegistration:
        """Simulate callback registration"""
        print(f"\n{'='*60}")
        print("CALLBACK REGISTRATION - SIMULATED")
        print(f"{'='*60}")
        print(f"Endpoint: POST {self.endpoint}")

        print(f"\nRequest Body:")
        print(f"  {{")
        print(f'    "url": "{registration.url}",')
        print(f'    "filter": {{')
        print(f'      "eventTypes": {registration.filter.event_types or "[]"}')
        print(f'    }}')
        if registration.http_header:
            print(f'    "httpHeader": "{registration.http_header}",')
            print(f'    "secret": "********"')
        print(f"  }}")

        time.sleep(0.2)

        registration.id = f"cb-{uuid.uuid4().hex[:12]}"
        self._registrations[registration.id] = registration

        print(f"\n✓ Callback Registered! (SIMULATED)")
        print(f"  Registration ID: {registration.id}")
        print(f"\nNote: Your webhook must:")
        print(f"  - Accept HTTP POST requests")
        print(f"  - Content-Type: application/cloudevents-batch+json")
        print(f"  - Return HTTP 200 OK on success")

        return registration


# =============================================================================
# Webhook Handler (Flask example)
# =============================================================================

FLASK_WEBHOOK_EXAMPLE = '''
"""
Example Flask webhook handler for HID Origo events

Run with: flask run --port 5000
"""
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)

# Your callback secret (set during registration)
WEBHOOK_SECRET = "your_webhook_secret"

def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature for security"""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route("/webhooks/origo", methods=["POST"])
def handle_origo_webhook():
    """
    Webhook endpoint for HID Origo events

    Requirements:
    - Accept POST requests
    - Content-Type: application/cloudevents-batch+json
    - Return HTTP 200 OK
    """
    # Verify authentication (if configured)
    auth_header = request.headers.get("Authorization")
    if auth_header != f"Bearer {WEBHOOK_SECRET}":
        return jsonify({"error": "Unauthorized"}), 401

    # Parse CloudEvents batch
    events = request.get_json()

    for event in events:
        event_type = event.get("type")
        subject = event.get("subject")
        data = event.get("data", {})

        print(f"Received event: {event_type}")
        print(f"  Subject: {subject}")
        print(f"  Data: {data}")

        # Handle specific event types
        if event_type == "PASS_UPDATED":
            handle_pass_updated(event)
        elif event_type == "USER_DELETED":
            handle_user_deleted(event)
        # ... handle other event types

    # CRITICAL: Return 200 OK to acknowledge receipt
    return jsonify({"status": "received"}), 200

def handle_pass_updated(event: dict):
    """Handle PASS_UPDATED event"""
    status = event["data"].get("status")
    user_id = event["data"].get("userId")

    if status == "COMPLETED":
        # Provisioning successful!
        # Update your database
        # Notify the user
        # Sync with access control system
        print(f"Pass provisioned for user {user_id}")

def handle_user_deleted(event: dict):
    """Handle USER_DELETED event"""
    # Cleanup local records
    # Revoke physical access
    pass

if __name__ == "__main__":
    app.run(port=5000, debug=True)
'''


if __name__ == "__main__":
    print("\n" + "="*70)
    print("HID ORIGO CALLBACKS & EVENTS DEMO")
    print("="*70)

    # Mock auth
    auth = MockOrigoAuth(
        organization_id="demo-org-123",
        client_id="demo-client-id",
        client_secret="demo-secret"
    )
    auth.authenticate()

    # Mock callback API
    callback_api = MockCallbackAPI(auth)

    # Question 2: Register a callback
    print("\n" + "="*70)
    print("QUESTION 2: Callback Registration Flow")
    print("="*70)

    registration = CallbackRegistration(
        url="https://acme.com/webhooks/origo",
        filter=EventFilter.user_events_only(),  # Question 3: Filter for user events
        http_header="Authorization",
        secret="Bearer my-secret-token"
    )

    callback_api.register_callback(registration)

    # Question 3: Event filter example
    print("\n" + "="*70)
    print("QUESTION 3: Event Filtering")
    print("="*70)
    print("\nFilter for only user management events:")
    user_filter = EventFilter.user_events_only()
    print(f"  eventTypes: {user_filter.event_types}")

    # Question 4: Recovery explanation
    print("\n" + "="*70)
    print("QUESTION 4: Troubleshooting Failed Callbacks")
    print("="*70)
    print(CallbackRecovery.explain_recovery())

    # Question 5: Event interpretation
    print("\n" + "="*70)
    print("QUESTION 5: Event Payload Interpretation")
    print("="*70)

    example_event = {
        "type": "PASS_UPDATED",
        "subject": "pass/45d3d21e-xxxx",
        "time": "2025-11-10T14:05:00Z",
        "data": {
            "status": "COMPLETED",
            "userId": "b47d-56f8-8bcd",
            "organizationId": "7521464"
        }
    }

    print("\nExample Event Payload:")
    import json
    print(json.dumps(example_event, indent=2))

    event = CloudEvent.from_dict(example_event)
    print("\nInterpretation:")
    print(event.interpret())

    # Show Flask example
    print("\n" + "="*70)
    print("WEBHOOK HANDLER EXAMPLE (Flask)")
    print("="*70)
    print(FLASK_WEBHOOK_EXAMPLE)
