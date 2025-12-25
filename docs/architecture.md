# Part 1: Solution Architecture - HID Origo Integration

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ACME CORPORATE INFRASTRUCTURE                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐    │
│  │   ACME IdP       │         │  ACME Backend    │         │  ACME Mobile     │    │
│  │   (OIDC SSO)     │◄───────►│  Server          │◄───────►│  App / Portal    │    │
│  │                  │  (1)    │                  │  (2)    │                  │    │
│  │  - User Auth     │         │  - User Sync     │         │  - Provisioning  │    │
│  │  - JWT Tokens    │         │  - Pass Mgmt     │         │    Trigger       │    │
│  │  - SSO Sessions  │         │  - Event Handler │         │  - Status View   │    │
│  └──────────────────┘         └────────┬─────────┘         └──────────────────┘    │
│                                        │                                            │
└────────────────────────────────────────┼────────────────────────────────────────────┘
                                         │
                    (3) OAuth2 + REST API │ (Bearer Token)
                                         │
┌────────────────────────────────────────┼────────────────────────────────────────────┐
│                            HID ORIGO CLOUD SERVICES                                 │
├────────────────────────────────────────┼────────────────────────────────────────────┤
│                                        ▼                                            │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐    │
│  │  Authentication  │         │  User Management │         │   Credential     │    │
│  │  Service         │────────►│  API             │────────►│   Management API │    │
│  │                  │         │                  │         │                  │    │
│  │  /token          │         │  /user           │         │  /pass           │    │
│  │  OAuth2 Flow     │         │  SCIM v2         │         │  /credential     │    │
│  └──────────────────┘         └──────────────────┘         └────────┬─────────┘    │
│                                                                      │              │
│  ┌──────────────────┐         ┌──────────────────┐                  │              │
│  │  Callback/Event  │◄────────│  Pass Template   │◄─────────────────┘              │
│  │  Service         │         │  Service         │                                  │
│  │                  │         │                  │         ┌──────────────────┐    │
│  │  /callback       │         │  - Artwork       │         │  Issuance Token  │    │
│  │  CloudEvents     │         │  - Credentials   │────────►│  Generator       │    │
│  └────────┬─────────┘         │  - Settings      │         │                  │    │
│           │                   └──────────────────┘         │  One-time PWD    │    │
│           │ (6)                                             └────────┬─────────┘    │
└───────────┼─────────────────────────────────────────────────────────┼──────────────┘
            │                                                          │
            │ Webhooks                              (4) Issuance Token │
            │ (CloudEvents)                                            │
            │                                                          ▼
┌───────────┼──────────────────────────────────────────────────────────────────────────┐
│           │                    MOBILE DEVICE / WALLET                                │
│           │   ┌──────────────────┐         ┌──────────────────┐                     │
│           │   │  HID Mobile      │         │  Apple Wallet /  │                     │
│           └──►│  Access SDK      │────────►│  Google Wallet   │                     │
│               │                  │  (5)    │                  │                     │
│               │  - Init SDK      │         │  - NFC Badge     │                     │
│               │  - Use Token     │         │  - BLE Support   │                     │
│               │  - Provision     │         │  - Secure Element│                     │
│               └──────────────────┘         └────────┬─────────┘                     │
│                                                      │                               │
└──────────────────────────────────────────────────────┼───────────────────────────────┘
                                                       │
                                        (7) NFC/BLE    │
                                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                         ACCESS CONTROL SYSTEM (LenelS2)                              │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐    │
│  │  Door Readers    │         │  Access Control  │         │  Door/Lock       │    │
│  │                  │────────►│  Panel           │────────►│  Hardware        │    │
│  │  - iCLASS SE     │         │                  │         │                  │    │
│  │  - SEOS          │         │  - Credential    │         │  - Grant/Deny    │    │
│  │  - NFC Readers   │         │    Validation    │         │  - Audit Log     │    │
│  └──────────────────┘         └──────────────────┘         └──────────────────┘    │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequence

### Flow 1: User Registration & Authentication
```
Employee ──► ACME IdP (OIDC) ──► JWT Token ──► ACME Backend
```

### Flow 2: User Sync to HID Origo
```
ACME Backend ──► OAuth2 Token Request ──► HID Origo Auth
             ──► POST /user ──► Create User in Origo
```

### Flow 3: Pass Creation & Issuance Token
```
ACME Backend ──► POST /pass (with passTemplateId, userId)
             ──► GET /pass/{id}/issuanceToken
             ──► Return token to mobile app
```

### Flow 4: Wallet Provisioning
```
Mobile App ──► Initialize HID SDK with issuanceToken
           ──► SDK contacts Origo for provisioning data
           ──► Credential provisioned to Secure Element
           ──► Pass appears in Apple/Google Wallet
```

### Flow 5: Event Callbacks
```
HID Origo ──► PASS_CREATED event ──► ACME Webhook endpoint
          ──► PASS_UPDATED event ──► Update internal status
          ──► USER_DELETED event ──► Cleanup operations
```

---

## API Endpoints Summary

| API | Endpoint | Purpose |
|-----|----------|---------|
| **Authentication** | `POST /authentication/customer/{org_id}/token` | Get OAuth2 Bearer Token |
| **User Management** | `POST /user` | Create user |
| | `GET /user/{id}` | Get user details |
| | `PATCH /user/{id}` | Update user |
| | `DELETE /user/{id}` | Delete user |
| **Credential Mgmt** | `POST /pass` | Create a pass |
| | `GET /pass/{id}` | Get pass status |
| | `GET /pass/{id}/issuanceToken` | Generate provisioning token |
| | `PATCH /pass/{id}` | Update pass (suspend/resume) |
| | `DELETE /pass/{id}` | Delete pass |
| **Callbacks** | `POST /callback` | Register webhook |
| | `GET /callback` | List registrations |
| | `DELETE /callback/{id}` | Remove registration |

---

## Authentication Mechanisms

### 1. ACME IdP → User (OpenID Connect)
- Standard OIDC flow for employee SSO
- JWT tokens for session management
- User authenticates once, token used throughout

### 2. ACME Backend → HID Origo (OAuth2 Client Credentials)
```
POST /authentication/customer/{organization_id}/token
Content-Type: application/x-www-form-urlencoded

client_id={system_account_id}
&client_secret={secret}
&grant_type=client_credentials
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 3. API Calls (Bearer Token)
```
Authorization: Bearer {access_token}
Application-ID: acme-mobile-access
Application-Version: 1.0.0
```

---

## Provisioning & Event Flow (200-300 words)

The HID Origo integration enables secure mobile credential provisioning through a coordinated flow between identity management, cloud services, and mobile wallets.

**User Onboarding**: When an employee joins ACME, they authenticate via the corporate Identity Provider (OIDC). The ACME backend synchronizes user data to HID Origo using the User Management API, creating a user record that links the corporate identity to Origo's credential system.

**Pass Issuance**: The ACME backend requests a pass from the Credential Management API, specifying a Pass Template (which defines credential type, artwork, and settings) and the user ID. Origo creates the pass and assigns credentials. The backend then requests an issuance token - a one-time password enabling secure provisioning.

**Mobile Provisioning**: The employee's mobile app (or web portal) receives the issuance token. Using the HID Mobile Access SDK, the app initializes a provisioning session. The SDK securely communicates with Origo, retrieves the credential data, and provisions it to the device's Secure Element. Once complete, the credential appears in Apple Wallet or Google Wallet as a functional access badge.

**Lifecycle Management**: Origo sends webhook events (CloudEvents format) to ACME's registered callback endpoint. Events like `PASS_CREATED`, `PASS_UPDATED`, and `USER_DELETED` enable real-time synchronization. The ACME backend can perform lifecycle operations (suspend during leave, resume upon return, delete upon termination) via PATCH and DELETE API calls.

**Physical Access**: When the employee presents their phone to a LenelS2 reader, NFC/BLE communication transmits the credential. The reader validates against the access control panel, grants or denies entry, and logs the event - completing the seamless digital-to-physical access chain.

---

## Security Considerations

1. **Token Expiry**: OAuth tokens expire after 1 hour; implement refresh logic
2. **Issuance Token**: One-time use, short-lived - never store or log
3. **Webhook Security**: Use `httpHeader` + `secret` for callback authentication
4. **Secure Element**: Credentials stored in hardware-backed secure storage
5. **TLS**: All API communication over HTTPS
6. **Audit Logging**: Track all credential lifecycle events
