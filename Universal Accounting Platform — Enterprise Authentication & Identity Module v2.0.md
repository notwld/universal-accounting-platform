# Universal Accounting Platform
## Enterprise Authentication & Identity Module
### Version 2.0 — Clerk Custom UI + Django REST Framework

---

## 1. Document Purpose

This document defines the **Authentication & Identity module only** for a universal, easy-to-use accounting SaaS intended to support organizations in:

- Pakistan
- India
- Saudi Arabia
- GCC countries
- United States
- United Kingdom

The wider platform will eventually provide:

- organizations/businesses;
- multiple branches/offices/locations;
- custom RBAC;
- custom roles and permissions;
- customers and vendors;
- quotations;
- invoices;
- expenses;
- payments;
- refunds;
- credit notes;
- taxation;
- cash flow;
- financial statements;
- reporting;
- notifications;
- email;
- audit history.

Those domains are intentionally **outside this module**.

This module provides the identity and security foundation they will consume.

---

# 2. Technology Stack

| Layer | Technology |
|---|---|
| Identity Provider | Clerk |
| Authentication UI | Fully Custom UI |
| Backend | Django |
| APIs | Django REST Framework |
| Primary Database | PostgreSQL |
| Cache | Redis |
| Background Jobs | Celery |
| Queue/Broker | Redis initially |
| API Style | REST |
| API Version | `/api/v1/` |
| IDs | UUIDv7 recommended |
| Deployment | ASGI |
| Monitoring | Prometheus + Grafana |
| Error Tracking | Sentry |
| Tracing | OpenTelemetry |
| Logging | Structured JSON |

---

# 3. Core Architecture Principle

Authentication and application authorization must be separated.

Clerk answers:

> Who is this user?

Django answers:

> What can this authenticated user do inside this accounting platform?

Therefore:

```text
CUSTOM FRONTEND UI
        │
        ▼
      CLERK
        │
        │ Authentication
        │ Session
        │ JWT
        ▼
DJANGO REST FRAMEWORK
        │
        ├── Verify Clerk JWT
        ├── Resolve local user
        ├── Resolve organization
        ├── Resolve location
        ├── Resolve RBAC
        ├── Establish RLS context
        ├── Audit
        └── Serve accounting APIs
```

---

# 4. Clerk vs Django Responsibility

## 4.1 Clerk owns authentication

The following functionality must be handled through Clerk:

| Capability | System |
|---|---|
| Sign up | Clerk |
| Login | Clerk |
| Logout | Clerk |
| Password authentication | Clerk |
| Password hashing/storage | Clerk |
| Email verification | Clerk |
| Forgot password | Clerk |
| Password reset | Clerk |
| OTP | Clerk |
| MFA | Clerk |
| TOTP | Clerk |
| Backup codes | Clerk |
| Passkeys | Clerk |
| Social authentication | Clerk |
| Enterprise SSO | Clerk |
| Authentication session | Clerk |
| Session token | Clerk |
| Token refresh | Clerk |

We will build **our own frontend UI**, but authentication actions underneath that UI use Clerk.

Clerk explicitly supports completely custom sign-in/sign-up flows rather than requiring its prebuilt components.

---

## 4.2 Django owns application identity

Django owns:

```text
Local application user
Organization membership
Location membership
Custom RBAC
Custom roles
Permissions
Application suspension
Authorization versioning
Application security events
Audit logs
RLS context
Tenant isolation
API authorization
Idempotency
Internal application identity
```

This separation is mandatory.

---

# 5. APIs We Will NOT Build in Django

The following endpoints should **not exist**:

```text
POST /api/v1/auth/login
POST /api/v1/auth/signup
POST /api/v1/auth/logout
POST /api/v1/auth/refresh

POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password

POST /api/v1/auth/send-otp
POST /api/v1/auth/verify-otp

POST /api/v1/auth/mfa/verify
POST /api/v1/auth/passkey
```

They duplicate Clerk.

Django should never become a second credential provider.

---

# 6. Custom Login UI Flow

Our UI may look completely different from Clerk.

Example:

```text
/account/login
```

User sees:

```text
Email
Password
Remember Device
Forgot Password
Login
```

Our React/Next.js frontend invokes Clerk.

Flow:

```text
User
 │
 ▼
Custom Login Form
 │
 ▼
Clerk SDK
 │
 ├── Verify email/password
 ├── MFA if required
 ├── Device verification if required
 └── Create Clerk session
 │
 ▼
Session established
 │
 ▼
Clerk session JWT
 │
 ▼
Django APIs
```

Django never receives the password.

---

# 7. Custom Logout Flow

Logout is also performed through Clerk.

Example frontend:

```javascript
await clerk.signOut()
```

Clerk explicitly provides `signOut()` for custom authentication interfaces.

After logout:

```text
Clerk session becomes invalid
       ↓
Frontend clears application state
       ↓
Return to /login
```

Django receives corresponding session/user events where configured and can update its local audit/session projection asynchronously.

---

# 8. Token Refresh

Django must not create its own refresh token.

Clerk session tokens are short-lived JWTs and Clerk refreshes them automatically. Clerk currently documents a 60-second refresh cycle.

When an immediate new token is required, the frontend may use:

```javascript
const token = await getToken({
    skipCache: true
})
```

Clerk documents this as the mechanism for forcing a fresh token.

Therefore there is no:

```text
POST /api/v1/auth/refresh
```

in Django.

---

# 9. Protected Django Request

Every protected Django request uses:

```http
Authorization: Bearer <CLERK_SESSION_JWT>
```

Example:

```http
GET /api/v1/auth/me
Authorization: Bearer eyJ...
Accept: application/json
```

Django:

```text
Extract token
    ↓
Verify token
    ↓
Resolve local user
    ↓
Check application status
    ↓
Resolve tenant
    ↓
Resolve location
    ↓
Apply permissions
    ↓
Set RLS context
    ↓
Process endpoint
```

---

# 10. JWT Verification

Django should verify Clerk session JWTs.

Important checks:

```text
signature
iss
exp
nbf
azp / authorized party
session ID
user ID
```

Relevant claims include:

```json
{
  "sub": "user_xxxxx",
  "sid": "sess_xxxxx",
  "iss": "https://xxxxx.clerk.accounts.dev",
  "azp": "https://app.example.com",
  "iat": 1789570000,
  "nbf": 1789570000,
  "exp": 1789570060
}
```

Use:

```text
sub
=
Clerk User ID

sid
=
Clerk Session ID
```

Clerk supports networkless token verification when the JWT verification key is supplied, and recommends checking `authorizedParties` against allowed frontend origins.

---

# 11. Do Not Call Clerk on Every Django Request

Avoid:

```text
API request
    ↓
Django
    ↓
Clerk Backend API
    ↓
get user
    ↓
Django database
```

Instead:

```text
API request
    ↓
verify JWT locally
    ↓
Redis
    ↓
PostgreSQL if required
```

Clerk notes that repeatedly retrieving user information through its Backend API adds latency and contributes to Backend API rate limits.

---

# 12. Do Not Put Full RBAC Into Clerk JWT

Our platform may eventually support permissions such as:

```text
invoice.create
invoice.read
invoice.update
invoice.void

quotation.create

expense.create
expense.approve

payment.create
payment.refund

customer.manage

reports.pnl.read
reports.balance_sheet.read

tax.read
tax.submit

location.users.assign

roles.create
roles.permissions.assign
```

Potentially hundreds of permissions.

Do not put this complete permission graph in Clerk session claims.

Clerk documents a practical custom-claims capacity of roughly 1.2 KB after accounting for its default cookie/session data.

RBAC belongs in PostgreSQL/Redis.

---

# 13. Django Authentication APIs

The Django Authentication module exposes only application-level identity APIs.

## API Catalogue

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/auth/bootstrap` | Initialize application identity after Clerk authentication |
| GET | `/api/v1/auth/me` | Return current application user |
| GET | `/api/v1/auth/context` | Return current tenant/location/auth context |
| GET | `/api/v1/auth/sessions` | Return application session projection |
| GET | `/api/v1/auth/security-events` | User-visible security events |
| POST | `/api/v1/auth/context/switch` | Validate/change application context |
| POST | `/api/v1/webhooks/clerk` | Receive Clerk events |

Notice:

```text
NO /login
NO /logout
NO /refresh
```

---

# 14. POST `/api/v1/auth/bootstrap`

This is **not login**.

Clerk authentication has already succeeded.

Bootstrap establishes our accounting application's local identity.

## Request

```http
POST /api/v1/auth/bootstrap
Authorization: Bearer <clerk-session-jwt>
Content-Type: application/json
Idempotency-Key: 019...
X-Request-ID: 019...
```

Payload:

```json
{
  "device": {
    "name": "Office MacBook",
    "platform": "web",
    "app_version": "1.0.0"
  },
  "preferences": {
    "timezone": "Asia/Karachi",
    "locale": "en-PK"
  }
}
```

---

# 15. Bootstrap Processing

```text
Verify Clerk JWT
       ↓
extract sub
       ↓
extract sid
       ↓
lookup local user
       ↓
       ├── exists → continue
       │
       └── missing → JIT provision
       ↓
check application account
       ↓
upsert local session projection
       ↓
resolve memberships
       ↓
resolve default organization
       ↓
resolve default location
       ↓
resolve authorization version
       ↓
populate Redis
       ↓
security event
       ↓
return bootstrap response
```

---

# 16. Bootstrap Response

### HTTP `200 OK`

```json
{
  "data": {
    "user": {
      "id": "019ab...",
      "first_name": "Hasnain",
      "last_name": "Muavia",
      "email": "hasnain@example.com",
      "email_verified": true,
      "status": "active"
    },

    "context": {
      "organization_id": "019ac...",
      "location_id": "019ad..."
    },

    "authorization": {
      "version": 7,
      "roles": [
        "owner"
      ]
    },

    "onboarding": {
      "required": false,
      "next_step": null
    }
  },

  "meta": {
    "request_id": "019...",
    "timestamp": "2026-09-16T08:00:00Z"
  }
}
```

---

# 17. Bootstrap Status Codes

| Status | Purpose |
|---:|---|
| `200` | Success |
| `400` | Invalid request |
| `401` | Invalid Clerk session |
| `403` | Application account suspended |
| `409` | Idempotency conflict |
| `422` | Payload validation failure |
| `429` | Rate limit |
| `503` | Required application dependency unavailable |

---

# 18. GET `/api/v1/auth/me`

Returns the current **application user**, not merely the Clerk user.

Request:

```http
GET /api/v1/auth/me
Authorization: Bearer <clerk-jwt>
X-Organization-ID: 019...
X-Location-ID: 019...
```

Response:

```json
{
  "data": {
    "id": "019...",

    "identity": {
      "clerk_user_id": "user_xxx",
      "first_name": "Hasnain",
      "last_name": "Muavia",
      "email": "hasnain@example.com",
      "email_verified": true,
      "avatar_url": null
    },

    "preferences": {
      "timezone": "Asia/Karachi",
      "locale": "en-PK"
    },

    "status": "active",

    "current_context": {
      "organization_id": "019...",
      "location_id": "019..."
    },

    "authorization": {
      "version": 7,
      "roles": [
        "owner"
      ]
    }
  },

  "meta": {
    "request_id": "019..."
  }
}
```

---

# 19. GET `/api/v1/auth/context`

Purpose:

> Tell the frontend what organization/location context is currently valid.

Request:

```http
GET /api/v1/auth/context

Authorization: Bearer <token>

X-Organization-ID: 019...
X-Location-ID: 019...
```

Backend checks:

```text
user authenticated?
       ↓
organization exists?
       ↓
membership exists?
       ↓
membership active?
       ↓
location belongs to organization?
       ↓
user has location access?
       ↓
return context
```

Response:

```json
{
  "data": {
    "organization": {
      "id": "019...",
      "name": "ABC Trading"
    },

    "location": {
      "id": "019...",
      "name": "Lahore Office"
    },

    "authorization": {
      "version": 7,
      "roles": [
        "owner"
      ]
    }
  }
}
```

---

# 20. POST `/api/v1/auth/context/switch`

Used when the user switches:

```text
Business
Branch
Office
Location
```

Example:

```http
POST /api/v1/auth/context/switch
Authorization: Bearer <token>
Content-Type: application/json
```

Payload:

```json
{
  "organization_id": "019...",
  "location_id": "019..."
}
```

Django validates everything.

Frontend cannot grant itself access by changing an ID.

Response:

```json
{
  "data": {
    "organization_id": "019...",
    "location_id": "019...",
    "authorization_version": 8
  }
}
```

---

# 21. Local User Database

## Table

```text
auth_user
```

Recommended schema:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `clerk_user_id` | varchar(64) | UNIQUE |
| `primary_email_hash` | char(64) | lookup |
| `primary_email_ciphertext` | text | encrypted if stored |
| `first_name` | varchar(150) | nullable |
| `last_name` | varchar(150) | nullable |
| `avatar_url` | text | nullable |
| `email_verified` | boolean | default false |
| `status` | varchar(20) | application status |
| `authorization_version` | bigint | default 1 |
| `timezone` | varchar(64) | nullable |
| `locale` | varchar(20) | nullable |
| `last_authenticated_at` | timestamptz | nullable |
| `last_seen_at` | timestamptz | nullable |
| `created_at` | timestamptz | required |
| `updated_at` | timestamptz | required |
| `deleted_at` | timestamptz | nullable |

Status:

```text
active
suspended
deleted
```

---

# 22. User Indexes

```sql
CREATE UNIQUE INDEX auth_user_clerk_user_id_uidx
ON auth_user(clerk_user_id);
```

```sql
CREATE INDEX auth_user_email_hash_idx
ON auth_user(primary_email_hash);
```

```sql
CREATE INDEX auth_user_non_active_idx
ON auth_user(status)
WHERE status <> 'active';
```

---

# 23. Django Password

Because Clerk owns credentials, Django should not maintain a usable password.

Conceptually:

```python
user.set_unusable_password()
```

Never synchronize Clerk passwords into PostgreSQL.

Never store:

```text
password
password hash
MFA secret
OTP
recovery code
reset token
```

in this platform database.

---

# 24. Local Session Projection

Clerk owns the real session.

Django may maintain a lightweight **projection** for:

```text
audit
device view
security dashboard
usage analytics
revocation awareness
```

Table:

```text
auth_session_projection
```

Schema:

| Column | Type |
|---|---|
| `id` | UUID PK |
| `user_id` | UUID FK |
| `clerk_session_id` | varchar(100) UNIQUE |
| `status` | varchar(20) |
| `device_name` | varchar(100) nullable |
| `device_platform` | varchar(40) nullable |
| `browser_family` | varchar(50) nullable |
| `app_version` | varchar(30) nullable |
| `ip_hash` | char(64) nullable |
| `user_agent_hash` | char(64) nullable |
| `created_at` | timestamptz |
| `last_seen_at` | timestamptz |
| `ended_at` | timestamptz nullable |

Possible statuses:

```text
active
ended
expired
unknown
```

This table is **not a second session authority**.

Clerk remains authoritative.

---

# 25. Session Indexes

```sql
CREATE UNIQUE INDEX auth_session_clerk_sid_uidx
ON auth_session_projection(clerk_session_id);
```

```sql
CREATE INDEX auth_session_user_active_idx
ON auth_session_projection(
    user_id,
    last_seen_at DESC
)
WHERE status = 'active';
```

---

# 26. GET `/api/v1/auth/sessions`

Provides application-visible session/device information.

Request:

```http
GET /api/v1/auth/sessions?limit=20&cursor=...

Authorization: Bearer <token>
```

Response:

```json
{
  "data": [
    {
      "id": "019...",
      "device_name": "Office MacBook",
      "platform": "web",
      "browser": "Chrome",
      "current": true,
      "status": "active",
      "last_seen_at": "2026-09-16T08:00:00Z"
    }
  ],

  "meta": {
    "has_more": false,
    "next_cursor": null
  }
}
```

Do not expose:

```text
JWT
raw session secret
full IP address
Authorization header
Clerk secret
```

---

# 27. Clerk Webhook Endpoint

Endpoint:

```http
POST /api/v1/webhooks/clerk
```

It is public from the Bearer-authentication perspective.

Security comes from webhook-signature verification.

Clerk provides webhook signature verification and recommends using the webhook signing secret.

---

# 28. Clerk Webhook Events

At minimum process:

```text
user.created
user.updated
user.deleted
```

Additional session events can be consumed when required by the implementation.

Clerk specifically documents these user events for external user synchronization.

---

# 29. Webhook Architecture

Never perform expensive work directly inside the HTTP webhook request.

Flow:

```text
Clerk webhook
     ↓
verify signature
     ↓
validate event
     ↓
deduplicate
     ↓
persist provider event
     ↓
DB commit
     ↓
queue Celery task
     ↓
return 2xx
```

Celery:

```text
read persisted event
     ↓
perform idempotent synchronization
     ↓
update event status
```

---

# 30. Webhook Event Table

## `auth_provider_event`

| Column | Type |
|---|---|
| `id` | UUID PK |
| `provider` | varchar(30) |
| `external_event_id` | varchar(150) |
| `event_type` | varchar(100) |
| `payload_hash` | char(64) |
| `status` | varchar(30) |
| `attempts` | integer |
| `received_at` | timestamptz |
| `processing_started_at` | timestamptz nullable |
| `processed_at` | timestamptz nullable |
| `error_code` | varchar(100) nullable |
| `error_summary` | text nullable |

Constraint:

```sql
UNIQUE(provider, external_event_id)
```

This guarantees event-level idempotency.

---

# 31. Webhooks Are Not the Login Dependency

Clerk warns that webhook synchronization is eventually consistent and webhook delivery may be delayed or fail.

Therefore never design:

```text
Clerk user created
       ↓
WAIT for webhook
       ↓
create Django user
       ↓
allow application
```

Instead:

```text
Clerk authentication succeeds
       ↓
/auth/bootstrap
       ↓
user exists locally?
       │
   ┌───┴───┐
   yes     no
    │       │
continue   JIT provision
```

Meanwhile:

```text
Clerk webhook
     ↓
UPSERT same user
```

Both paths are idempotent.

---

# 32. JIT Provisioning

Local user creation should use:

```text
clerk_user_id
```

as the external identity key.

Pseudo-operation:

```python
user, created = User.objects.update_or_create(
    clerk_user_id=claims["sub"],
    defaults={
        ...
    },
)
```

In real implementation, avoid overwriting user-managed local fields unnecessarily.

Critical DB constraint:

```sql
UNIQUE(clerk_user_id)
```

This prevents race-condition duplication.

---

# 33. Authentication Cache

Redis keys:

```text
acct:auth:user:<clerk_user_id>
```

```text
acct:auth:session:<clerk_session_id>
```

```text
acct:auth:context:
<user_uuid>:
<organization_uuid>:
<location_uuid>:
v<authorization_version>
```

```text
acct:auth:rate:<scope>:<identifier>
```

```text
acct:auth:webhook:<event_id>
```

---

# 34. Recommended Cache TTL

| Cache | TTL |
|---|---:|
| Local user projection | 5 minutes |
| Authorization context | 2–5 minutes |
| Negative user lookup | 15–30 sec |
| Webhook processing lock | 2 min |
| Bootstrap lock | 30 sec |

Add jitter.

Instead of every key expiring after exactly:

```text
300 seconds
```

use approximately:

```text
270–330 seconds
```

to reduce coordinated expiration.

---

# 35. Authorization Version

Every application user has:

```text
authorization_version
```

Example:

```text
17
```

If their:

```text
organization membership
role
permission
location access
account status
```

changes:

```text
17 → 18
```

Cache:

```text
acct:auth:context:user:org:location:v18
```

The previous cache automatically becomes obsolete.

---

# 36. Cache Stampede Protection

When authorization cache expires:

```text
request
   ↓
Redis lookup
   ↓
MISS
   ↓
SET NX distributed lock
   ↓
first process gets DB data
   ↓
cache
   ↓
other processes reuse result
```

Do not let 500 simultaneous dashboard requests produce 500 identical permission queries.

---

# 37. Application Account Suspension

A user can be authenticated by Clerk but blocked from our application.

For example:

```text
Clerk authentication = valid

Django application status = suspended
```

Return:

```http
HTTP/1.1 403 Forbidden
```

```json
{
  "error": {
    "code": "account_suspended",
    "message": "This account is currently unavailable.",
    "request_id": "019..."
  }
}
```

Do not delete Clerk authentication simply to implement an accounting-platform suspension.

---

# 38. Authentication Middleware

Recommended request pipeline:

```text
Request
   ↓
Request ID
   ↓
CORS
   ↓
Clerk JWT Authentication
   ↓
Local User Resolver
   ↓
Application Status Check
   ↓
Organization Resolver
   ↓
Location Resolver
   ↓
Authorization Engine
   ↓
RLS Context
   ↓
APIView
```

---

# 39. DRF Authentication Class

Create:

```text
apps.authentication.authenticators.ClerkJWTAuthentication
```

Conceptually:

```python
class ClerkJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):

        token = extract_bearer_token(request)

        if not token:
            return None

        claims = verify_clerk_token(token)

        clerk_user_id = claims["sub"]
        clerk_session_id = claims["sid"]

        user = identity_service.resolve_user(
            clerk_user_id=clerk_user_id
        )

        security_service.enforce_user_status(user)

        context = ClerkAuthenticationContext(
            clerk_user_id=clerk_user_id,
            clerk_session_id=clerk_session_id,
            claims=claims,
        )

        return user, context
```

---

# 40. Global API Security

Production DRF defaults:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authentication.authenticators."
        "ClerkJWTAuthentication",
    ],

    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions."
        "IsAuthenticated",
    ],
}
```

Everything is authenticated by default.

Explicit public endpoints use:

```text
AllowAny
```

Examples:

```text
health
readiness
Clerk webhook
selected public configuration
```

---

# 41. Request Headers

Recommended standard:

```http
Authorization: Bearer <clerk-session-jwt>

X-Request-ID: <uuid>

X-Organization-ID: <uuid>

X-Location-ID: <uuid>

X-Timezone: Asia/Karachi

Accept-Language: en-PK

Content-Type: application/json
```

For supported mutation requests:

```http
Idempotency-Key: <unique-key>
```

---

# 42. Never Trust Context Headers

These headers:

```text
X-Organization-ID
X-Location-ID
```

are user requests, not authorization evidence.

Backend must perform:

```text
Does organization exist?
       ↓
Does user belong to organization?
       ↓
Is membership active?
       ↓
Does location belong to organization?
       ↓
Does user have access to location?
       ↓
Does role scope allow operation?
```

Only then may the context become trusted.

---

# 43. Standard Success Response

```json
{
  "data": {},
  "meta": {
    "request_id": "019...",
    "timestamp": "2026-09-16T08:00:00Z"
  }
}
```

---

# 44. Standard Error Response

```json
{
  "error": {
    "code": "invalid_token",
    "message": "Authentication could not be validated.",
    "field_errors": null,
    "request_id": "019...",
    "timestamp": "2026-09-16T08:00:00Z"
  }
}
```

Never expose:

```text
traceback
SQL
secret key
JWT
internal server paths
Redis credentials
Clerk credentials
```

---

# 45. Authentication Error Catalogue

| Code | HTTP |
|---|---:|
| `authentication_required` | `401` |
| `invalid_token` | `401` |
| `expired_token` | `401` |
| `invalid_token_issuer` | `401` |
| `invalid_authorized_party` | `401` |
| `invalid_session` | `401` |
| `account_suspended` | `403` |
| `organization_access_denied` | `403` |
| `location_access_denied` | `403` |
| `permission_denied` | `403` |
| `context_not_found` | `404` |
| `idempotency_conflict` | `409` |
| `validation_error` | `422` |
| `rate_limit_exceeded` | `429` |
| `identity_dependency_unavailable` | `503` |

---

# 46. Response Headers

Sensitive authentication APIs:

```http
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache
X-Request-ID: 019...
```

Authentication errors:

```http
WWW-Authenticate: Bearer
```

Throttled:

```http
Retry-After: 30
```

---

# 47. Idempotency

Authentication bootstrap is an ideal candidate for idempotency.

Header:

```http
Idempotency-Key: 019...
```

Table:

```text
api_idempotency_record
```

Fields:

```text
id
user_id
organization_id

key_hash
method
canonical_path
request_hash

status

response_status
response_body

created_at
expires_at
```

Unique:

```text
user
+
method
+
canonical path
+
idempotency key
```

---

# 48. Idempotency Conflict

If:

```text
same key
+
different payload
```

return:

```http
409 Conflict
```

```json
{
  "error": {
    "code": "idempotency_conflict",
    "message": "This idempotency key was already used for a different request.",
    "request_id": "019..."
  }
}
```

---

# 49. PostgreSQL RLS

Authentication establishes the trusted identity context used by future accounting tables.

Example transaction:

```sql
BEGIN;

SET LOCAL app.user_id =
'019...';

SET LOCAL app.organization_id =
'019...';

SET LOCAL app.location_id =
'019...';

SELECT *
FROM invoice;

COMMIT;
```

Future RLS:

```sql
CREATE POLICY invoice_tenant_isolation
ON invoice

USING (
    organization_id =
    current_setting(
        'app.organization_id',
        true
    )::uuid
);
```

This protects against accidental missing tenant filters.

---

# 50. Important RLS Rule

The ordinary Django database connection role should **not** have:

```text
BYPASSRLS
```

Otherwise application-level tenant isolation can accidentally bypass PostgreSQL RLS entirely.

Migration/administrative roles can be separated.

---

# 51. Celery + RLS

Celery does not have an HTTP request context.

Tenant-sensitive task payload:

```json
{
  "organization_id": "019...",
  "location_id": "019...",
  "actor_user_id": "019...",
  "resource_id": "019..."
}
```

Worker:

```text
receive task
      ↓
validate IDs
      ↓
BEGIN transaction
      ↓
SET LOCAL RLS context
      ↓
perform operation
      ↓
COMMIT
```

Never depend upon a global:

```text
current_organization
```

variable.

---

# 52. Celery Queues

Authentication-related queues:

```text
auth.webhooks
auth.audit
auth.security
auth.notifications
auth.maintenance
```

Potential tasks:

```text
process_clerk_user_created

process_clerk_user_updated

process_clerk_user_deleted

sync_user_projection

persist_security_event

send_security_notification

expire_local_session_projection

cleanup_provider_events

cleanup_idempotency_records
```

---

# 53. Celery Payload Security

Never place these into Celery messages:

```text
password
session JWT
Authorization header
OTP
TOTP secret
backup code
Clerk secret key
```

Pass internal identifiers instead:

```json
{
  "provider_event_id": "019..."
}
```

Worker retrieves required data itself.

---

# 54. Security Events

Table:

```text
auth_security_event
```

Schema:

| Field | Type |
|---|---|
| `id` | UUID |
| `event_type` | varchar |
| `actor_user_id` | UUID nullable |
| `subject_user_id` | UUID nullable |
| `clerk_session_id` | varchar nullable |
| `organization_id` | UUID nullable |
| `location_id` | UUID nullable |
| `severity` | varchar |
| `request_id` | UUID nullable |
| `ip_hash` | char(64) nullable |
| `user_agent_hash` | char(64) nullable |
| `metadata` | jsonb |
| `occurred_at` | timestamptz |

---

# 55. Security Event Types

Examples:

```text
auth.application_bootstrap

auth.session_seen

auth.account_suspended

auth.account_reactivated

auth.invalid_token

auth.invalid_authorized_party

auth.organization_denied

auth.location_denied

auth.permission_denied

auth.context_switched

auth.webhook_received

auth.webhook_processed

auth.webhook_failed

auth.webhook_duplicate
```

---

# 56. Security Event Indexes

```sql
CREATE INDEX auth_security_user_time_idx
ON auth_security_event(
    subject_user_id,
    occurred_at DESC
);
```

```sql
CREATE INDEX auth_security_type_time_idx
ON auth_security_event(
    event_type,
    occurred_at DESC
);
```

```sql
CREATE INDEX auth_security_request_idx
ON auth_security_event(request_id)
WHERE request_id IS NOT NULL;
```

Large future audit datasets can use time partitioning.

---

# 57. GET `/api/v1/auth/security-events`

Request:

```http
GET /api/v1/auth/security-events
?limit=50
&cursor=...

Authorization: Bearer <token>
```

Response:

```json
{
  "data": [
    {
      "id": "019...",
      "type": "auth.application_bootstrap",
      "severity": "info",
      "device": "Web browser",
      "occurred_at": "2026-09-16T08:00:00Z"
    }
  ],

  "meta": {
    "has_more": false,
    "next_cursor": null
  }
}
```

Expose only events appropriate for the end user.

Internal administrator audits belong to the dedicated Audit module.

---

# 58. Operational Logging

Every request should produce structured logging.

Example:

```json
{
  "timestamp": "2026-09-16T08:00:00Z",
  "level": "INFO",
  "service": "accounting-api",
  "environment": "production",

  "request_id": "019...",

  "method": "GET",
  "path": "/api/v1/auth/me",
  "status_code": 200,
  "duration_ms": 34,

  "user_id": "019...",
  "organization_id": "019...",
  "location_id": "019..."
}
```

---

# 59. Never Log

Never log:

```text
Authorization header
Clerk session JWT
password
OTP
TOTP secret
backup codes
verification codes
Clerk secret
database credentials
Redis credentials
raw cookie values
```

---

# 60. Audit Log vs Application Log

These are different systems.

## Application logs

Used for:

```text
debugging
latency
exceptions
operations
infrastructure
```

## Audit records

Used for:

```text
who
did what
when
where
within which tenant
against which resource
whether it succeeded
```

Accounting software requires this distinction from day one.

---

# 61. N+1 Prevention

Example `/auth/sessions`.

Bad:

```text
1 query sessions

20 queries users

20 queries devices
```

Good:

```text
1 indexed bounded query
```

Future organization/RBAC resolution should use:

```python
select_related(...)
```

and:

```python
prefetch_related(...)
```

where appropriate.

Do not use prefetch blindly; profile the actual query path.

---

# 62. Query Budgets

Add performance tests.

Starting targets:

```text
GET /auth/me

Cache hit:
0 DB queries ideally

Cache miss:
≤2 DB queries
```

```text
GET /auth/context

Cache hit:
0–1 DB queries

Cache miss:
≤4 DB queries
```

```text
GET /auth/sessions

≤2 DB queries
```

Number of SQL queries should not grow linearly with returned records.

---

# 63. Pagination

Use cursor pagination for chronological security data.

Example:

```text
?limit=50
&cursor=eyJ...
```

Maximum:

```text
sessions
50/request

security events
100/request
```

Avoid deep `OFFSET 500000`.

---

# 64. Rate Limiting

Suggested initial application policies:

| Endpoint | Initial limit |
|---|---:|
| `/auth/bootstrap` | 30/min/user |
| `/auth/me` | 180/min/user |
| `/auth/context` | 120/min/user |
| `/auth/context/switch` | 30/min/user |
| `/auth/sessions` | 60/min/user |
| `/auth/security-events` | 30/min/user |
| Clerk webhook | infrastructure-controlled |

Use:

```text
WAF
+
reverse proxy controls
+
Redis atomic limiter
+
DRF policy throttling
```

Numbers must eventually be tuned using production traffic.

---

# 65. Redis Failure

Redis is not the source of truth.

If Redis fails:

```text
user cache
→ PostgreSQL

authorization cache
→ PostgreSQL

session projection
→ PostgreSQL
```

Critical security behavior should not become permissive merely because Redis is unavailable.

---

# 66. Clerk Backend API Failure

Ordinary authenticated API requests should use networkless/local JWT verification where practical.

Therefore:

```text
Clerk Backend API temporarily unavailable
```

should not necessarily mean:

```text
all authenticated accounting APIs unavailable
```

This significantly improves resilience.

---

# 67. PostgreSQL Failure

A Clerk JWT may still be cryptographically valid while PostgreSQL is unavailable.

However Django cannot safely determine:

```text
organization membership
location membership
application suspension
custom roles
permissions
```

Therefore return:

```http
503 Service Unavailable
```

Do not bypass authorization.

---

# 68. Frontend 401 Handling

Frontend request interceptor:

```text
API request
    ↓
401
    ↓
force fresh Clerk token
    ↓
retry original request ONCE
```

If second request returns 401:

```text
clear application state
      ↓
return to login
```

Never create an infinite refresh loop.

---

# 69. Frontend Bootstrap

Recommended application initialization:

```text
Clerk ready
    ↓
authenticated?
 ┌──┴──┐
no    yes
│      │
login  getToken()
       │
       ▼
POST /api/v1/auth/bootstrap
       │
       ▼
load application shell
```

Avoid:

```text
/me
/organizations
/locations
/roles
/permissions
/profile
/settings
```

as six mandatory serial API calls before the dashboard appears.

Bootstrap should provide the minimum information required to initialize the application.

---

# 70. Frontend State

Frontend may cache:

```text
application user ID
display name
current organization
current location
role labels
authorization version
```

Frontend must not treat cached role or permission information as authoritative.

Every sensitive Django endpoint performs server-side authorization.

---

# 71. Security Principle

Never implement:

```javascript
if (user.role === "admin") {
    showButton()
}
```

and consider the resource secure.

Frontend condition:

```text
controls presentation
```

Backend condition:

```text
controls authorization
```

Both should exist.

Only the backend decision provides security.

---

# 72. MFA

Because this is accounting software, MFA should be strongly supported.

Clerk remains responsible for:

```text
MFA enrollment
second-factor challenge
factor validation
recovery
```

Django should never store the factor secret.

Our custom UI simply presents the Clerk authentication states.

---

# 73. Enterprise SSO

Future enterprise customers may use:

```text
Microsoft Entra ID
Google Workspace
Okta
other SAML/OIDC providers
```

Architecture remains:

```text
Enterprise Identity Provider
        ↓
Clerk
        ↓
Clerk Session
        ↓
Django
        ↓
Accounting RBAC
```

Therefore accounting modules remain independent from the identity-provider implementation.

---

# 74. User Deletion

When Clerk reports:

```text
user.deleted
```

do not immediately hard-delete accounting audit relationships.

Accounting data may legally and operationally require historical actor information.

Recommended application handling:

```text
Clerk user deleted
       ↓
local AuthUser
status = deleted
       ↓
remove active access
       ↓
retain immutable identifiers
       ↓
anonymize personal fields according to policy
```

Actual retention rules must later be defined per jurisdiction.

---

# 75. Privacy Design

Because the platform targets multiple jurisdictions, authentication should use data minimization.

Store only what application functionality requires.

For example:

```text
Clerk ID
internal user UUID
display identity
verified email status
locale
timezone
application status
```

Avoid unnecessarily copying Clerk's complete user profile.

---

# 76. Observability

Recommended:

```text
Prometheus
Grafana
Sentry
OpenTelemetry
structured JSON logs
```

Metrics:

```text
auth_requests_total

auth_401_total

auth_403_total

auth_token_verification_seconds

auth_bootstrap_seconds

auth_context_resolution_seconds

auth_cache_hits_total

auth_cache_misses_total

auth_webhook_received_total

auth_webhook_failed_total

auth_webhook_processing_seconds

auth_jit_provision_total
```

---

# 77. Authentication Operations Dashboard

Internal enterprise dashboard should eventually show:

```text
active application users

active session projections

invalid JWT rate

401 rate

403 rate

application-suspended users

authentication request volume

context resolution latency

Redis hit ratio

webhook success/failure

webhook backlog

Celery queue depth

JIT provisioning events
```

Filters:

```text
date/time

organization

location

environment
```

where applicable.

---

# 78. Performance Objectives

Initial engineering objectives:

| Operation | p95 target |
|---|---:|
| JWT verification | `<15 ms` |
| Cached user resolution | `<10 ms` |
| `/auth/me` | `<100 ms` |
| `/auth/context` cached | `<100 ms` |
| Bootstrap | `<200 ms` |
| Redis lookup | `<10 ms` |

These are internal engineering targets, not guarantees.

Validate with load testing.

---

# 79. Django Folder Architecture

```text
apps/
└── authentication/
    │
    ├── api/
    │   └── v1/
    │       ├── urls.py
    │       ├── views.py
    │       ├── serializers.py
    │       └── pagination.py
    │
    ├── authenticators/
    │   └── clerk.py
    │
    ├── models/
    │   ├── user.py
    │   ├── session_projection.py
    │   ├── security_event.py
    │   ├── provider_event.py
    │   └── idempotency.py
    │
    ├── services/
    │   ├── identity_service.py
    │   ├── bootstrap_service.py
    │   ├── context_service.py
    │   ├── session_service.py
    │   ├── security_service.py
    │   ├── webhook_service.py
    │   └── cache_service.py
    │
    ├── selectors/
    │   ├── identity.py
    │   ├── sessions.py
    │   └── security.py
    │
    ├── webhooks/
    │   ├── clerk.py
    │   └── handlers.py
    │
    ├── tasks/
    │   ├── webhook_tasks.py
    │   ├── security_tasks.py
    │   └── maintenance_tasks.py
    │
    ├── middleware/
    │   ├── request_id.py
    │   └── context.py
    │
    ├── permissions/
    │   └── authenticated.py
    │
    ├── exceptions.py
    ├── constants.py
    ├── metrics.py
    └── tests/
        ├── unit/
        ├── integration/
        ├── contract/
        ├── security/
        └── performance/
```

---

# 80. Authentication URLs

Django:

```python
urlpatterns = [

    path(
        "bootstrap",
        BootstrapAPIView.as_view(),
        name="auth-bootstrap",
    ),

    path(
        "me",
        MeAPIView.as_view(),
        name="auth-me",
    ),

    path(
        "context",
        AuthContextAPIView.as_view(),
        name="auth-context",
    ),

    path(
        "context/switch",
        SwitchContextAPIView.as_view(),
        name="auth-context-switch",
    ),

    path(
        "sessions",
        SessionListAPIView.as_view(),
        name="auth-sessions",
    ),

    path(
        "security-events",
        SecurityEventListAPIView.as_view(),
        name="auth-security-events",
    ),
]
```

Webhook separately:

```python
path(
    "api/v1/webhooks/clerk",
    ClerkWebhookAPIView.as_view(),
)
```

No:

```text
/login
/logout
/refresh
/signup
```

routes are created in Django.

---

# 81. `.env` Structure

```dotenv
# ============================================================
# APPLICATION
# ============================================================

APP_NAME=universal-accounting-api
APP_ENV=production
APP_VERSION=2.0.0

DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=

DEBUG=false

API_BASE_URL=https://api.example.com
FRONTEND_URL=https://app.example.com

ALLOWED_HOSTS=api.example.com

CORS_ALLOWED_ORIGINS=https://app.example.com

CSRF_TRUSTED_ORIGINS=https://app.example.com


# ============================================================
# POSTGRESQL
# ============================================================

DATABASE_URL=

DB_CONN_MAX_AGE=60

DB_CONNECT_TIMEOUT_SECONDS=5

DB_STATEMENT_TIMEOUT_MS=15000


# ============================================================
# CLERK
# ============================================================

CLERK_PUBLISHABLE_KEY=

CLERK_SECRET_KEY=

CLERK_JWT_KEY=

CLERK_ISSUER=

CLERK_WEBHOOK_SIGNING_SECRET=

CLERK_AUTHORIZED_PARTIES=https://app.example.com

CLERK_VERIFY_AUTHORIZED_PARTY=true

CLERK_CLOCK_SKEW_MS=5000


# ============================================================
# REDIS
# ============================================================

REDIS_URL=

REDIS_KEY_PREFIX=acct

AUTH_USER_CACHE_TTL_SECONDS=300

AUTH_CONTEXT_CACHE_TTL_SECONDS=180

AUTH_NEGATIVE_CACHE_TTL_SECONDS=20

CACHE_TTL_JITTER_PERCENT=10


# ============================================================
# CELERY
# ============================================================

CELERY_BROKER_URL=

CELERY_RESULT_BACKEND=

CELERY_TASK_ACKS_LATE=true

CELERY_WORKER_PREFETCH_MULTIPLIER=1

CELERY_TASK_TIME_LIMIT=300

CELERY_TASK_SOFT_TIME_LIMIT=270


# ============================================================
# IDEMPOTENCY
# ============================================================

IDEMPOTENCY_ENABLED=true

IDEMPOTENCY_RECORD_TTL_SECONDS=86400

IDEMPOTENCY_LOCK_TTL_SECONDS=60


# ============================================================
# APPLICATION SECURITY
# ============================================================

PII_HMAC_KEY=

FIELD_ENCRYPTION_KEY=

AUTH_SESSION_PROJECTION_ENABLED=true

AUTH_REQUIRE_CONTEXT_FOR_TENANT_APIS=true


# ============================================================
# RATE LIMITS
# ============================================================

AUTH_BOOTSTRAP_RATE_LIMIT=30/min

AUTH_ME_RATE_LIMIT=180/min

AUTH_CONTEXT_RATE_LIMIT=120/min

AUTH_CONTEXT_SWITCH_RATE_LIMIT=30/min

AUTH_SECURITY_EVENTS_RATE_LIMIT=30/min


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL=INFO

LOG_FORMAT=json

LOG_PII=false


# ============================================================
# SENTRY
# ============================================================

SENTRY_DSN=

SENTRY_ENVIRONMENT=production

SENTRY_TRACES_SAMPLE_RATE=


# ============================================================
# OPEN TELEMETRY
# ============================================================

OTEL_ENABLED=true

OTEL_SERVICE_NAME=universal-accounting-api

OTEL_EXPORTER_OTLP_ENDPOINT=


# ============================================================
# SECURITY EVENT STORAGE
# ============================================================

SECURITY_EVENT_RETENTION_DAYS=

PROVIDER_EVENT_RETENTION_DAYS=

AUDIT_HASH_IP_ADDRESSES=true

AUDIT_HASH_USER_AGENTS=true
```

Production secrets should come from a secret manager rather than a committed `.env`.

---

# 82. Required Database Constraints

At minimum:

```text
UNIQUE auth_user.clerk_user_id
```

```text
UNIQUE auth_session_projection.clerk_session_id
```

```text
UNIQUE (
    auth_provider_event.provider,
    auth_provider_event.external_event_id
)
```

All foreign keys should use explicit deletion policies.

For accounting audit relationships, avoid unrestricted cascade deletion.

---

# 83. Async Strategy

Do not make everything asynchronous merely because Celery exists.

Synchronous request:

```text
JWT verification
local user lookup
authorization
RLS
small indexed queries
```

Celery:

```text
webhook processing
security notifications
reconciliation
cleanup
long-running synchronization
audit enrichment
```

This keeps normal API behavior predictable and fast.

---

# 84. Reconciliation

Because webhooks can fail, implement a low-frequency repair mechanism.

For example:

```text
recent identity records
       ↓
identify inconsistency
       ↓
selectively reconcile
```

Do not:

```text
download all Clerk users every minute
```

or repeatedly synchronize identity data when nothing changed.

---

# 85. Authentication Security Tests

Required tests:

```text
valid Clerk token accepted

expired token rejected

wrong issuer rejected

wrong authorized party rejected

missing token rejected

suspended application user rejected

cross-organization access rejected

cross-location access rejected

duplicate webhook ignored safely

webhook signature failure rejected

JIT/webhook race does not duplicate user

Redis failure uses DB fallback

cache invalidates after authorization change

RLS prevents tenant leakage

idempotency replay returns same result

idempotency key + different payload rejected
```

---

# 86. Load Tests

Test:

```text
1,000 simultaneous /auth/me requests

organization context lookup

location switching

Redis cache miss storm

Redis unavailable

webhook burst

Celery webhook backlog

database connection pressure
```

Validate:

```text
latency
query count
Redis usage
CPU
memory
database connections
Celery throughput
```

---

# 87. Authentication Module Boundary

After implementation, authentication should work as:

```text
CUSTOM SIGN-UP UI
       ↓
CLERK

CUSTOM LOGIN UI
       ↓
CLERK

PASSWORD / MFA
       ↓
CLERK

SESSION + JWT
       ↓
CLERK

APPLICATION BOOTSTRAP
       ↓
DJANGO

CURRENT USER
       ↓
DJANGO

TENANT / LOCATION CONTEXT
       ↓
DJANGO

CUSTOM RBAC
       ↓
DJANGO

POSTGRESQL RLS
       ↓
DATABASE

LOGOUT
       ↓
CLERK

TOKEN REFRESH
       ↓
CLERK
```

---

# 88. Final API Boundary

## Clerk / Custom Frontend

```text
Sign Up

Login

Logout

Email Verification

Forgot Password

Reset Password

MFA

OTP

Passkeys

SSO

Token Refresh
```

## Django Authentication API

```text
POST
/api/v1/auth/bootstrap

GET
/api/v1/auth/me

GET
/api/v1/auth/context

POST
/api/v1/auth/context/switch

GET
/api/v1/auth/sessions

GET
/api/v1/auth/security-events

POST
/api/v1/webhooks/clerk
```

This is the final recommended boundary.

---

# 89. Architecture to Reuse Across the Accounting Platform

All future protected modules should receive the same trusted context:

```text
request.user

request.auth.clerk_user_id

request.auth.clerk_session_id

request.organization

request.location

request.authorization

request.request_id
```

Therefore:

```text
Customers
Vendors
Invoices
Quotations
Expenses
Payments
Refunds
Credit Notes
Taxes
Banking
Cash Flow
Reports
Notifications
Emails
Audit
```

do not implement authentication themselves.

They simply consume this identity/security layer.

---

# 90. Recommended Next Architecture Layer

The authentication module should be implemented first.

The next architectural dependency should be:

```text
Authentication
      ↓
Organization / Tenant Management
      ↓
Office / Location Management
      ↓
Enterprise RBAC & Custom Permissions
      ↓
Accounting Core
```

Do not start designing invoices or accounting ledgers before tenant, location and authorization boundaries are finalized, because almost every financial record will depend on:

```text
organization_id
location_id
created_by
authorization scope
RLS policy
audit context
```

That foundation will determine whether the accounting platform remains secure and manageable when it grows from one small business to thousands of organizations.