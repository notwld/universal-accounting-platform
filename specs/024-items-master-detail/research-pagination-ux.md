# Research: Reusable list pagination UX (concrete)

**Date**: 2026-09-19

## Consensus (Elastic EUI, UX Patterns, SaaS table guides)

1. **Compact footer** near the list: rows-per-page + prev/next + visible range (`1 - 25`), not a bare `0`.
2. **Familiar page sizes only**: `10 / 25 / 50 / 100` (+ optional `200`). Default **25** for dense finance lists.
3. **Reset to page 1** when page size, search, or filters change.
4. **Disable** (don’t hide) prev on first / next on last — avoids layout shift.
5. **Searchable size menu** when options grow: Popover + Command (shadcn combobox pattern) with checkmark on current size — matches product screenshot.
6. Master-detail: list chrome fixed; **only rows scroll**; filters behind progressive disclosure icon.

## Implementation in UAP

- `PageSizePagination`: bordered split control (gear + “N per page” | range + chevrons).
- `MasterDetailWorkspace`: InputGroup search, Select filters, Field forms, Button actions — all shadcn.
