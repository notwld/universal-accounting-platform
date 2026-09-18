# Feature Specification: Frontend Next.js scaffold

**Feature Branch**: `016-frontend-scaffold`

**Created**: 2026-09-18

**Status**: Implemented

**Input**: Initialize Next.js in `frontend/`. Install axios, TanStack, shadcn/ui, Zod, Zustand, and libraries needed to call the existing Django API.

## User Scenarios & Testing

### User Story 1 - App boots (Priority: P1)

A developer can start the frontend and see a Next.js app with TypeScript, Tailwind, and shadcn.

**Independent Test**: `pnpm build` in `frontend/` succeeds.

## Requirements

- **FR-001**: Next.js App Router + TypeScript lives in `frontend/`.
- **FR-002**: axios, TanStack Query, Zod, Zustand, and shadcn/ui are installed and wired.
- **FR-003**: Dev server uses port 5173 so existing CORS and Clerk authorized parties still match.
- **FR-004**: No finance screens or mocked amounts in this slice.

## Success Criteria

- **SC-001**: Frontend production build completes without errors.

## Assumptions

- Clerk SDK is included because identity is Clerk; custom auth screens come later.
- React Hook Form + resolvers ship with shadcn forms.

## Out of Scope

- Zoho-parity shell, finance routes, generated OpenAPI client.
