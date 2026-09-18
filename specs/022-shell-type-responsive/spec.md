# Feature Specification: Shell typography and responsive polish

**Feature Branch**: `022-shell-type-responsive`

**Created**: 2026-09-18

**Status**: Ready for planning

**Input**: User description: "See finance-frontend-zoho-books-parity-plan.md but keep current style/design; change font; use taste-skill; fully responsive frontend; best UI/UX; transitions where needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Distinct product typography (Priority: P1)

Signed-in users see UAP Books with a clear, finance-appropriate typeface (not the previous default stack). Numbers stay tabular and readable.

**Why this priority**: Typography is the only visual change the user explicitly requested while keeping current colors and layout language.

**Independent Test**: Open sign-in, org picker, and dashboard; confirm body and headings use the new family and metrics align.

**Acceptance Scenarios**:

1. **Given** any authenticated or auth screen, **When** the page loads, **Then** UI text uses the product sans family and code/numeric UI can use mono/tabular figures.
2. **Given** the dashboard metric placeholders, **When** viewed, **Then** numeric placeholders use tabular numerals.

---

### User Story 2 - Usable shell on phone and tablet (Priority: P1)

Users on viewports under ~1024px can open navigation without a permanently visible desktop sidebar; content stacks; primary actions remain reachable.

**Why this priority**: Parity plan §3.2 and UX research both require mobile-specific shell behavior, not a squished desktop layout.

**Independent Test**: Resize to 375px and 768px; open/close nav; complete org pick and view dashboard.

**Acceptance Scenarios**:

1. **Given** viewport &lt; 1024px, **When** the dashboard loads, **Then** the sidebar is hidden behind a menu control and opens as an overlay/drawer.
2. **Given** the drawer is open, **When** the user chooses a destination or dismisses, **Then** the drawer closes and focus returns to the page.
3. **Given** a narrow viewport, **When** viewing the dashboard, **Then** summary cards stack vertically without horizontal page scroll.

---

### User Story 3 - Purposeful motion (Priority: P2)

Interactive shell elements (nav accordion, drawer, hover/active controls) animate briefly; users who prefer reduced motion see minimal or no animation.

**Why this priority**: Improves perceived quality without changing product structure.

**Independent Test**: Toggle accordion and mobile drawer; enable prefers-reduced-motion and confirm animations are suppressed.

**Acceptance Scenarios**:

1. **Given** an accordion group, **When** expanded/collapsed, **Then** height/chevron animate within ~300ms.
2. **Given** prefers-reduced-motion, **When** the same actions occur, **Then** transitions are near-instant or disabled.

### Edge Cases

- Very wide screens: content remains readable with a max useful width.
- Drawer open while rotating device: drawer state remains coherent.
- Auth and org-picker screens remain usable at 320px width.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Replace the previous default UI font with a distinctive humanist sans suitable for dense B2B accounting UI; pair with a mono family for numeric/tabular contexts.
- **FR-002**: Preserve existing color tokens, brand chrome (dark header, light sidebar, blue active page), and information hierarchy — no Zoho asset copy, no redesign to dark navy sidebar unless already present.
- **FR-003**: Below 1024px, provide a collapsible navigation drawer with open/close control and backdrop dismiss.
- **FR-004**: Auth, org picker, and dashboard layouts must remain usable from 320px upward (stacking, padding, touch targets ≥ 44px where interactive).
- **FR-005**: Apply short CSS transitions for nav, drawer, and interactive controls; honor `prefers-reduced-motion`.
- **FR-006**: Do not ship incomplete Zoho parity modules; this feature is shell/typography/responsive polish only.

### Key Entities

- None (presentation-only change).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At 375×812 and 768×1024, dashboard and org picker require no horizontal page scrolling for primary content.
- **SC-002**: Mobile users can open and close navigation in under two taps/clicks.
- **SC-003**: Typography change is visible on all primary routes (sign-in, org picker, dashboard) without changing existing accent colors.
- **SC-004**: With reduced-motion preference enabled, shell animations do not run beyond negligible duration.

## Assumptions

- Keep current UAP visual language; parity plan informs responsive breakpoints and density, not a full visual restyle.
- taste-skill / redesign-existing-projects guide choices; dials: preserve layout (low variance), modest motion, higher density for product UI.
- IBM Plex Sans + IBM Plex Mono is an acceptable finance-appropriate pairing (tabular figures, not Inter/Geist defaults).
