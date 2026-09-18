# Research: Shell typography and responsive polish

## Decision: IBM Plex Sans + IBM Plex Mono

- Finance/dashboard UX guidance favors humanist sans + mono/tabular numerals for dense metrics.
- Avoids Inter/Geist as overused AI defaults (taste-skill / redesign audit).
- Available via `next/font/google` with no new npm package.

## Decision: Drawer below 1024px

- Aligns with parity plan §3.2 and mobile SaaS dashboard practice: do not squish a permanent sidebar.
- Overlay drawer + backdrop; close on navigate/escape/backdrop.

## Decision: CSS transitions only

- No GSAP (taste-skill landing-oriented; product shell needs light motion).
- Accordion already uses grid-rows; add drawer transform/opacity; honor `prefers-reduced-motion`.

## Out of scope

- Full Zoho module parity, dark navy sidebar restyle, fake financial amounts.
