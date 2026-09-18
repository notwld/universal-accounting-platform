# Feature Specification: Docker app services

**Feature Branch**: `019-docker-apps`

**Created**: 2026-09-18

**Status**: Implemented

**Input**: Run backend and frontend in Docker alongside existing Postgres/Redis/Mailpit.

## User Scenarios & Testing

### User Story 1 - Full stack via compose (Priority: P1)

A developer runs `docker compose up` and reaches the API on 8000 and the UI on 5173 without local Node/Python servers.

**Independent Test**: `docker compose up -d --build` then HTTP 200 (or redirect) from `localhost:5173` and `localhost:8000/health/`.

## Requirements

- **FR-001**: Backend container serves the Django API on host port 8000.
- **FR-002**: Frontend container serves Next.js on host port 5173.
- **FR-003**: App containers use compose Postgres and Redis hostnames, not localhost.
- **FR-004**: Clerk and other secrets come from env files, not image layers.

## Success Criteria

- **SC-001**: Compose brings up postgres, redis, mailpit, backend, and frontend.
- **SC-002**: Sign-in page loads from the frontend container.

## Assumptions

- Dev compose uses hot-reload volumes where cheap; production hardening is later.
- Migrations run on backend start.

## Out of Scope

- Celery workers in compose, multi-env prod overlays, Kubernetes.
