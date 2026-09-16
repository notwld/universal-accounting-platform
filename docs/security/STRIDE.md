# STRIDE Threat Model — Auth & Identity Module

**Scope**: Custom Clerk UI → Clerk → Django `/api/v1/auth/*` + webhook.  
**Date**: 2026-09-16  
**Method**: Microsoft STRIDE per trust boundary.

## Trust boundaries

1. Browser ↔ Clerk (credentials, session)
2. Browser ↔ Django API (Bearer JWT, CORS)
3. Clerk ↔ Django webhook (Svix signature)
4. Django ↔ PostgreSQL / Redis / SMTP

---

| ID | Threat | Asset / Flow | Mitigation (code) |
|---|---|---|---|
| S1 | Spoofing — forged Bearer JWT | API auth | Local JWKS/JWT verify: iss, signature, exp/nbf, optional azp (`authenticators/clerk.py`) |
| S2 | Spoofing — fake org/location headers | Tenant context | Membership check server-side; never trust headers alone (`context_service.py`) |
| S3 | Spoofing — forged webhook | Clerk sync | Svix/Clerk signing secret verification (`webhooks/clerk.py`) |
| T1 | Tampering — replayed bootstrap | Bootstrap | Idempotency-Key + request hash conflict (`idempotency`) |
| T2 | Tampering — JWT claim RBAC | Authorization | Roles/version only from Django DB, not JWT (`bootstrap_service`) |
| T3 | Tampering — email at rest | User PII | HMAC lookup + optional Fernet ciphertext (`crypto.py`) |
| R1 | Repudiation — denied login/switch | Audit | `security_event` rows for bootstrap, switch, suspend (`security_service`) |
| R2 | Repudiation — webhook processing | Provider sync | Unique `(provider, external_event_id)` + processed_at |
| I1 | Info disclosure — logs | Secrets/PII | Structured logs; never log JWT/raw email/webhook body secrets |
| I2 | Info disclosure — CORS * | Browser | Exact origin allowlist; no `*` with credentials |
| I3 | Info disclosure — verbose errors | API | Standard error catalogue; no stack traces in prod |
| D1 | DoS — bootstrap flood | Auth API | Rate limits per endpoint (`AUTH_*_RATE_LIMIT`) |
| D2 | DoS — cache stampede | Redis | Lock + negative cache TTL jitter |
| D3 | DoS — SMTP stall | Request path | Email via Celery only; bootstrap never waits on SMTP |
| E1 | Elevation — self-grant role | RBAC | No client-writable roles; authz version bump on server |
| E2 | Elevation — cross-tenant location | Context switch | Location must belong to org + membership |

## SMTP (gap fill)

Clerk owns verification/OTP mail. Django SMTP is **only** for application security notifications (new session, context switch alerts). Always TLS; credentials from env/secret manager.

## CORS (gap fill)

- `CORS_ALLOWED_ORIGINS` exact list  
- `CORS_ALLOW_CREDENTIALS` true only if cookie flows needed (JWT Bearer default can keep credentials false; frontend uses Authorization header)  
- `CSRF_TRUSTED_ORIGINS` for cookie POSTs if added later  
- `Vary: Origin` via django-cors-headers

## Residual risk

- Compromised Clerk tenant admin → full IdP takeover (accepted; out of Django control).  
- JWKS cache poisoning if MITM to Clerk without TLS pinning (mitigate: HTTPS only, short cache TTL).
