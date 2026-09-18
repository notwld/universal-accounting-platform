# Implementation Plan: Auth login and signup screens

**Branch**: `018-auth-screens` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

## Summary

Centered shadcn cards at `/sign-in` and `/sign-up`. Clerk when keys exist.

## Technical Context

**Language/Version**: TypeScript, Next.js 16 App Router

**Primary Dependencies**: shadcn card/input/label, react-hook-form, zod, @clerk/nextjs

**Storage**: Clerk (no local passwords)

**Testing**: `pnpm build`; open `/sign-in` and `/sign-up`

**Target Platform**: Browser, port 5173

## Project Structure

```text
src/app/(auth)/layout.tsx
src/app/(auth)/sign-in/page.tsx
src/app/(auth)/sign-up/page.tsx
src/features/auth/auth-shell.tsx
src/features/auth/login-form.tsx
src/features/auth/signup-form.tsx
src/features/auth/schema.ts
src/proxy.ts
```
