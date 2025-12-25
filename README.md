# HID Origo Integration - Technical Exercise

## Scenario: ACME Corporate Mobile Badge Integration

**Objective**: Enable employee badges in Apple and Google Wallet using HID Origo platform

### Systems Involved
- ACME Corporate Identity Provider (OpenID Connect SSO)
- HID Origo Cloud Services
- Apple Wallet / Google Wallet
- Access Control System (LenelS2)

### Integration Requirements
1. Secure credential issuance and provisioning (Web SDK or Mobile SDK)
2. Lifecycle operations (Suspend, Resume, Delete)
3. Event handling and callback registration

## Project Structure

```
HID-Origo-Integration/
├── docs/                    # Architecture diagrams and documentation
│   ├── architecture.md      # Part 1: Solution Architecture
│   └── troubleshooting.md   # Part 3: Troubleshooting Guide
├── src/
│   ├── api/                 # API client implementations
│   │   ├── auth.py          # OAuth2 authentication
│   │   ├── users.py         # User Management API
│   │   ├── credentials.py   # Credential Management API
│   │   └── callbacks.py     # Callback/Events API
│   ├── models/              # Data models
│   │   ├── user.py
│   │   ├── pass_model.py
│   │   └── events.py
│   ├── services/            # Business logic
│   │   └── provisioning.py  # Orchestration service
│   └── utils/
│       └── config.py
├── tests/                   # Test cases
├── diagrams/                # Architecture diagrams
└── requirements.txt
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo
python -m src.demo
```

## Exercise Parts

1. **Part 1** - Solution Architecture (docs/architecture.md)
2. **Part 2** - API Exercise (src/api/*.py)
3. **Part 3** - Troubleshooting (docs/troubleshooting.md)
4. **Part 4** - Callbacks & Events (src/api/callbacks.py)
