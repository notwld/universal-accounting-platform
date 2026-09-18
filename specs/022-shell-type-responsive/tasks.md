# Tasks: Shell typography and responsive polish

**Input**: specs/022-shell-type-responsive/

## Phase 1: Foundational

- [x] T001 Swap Geist → IBM Plex Sans/Mono in `frontend/src/app/layout.tsx` and wire CSS vars in `frontend/src/app/globals.css`
- [x] T002 Add global `prefers-reduced-motion` rules in `frontend/src/app/globals.css`

## Phase 2: US1 Typography

- [x] T003 Ensure dashboard/auth/org surfaces use `tabular-nums` / mono where metrics appear

## Phase 3: US2 Responsive shell

- [x] T004 Refactor `app-shell` / `app-sidebar` / `app-header` for &lt;1024px drawer with menu toggle and backdrop
- [x] T005 Responsive padding/stacking on `dashboard-home.tsx`, `org-picker.tsx`, `auth-shell.tsx`

## Phase 4: US3 Motion

- [x] T006 Drawer/open-nav transitions; keep accordion transitions; respect reduced-motion

## Phase 5: Verify

- [x] T007 Manual check: 375px drawer, 768px stack, desktop sidebar unchanged colors
