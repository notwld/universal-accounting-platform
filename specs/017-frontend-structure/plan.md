# Implementation Plan: Frontend production folder structure

**Branch**: `017-frontend-structure` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

## Summary

Reorganize the Next.js scaffold so `app/` is routing-only and infra lives in `lib/` / `components/` / `stores/` / `types/`. No new screens.

## Technical Context

**Language/Version**: TypeScript 5, Next.js 16 App Router

**Primary Dependencies**: existing (axios, TanStack Query, Zod, Zustand, shadcn)

**Storage**: N/A

**Testing**: `pnpm build`

**Target Platform**: Browser, port 5173

**Project Type**: web app

**Constraints**: Ponytail ultra — no empty feature folders; URLs unchanged.

**Scale/Scope**: scaffold only

## Constitution Check

Reuse Organization header and Clerk later. No new Django apps. No claimed tax compliance.

## Project Structure

```text
frontend/src/
  app/
    layout.tsx
    globals.css
    error.tsx
    (app)/page.tsx
  components/
    providers.tsx
    ui/
  lib/
    env.ts
    utils.ts
    query.ts
    api/client.ts
    api/keys.ts
  stores/org.ts
  types/api.ts
```
