# Implementation Plan: Enterprise Auth & Identity

**Branch**: `001-enterprise-auth-identity` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

## Summary

Build Clerk-custom-UI + Django/DRF identity module per UAP Auth v2.0. Close gaps: org/location stubs, SMTP security mail, CORS hardening, STRIDE threat model.

## Technical Context

**Language/Version**: Python 3.12+ (venv); Node 20+ for frontend  
**Primary Dependencies**: Django 5.x, DRF, django-cors-headers, celery, redis, PyJWT, cryptography, httpx, django-environ, uuid6  
**Storage**: PostgreSQL (+ SQLite for local tests), Redis  
**Testing**: pytest-django  
**Target Platform**: ASGI (uvicorn/daphne) API + Vite/React SPA  
**Project Type**: monorepo `backend/` + `frontend/`  
**Performance Goals**: auth bootstrap p95 < 200ms excluding Clerk UI  
**Constraints**: no credential APIs in Django; JWT verify offline  
**Scale/Scope**: Auth module only (not full accounting)

## Constitution Check

- Auth separation: PASS  
- Speckit-first: PASS (this plan)  
- Ponytail ultra: lean services, no duplicate auth stacks  
- Tenant isolation: membership checks + RLS session vars  
- Privacy: hashed IP/UA, email HMAC/ciphertext helpers  

## Project Structure

```text
backend/
  config/                 # Django project settings
  apps/authentication/    # per MD §79
  apps/tenancy/           # org/location/membership stubs
  manage.py
frontend/
  src/account/            # custom Clerk login/signup
docs/security/STRIDE.md
docker-compose.yml
```

## Approach

1. Scaffold Django settings (dev/prod split), CORS, SMTP, Celery, Redis.
2. Models + migrations; DRF authenticator for Clerk JWT.
3. Services + API views matching catalogue.
4. Webhooks + Celery tasks (including SMTP security mail).
5. Frontend Clerk custom UI → bootstrap.
6. Tests + STRIDE mapping doc.

## Research Notes (gaps)

- **CORS**: exact `Access-Control-Allow-Origin`, `Allow-Credentials: true` only with allowlist; `Vary: Origin`; CORS ≠ CSRF.
- **SMTP**: port 587 STARTTLS or 465 SSL; authenticated relay; async send to avoid timing side-channels on sensitive paths.
- **STRIDE**: map Spoofing→JWT verify; Tampering→signed webhooks/idempotency; Repudiation→security_event; Info disclosure→no PII logs; DoS→rate limits; EoP→server-side membership/RBAC version.
