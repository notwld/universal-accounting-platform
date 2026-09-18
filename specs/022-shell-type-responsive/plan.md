# Implementation Plan: Shell typography and responsive polish

**Branch**: `022-shell-type-responsive` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

## Summary

Keep current UAP shell colors and structure. Swap Geist → IBM Plex Sans/Mono. Add mobile nav drawer (&lt;1024px), stack dashboard/auth layouts, and add restrained transitions with reduced-motion support. Guided by taste-skill redesign-preserve + Zoho parity plan §3.2 breakpoints only.

## Technical Context

**Language/Version**: TypeScript / Next.js 16  
**Primary Dependencies**: Tailwind v4, shadcn, lucide-react, next/font (IBM Plex)  
**Storage**: N/A  
**Testing**: Manual viewport check (ponytail: no new test harness)  
**Target Platform**: Modern browsers, mobile + desktop  
**Project Type**: Web app (`frontend/`)  
**Constraints**: Speckit-first; ponytail ultra; no new UI libraries; no Zoho asset copying  
**Scale/Scope**: Shell + auth + org picker + dashboard only

## Constitution Check

Passes: presentation-only, no finance calculation changes, org isolation unchanged.

## Project Structure

### Documentation

```text
specs/022-shell-type-responsive/
├── spec.md
├── plan.md
├── research.md
├── tasks.md
└── checklists/requirements.md
```

### Source files to touch

- `frontend/src/app/layout.tsx` — fonts
- `frontend/src/app/globals.css` — font CSS vars, reduced-motion
- `frontend/src/features/shell/*` — drawer, header menu, responsive
- `frontend/src/features/orgs/org-picker.tsx` — responsive grid/padding
- `frontend/src/features/auth/auth-shell.tsx` — responsive card

## Design read (taste-skill)

Redesign-preserve of UAP Books accounting shell for SMB operators; trust-first dense product UI; keep current tokens; IBM Plex; shadcn.

**Dials**: VARIANCE 4 · MOTION 4 · DENSITY 7
