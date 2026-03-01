# Authentication and Authorization Guide

This guide explains how to implement and configure authentication and authorization for the Autonomous Field Engineer API.

## Overview

The system uses a multi-layered security approach:
1. **API Key Authentication** for REST endpoints
2. **AWS IAM** for Bedrock access
3. **Role-Based Access Control (RBAC)** for operations
4. **Audit Logging** for all security events

## API Key Authentication

### Generating API Keys

```python
import secrets
import hashlib
from datetime import datetime, timedelta

def generate_api_key():
    """Generate a secure API key."""
    key = secrets.token_urlsafe(32)
    return f"afe_{key}"

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()

# Generate key
api_key = generate_api_key()
print(f"API Key: {api_key}")
print(f"Hash: {hash_api_key(api_key)}")
```

### Storing API Keys

Store hashed keys in database:

```sql
CREATE TABLE api_keys (
    key_id TEXT PRIMARY KEY,
    key_hash TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
```

### Using API Keys

**Request Header:**
```http
GET /api/v1/workflow/session-123 HTTP/1.1
Host: api.example.com
X-API-Key: afe_your_api_key_here
Content-Type: application/json
```

**cURL Example:**
```bash
curl -H "X-API-Key: afe_your_api_key_here" \
     https://api.example.com/api/v1/workflow/session-123
```

**Python Example:**
```python
import requests

headers = {
    "X-API-Key": "afe_your_api_key_here",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.example.com/api/v1/workflow/session-123",
    headers=headers
)
```

### Implementing API Key Middleware

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import hashlib

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key and return user context."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Hash the provided key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Look up in database
    key_record = await db.get_api_key(key_hash)
    
    if not key_record or not key_record.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    # Check expiration
    if key_record.expires_at and key_record.expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )
    
    # Update last used timestamp
    await db.update_last_used(key_record.key_id)
    
    return {
        "user_id": key_record.user_id,
        "role": key_record.role
    }
```

### Using in Endpoints

```python
from fastapi import Depends

@app.get("/api/v1/workflow/{session_id}")
async def get_workflow(
    session_id: str,
    user: dict = Depends(verify_api_key)
):
    """Get workflow state (requires authentication)."""
    # user contains: {"user_id": "...", "role": "..."}
    
    # Check authorization
    if not can_access_workflow(user, session_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return orchestration.get_workflow_state(session_id)
```

## Role-Based Access Control (RBAC)

### Roles

**Technician:**
- Submit diagnosis requests
- View own workflows
- Follow repair guidance
- Cannot approve purchases > $1000

**Supervisor:**
- All technician permissions
- View team workflows
- Approve purchases up to $5000
- Resolve escalations

**Manager:**
- All supervisor permissions
- View all workflows
- Approve purchases up to $25000
- Access audit logs

**Safety Officer:**
- View safety-related workflows
- Approve high-risk procedures
- Access safety audit logs
- Cannot modify workflows

**Admin:**
- All permissions
- Manage users and API keys
- Configure system settings
- Access all audit logs

### Permission Matrix

| Operation | Technician | Supervisor | Manager | Safety Officer | Admin |
|-----------|------------|------------|---------|----------------|-------|
| Submit diagnosis | ✓ | ✓ | ✓ | ✗ | ✓ |
| View own workflows | ✓ | ✓ | ✓ | ✗ | ✓ |
| View team workflows | ✗ | ✓ | ✓ | ✗ | ✓ |
| View all workflows | ✗ | ✗ | ✓ | ✗ | ✓ |
| Approve < $1K | ✗ | ✓ | ✓ | ✗ | ✓ |
| Approve < $5K | ✗ | ✓ | ✓ | ✗ | ✓ |
| Approve < $25K | ✗ | ✗ | ✓ | ✗ | ✓ |
| Approve > $25K | ✗ | ✗ | ✗ | ✗ | ✓ |
| Resolve escalations | ✗ | ✓ | ✓ | ✓ | ✓ |
| View audit logs | ✗ | ✗ | ✓ | ✓ | ✓ |
| Manage users | ✗ | ✗ | ✗ | ✗ | ✓ |

### Implementing RBAC

```python
from enum import Enum
from typing import List

class Role(str, Enum):
    TECHNICIAN = "technician"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    SAFETY_OFFICER = "safety_officer"
    ADMIN = "admin"

class Permission(str, Enum):
    SUBMIT_DIAGNOSIS = "submit_diagnosis"
    VIEW_OWN_WORKFLOWS = "view_own_workflows"
    VIEW_TEAM_WORKFLOWS = "view_team_workflows"
    VIEW_ALL_WORKFLOWS = "view_all_workflows"
    APPROVE_PURCHASE_1K = "approve_purchase_1k"
    APPROVE_PURCHASE_5K = "approve_purchase_5k"
    APPROVE_PURCHASE_25K = "approve_purchase_25k"
    APPROVE_PURCHASE_UNLIMITED = "approve_purchase_unlimited"
    RESOLVE_ESCALATIONS = "resolve_escalations"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_USERS = "manage_users"

ROLE_PERMISSIONS = {
    Role.TECHNICIAN: [
        Permission.SUBMIT_DIAGNOSIS,
        Permission.VIEW_OWN_WORKFLOWS,
    ],
    Role.SUPERVISOR: [
        Permission.SUBMIT_DIAGNOSIS,
        Permission.VIEW_OWN_WORKFLOWS,
        Permission.VIEW_TEAM_WORKFLOWS,
        Permission.APPROVE_PURCHASE_1K,
        Permission.APPROVE_PURCHASE_5K,
        Permission.RESOLVE_ESCALATIONS,
    ],
    Role.MANAGER: [
        Permission.SUBMIT_DIAGNOSIS,
        Permission.VIEW_OWN_WORKFLOWS,
        Permission.VIEW_TEAM_WORKFLOWS,
        Permission.VIEW_ALL_WORKFLOWS,
        Permission.APPROVE_PURCHASE_1K,
        Permission.APPROVE_PURCHASE_5K,
        Permission.APPROVE_PURCHASE_25K,
        Permission.RESOLVE_ESCALATIONS,
        Permission.VIEW_AUDIT_LOGS,
    ],
    Role.SAFETY_OFFICER: [
        Permission.VIEW_ALL_WORKFLOWS,
        Permission.RESOLVE_ESCALATIONS,
        Permission.VIEW_AUDIT_LOGS,
    ],
    Role.ADMIN: list(Permission),  # All permissions
}

def has_permission(role: Role, permission: Permission) -> bool:
    """Check if role has permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])

def require_permission(permission: Permission):
    """Decorator to require permission for endpoint."""
    def decorator(func):
        async def wrapper(*args, user: dict = Depends(verify_api_key), **kwargs):
            if not has_permission(Role(user["role"]), permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
```

### Using Permission Checks

```python
@app.get("/api/v1/workflows")
@require_permission(Permission.VIEW_ALL_WORKFLOWS)
async def list_workflows(user: dict = Depends(verify_api_key)):
    """List all workflows (requires manager or admin role)."""
    return orchestration.list_workflows()

@app.post("/api/v1/escalations/{escalation_id}/resolve")
@require_permission(Permission.RESOLVE_ESCALATIONS)
async def resolve_escalation(
    escalation_id: str,
    resolution: str,
    user: dict = Depends(verify_api_key)
):
    """Resolve escalation (requires supervisor or higher)."""
    return orchestration.resolve_escalation(escalation_id, resolution)
```

## AWS IAM Configuration

### IAM Policy for Bedrock Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.nova-act-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.nova-sonic-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*"
      ]
    },
    {
      "Sid": "BedrockModelList",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    }
  ]
}
```

### IAM Role for ECS Task

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Attach Policy to Role

```bash
# Create role
aws iam create-role \
  --role-name AFE-Orchestration-Role \
  --assume-role-policy-document file://trust-policy.json

# Attach Bedrock policy
aws iam put-role-policy \
  --role-name AFE-Orchestration-Role \
  --policy-name BedrockAccess \
  --policy-document file://bedrock-policy.json

# Attach to ECS task definition
aws ecs register-task-definition \
  --family afe-orchestration \
  --task-role-arn arn:aws:iam::ACCOUNT:role/AFE-Orchestration-Role \
  --execution-role-arn arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole \
  ...
```

## Audit Logging

### Security Events to Log

```python
from enum import Enum

class SecurityEvent(str, Enum):
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    ESCALATION_CREATED = "escalation_created"
    ESCALATION_RESOLVED = "escalation_resolved"
    SAFETY_VIOLATION = "safety_violation"
    BUDGET_EXCEEDED = "budget_exceeded"

def log_security_event(
    event: SecurityEvent,
    user_id: str,
    details: dict,
    severity: str = "info"
):
    """Log security event to audit log."""
    audit_logger.log({
        "timestamp": datetime.now().isoformat(),
        "event": event.value,
        "user_id": user_id,
        "severity": severity,
        "details": details
    })
```

### Audit Log Schema

```sql
CREATE TABLE security_audit_log (
    log_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event TEXT NOT NULL,
    user_id TEXT,
    role TEXT,
    ip_address TEXT,
    user_agent TEXT,
    resource TEXT,
    action TEXT,
    result TEXT,
    severity TEXT,
    details JSON
);

CREATE INDEX idx_audit_timestamp ON security_audit_log(timestamp);
CREATE INDEX idx_audit_user ON security_audit_log(user_id);
CREATE INDEX idx_audit_event ON security_audit_log(event);
```

## Best Practices

### API Key Management

1. **Rotate keys regularly** (every 90 days)
2. **Use separate keys per environment** (dev, staging, prod)
3. **Never commit keys to version control**
4. **Store keys in secrets manager** (AWS Secrets Manager, HashiCorp Vault)
5. **Monitor key usage** for anomalies
6. **Revoke unused keys** immediately

### Password Security

1. **Enforce strong passwords** (min 12 characters, mixed case, numbers, symbols)
2. **Hash passwords** with bcrypt or Argon2
3. **Implement rate limiting** on login attempts
4. **Use MFA** for admin accounts
5. **Expire passwords** after 90 days

### Network Security

1. **Use HTTPS** for all API endpoints
2. **Implement CORS** properly
3. **Use VPC** for AWS resources
4. **Configure security groups** restrictively
5. **Enable WAF** for production

### Monitoring

1. **Alert on failed auth attempts** (> 5 in 5 minutes)
2. **Monitor API key usage** patterns
3. **Track permission denials**
4. **Review audit logs** regularly
5. **Set up anomaly detection**

## Testing Authentication

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient

def test_api_key_required():
    """Test that API key is required."""
    response = client.get("/api/v1/workflow/session-123")
    assert response.status_code == 401

def test_invalid_api_key():
    """Test invalid API key is rejected."""
    response = client.get(
        "/api/v1/workflow/session-123",
        headers={"X-API-Key": "invalid_key"}
    )
    assert response.status_code == 401

def test_valid_api_key():
    """Test valid API key is accepted."""
    response = client.get(
        "/api/v1/workflow/session-123",
        headers={"X-API-Key": "afe_valid_key"}
    )
    assert response.status_code == 200

def test_permission_denied():
    """Test permission check works."""
    # Technician trying to view all workflows
    response = client.get(
        "/api/v1/workflows",
        headers={"X-API-Key": "afe_technician_key"}
    )
    assert response.status_code == 403
```

## Troubleshooting

### Common Issues

**401 Unauthorized:**
- Check API key is included in header
- Verify key is not expired
- Ensure key is active in database

**403 Forbidden:**
- Check user role has required permission
- Verify resource ownership
- Review RBAC configuration

**AWS Access Denied:**
- Check IAM policy is attached to role
- Verify role is assigned to ECS task
- Ensure Bedrock models are enabled

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
