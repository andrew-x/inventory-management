---
name: saas-ui-redesign
description: Use when asked to redesign, modernize, restyle, or polish this repo's Vue 3 client — replacing the top nav bar with a vertical left sidebar, making spacing consistent, or giving the UI a modern SaaS look.
---

# SaaS UI Redesign — Vue 3 Client

## Overview

Converts the client from a horizontal top-nav layout to a modern SaaS shell: dark
vertical sidebar on the left, light canvas, white cards, consistent spacing driven
by tokens.

**Core principle: the shell moves, the primitives stay.**

`client/src/App.vue`'s `<style>` block is **unscoped and load-bearing**. It defines
`.page-header`, `.stats-grid`, `.stat-card`, `.card`, `.card-header`, `.card-title`,
table styles, `.badge.*`, `.loading`, `.error` — every view consumes these class
names. Change the nav rules and the *values* inside the primitives. Never rename or
delete a primitive class, or all seven views break at once.

## Five Gates

These are the steps agents skip. Each is non-negotiable.

1. **Delegate every `.vue` write to `vue-expert`.** The root `CLAUDE.md` marks this
   MANDATORY for any file you create or significantly modify. This redesign touches
   at least nine `.vue` files. Delegate per file, not in one batch.
2. **Verify with Playwright MCP, never by hand.** `CLAUDE.md` mandates
   `mcp__playwright__*` against `http://localhost:3000`. "Manually click through the
   routes" is not verification.
3. **Every new copy key lands in BOTH `en.js` and `ja.js`.** Same key, same shape.
4. **Sweep the views. Spacing does not improve for free.** See the rationalization
   table below.
5. **Do not change `FilterBar`'s contract.** Restyle and relocate it; leave its
   `useFilters` bindings, the `'all'` sentinel handling, and `resetFilters` alone.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "Views inherit the global tokens, so tightening App.vue fixes spacing for free" | False. Each view has its own `<style scoped>` block with hardcoded rem values in view-specific grids and cards. Those inherit nothing. Phase 5 is required work, not polish. |
| "Responsive collapse is a stretch goal" | It is in scope. The app has zero `@media` queries today — that is the gap to close, not a reason to defer. |
| "Modals are `position: fixed`, so the shell change doesn't affect them" | Layout-unaffected is not the same as in-spec. Six modals each redeclare `.modal-overlay`; they are part of the restyle. |
| "Backlog.vue isn't routed, so leave it" | Correct to not link it from the sidebar. Still restyle it — it is a real view and it uses `.page-header`. |
| "I'll add icons with emoji for speed" | `CLAUDE.md` bans emojis in the UI. Inline SVG only. |
| "I'll pull in an icon library / Tailwind" | No new dependencies. This repo hand-rolls all CSS and all icons. |

## Workflow

### Phase 0 — Preflight
Run `./scripts/start.sh` (logs to `/tmp/inventory-*.log`). Confirm `:3000` and
`:8001` respond. Work on a branch. Screenshot the current UI via Playwright as a
before-reference.

### Phase 1 — Tokens
Add a `:root` block at the top of `App.vue`'s global `<style>`. Define tokens
(see Design System below), then rewrite the existing primitives to reference them.
Class names and visual output stay the same. Nothing else changes in this phase.

### Phase 2 — Sidebar shell
Create `client/src/components/Sidebar.vue` (scoped styles). Move the brand block,
the six `router-link`s, `LanguageSwitcher`, and `ProfileMenu` into it. Re-emit
`show-profile-details` and `show-tasks` so `App.vue`'s existing task CRUD is
untouched.

In `App.vue`: replace `<header class="top-nav">` with `<Sidebar />`, change `.app`
from a flex column to a two-column shell, and delete the `.top-nav`, `.nav-container`,
`.logo`, `.subtitle`, `.nav-tabs` rules. Add the `nav.reports` key rather than
carrying the hardcoded `Reports` literal across.

### Phase 3 — Responsive collapse
Icon rail below the breakpoint. Inline SVG icons at 20×20, `stroke="currentColor"`,
matching the existing hand-authored style in `FilterBar.vue` and `ProfileMenu.vue`.
Collapse state is a local `ref` plus a class; persist to `localStorage`.
`aria-label` on the toggle, `aria-current="page"` on the active link.

### Phase 4 — Chrome
`FilterBar.vue`: change `top: 70px` to `top: 0` and re-token its padding. Restyle
`ProfileMenu.vue` and `LanguageSwitcher.vue` as full-width footer rows whose
dropdowns open **upward** (`bottom: calc(100% + 0.5rem)`, not `top:`) — they now sit
at the bottom of the viewport. Keep the popovers light-on-white for legibility; only
the always-visible trigger goes light-on-dark. Then the six modals: one
`.modal-overlay` definition, tokenized padding and radius.

### Phase 5 — View sweep
All eight views, **one at a time, each delegated to `vue-expert`**:
`Dashboard.vue`, `Spending.vue`, `Reports.vue`, `Restocking.vue`, `Demand.vue`,
`Inventory.vue`, `Orders.vue`, `Backlog.vue`.

Per view: replace hardcoded rem values in the scoped block with spacing tokens,
align card padding and radius to the spec, confirm the `.page-header` block matches
the standard pattern, and point hand-written SVG chart colors at tokens instead of
inline hexes.

### Phase 6 — i18n parity
```bash
cd client/src/locales && comm -3 \
  <(grep -oE "^[[:space:]]*[A-Za-z0-9_]+:" en.js | tr -d ' :' | sort -u) \
  <(grep -oE "^[[:space:]]*[A-Za-z0-9_]+:" ja.js | tr -d ' :' | sort -u) \
  | grep -vE "productNames|customerNames"
```
Any key this reports is a bug. `productNames` and `customerNames` are filtered out
because they are **intentionally ja-only** — they are data-value translation maps,
not UI copy, and have no English counterpart by design. Expect empty output.

Two distinct paths, do not confuse them:
- **UI copy** (nav labels, button text, aria-labels) → a key in **both** `en.js` and `ja.js`.
- **Data values** (product names, customer names, warehouses) → the
  `translateProductName` / `translateCustomerName` / `translateWarehouse` maps.

Known pre-existing gap this phase should close: `nav.reports` is missing from both
files, so the check will *not* flag it. Add it to both.

### Phase 7 — Verify
Playwright MCP over all seven routes (`/`, `/inventory`, `/orders`, `/demand`,
`/restocking`, `/spending`, `/reports`; `Backlog.vue` has no route — do not link it from the sidebar
unless you add one to `main.js`). For each: screenshot at wide and narrow widths,
confirm the console is clean.

Then exercise the thing most likely to have silently broken: change each of the four
filters and confirm the views still react. A redesign that breaks filtering looks
perfect in a screenshot.

## Design System

### Tokens
```css
:root {
  /* surface */
  --sidebar-bg: #0f172a;      /* dark rail */
  --canvas: #f8fafc;          /* app background */
  --surface: #ffffff;         /* cards */
  --border: #e2e8f0;
  --border-strong: #cbd5e1;

  /* text */
  --text: #0f172a;
  --text-muted: #64748b;
  --text-on-dark: #cbd5e1;
  --text-on-dark-active: #ffffff;

  /* accent — already the app's blue, keep it */
  --accent: #2563eb;
  --accent-soft: #eff6ff;

  /* status — match existing badge palette */
  --success: #059669;
  --warning: #ea580c;
  --danger: #dc2626;

  /* spacing — 4px base, use these everywhere */
  --space-1: 0.25rem;  --space-2: 0.5rem;   --space-3: 0.75rem;
  --space-4: 1rem;     --space-5: 1.25rem;  --space-6: 1.5rem;
  --space-8: 2rem;     --space-10: 2.5rem;

  --radius-sm: 6px; --radius-md: 8px; --radius-lg: 10px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.05);
  --shadow-md: 0 4px 12px rgba(0,0,0,.06);

  --sidebar-w: 260px;
  --sidebar-w-collapsed: 72px;
  --content-max: 1600px;
  --topbar-h: 56px;
}
```

`--content-max` replaces the `1600px` literal currently duplicated in three places.
`--topbar-h` replaces the `70px` literal duplicated in two.

### Layout shell
```
.app-shell   display: grid; grid-template-columns: var(--sidebar-w) 1fr; min-height: 100vh
.sidebar     sticky, top 0, height 100vh, --sidebar-bg, flex column
.app-main    min-width: 0   /* required — without it wide tables blow out the grid */
.main-content max-width: var(--content-max); padding: var(--space-6) var(--space-8)
```

`min-width: 0` on the content column is not optional. A CSS Grid track defaults to
`min-width: auto`, so one wide table pushes the whole column past the viewport.

### Sidebar
| Property | Expanded | Collapsed |
|---|---|---|
| Width | `--sidebar-w` | `--sidebar-w-collapsed` |
| Item | icon + label | icon only, label removed from flow |
| Item height | 40px, `--space-2` gap | 40px, centered |
| Active | `--text-on-dark-active` + `rgba(37,99,235,.15)` fill + 2px left accent bar | same, bar only |
| Hover | `rgba(255,255,255,.06)` | same |
| Footer | language + profile rows, dropdowns open upward | icon triggers |

### Z-index scale
Declare it once and use it; do not invent new values.
```
sidebar 100 · filter bar 90 · dropdowns 1000 · modals 2000
```

### Repeating patterns
- **Page header** — `<div class="page-header"><h2>title</h2><p>subtitle</p></div>`,
  `margin-bottom: var(--space-6)`. Every view already opens this way; keep it.
- **Card** — `--surface`, `1px solid var(--border)`, `--radius-lg`,
  `padding: var(--space-5)`, `--shadow-sm`; `--shadow-md` and `--border-strong` on hover.
- **Table** — `thead` on `--canvas`, uppercase `0.75rem` `--text-muted` headers,
  `--space-2 --space-3` cells, `--border` hairlines, row hover `--canvas`.
- **Control** — `--radius-sm`, `1px solid var(--border-strong)`, focus ring
  `0 0 0 3px rgba(37,99,235,.1)`. Matches `.filter-select` today.

## Script Conventions

The repo is **mixed**. Verified split:

| Style | Files |
|---|---|
| `setup()` + explicit return | `App.vue`, `FilterBar.vue`, and all 8 views |
| `<script setup>` | `ProfileMenu.vue`, `LanguageSwitcher.vue`, `ProfileDetailsModal.vue`, and 4 of the 6 detail modals |

**Preserve each file's existing style.** This redesign is a restyle — rewriting a
working `<script setup>` component into `setup()` (or the reverse) is unrequested
churn that buries the actual CSS diff in review.

The root `CLAUDE.md` says "all views are Composition API via `setup()` with an
explicit return." That is accurate **for views** — do not generalize it to components.

New `Sidebar.vue` uses `setup()` with an explicit return, matching `App.vue` and
`FilterBar.vue`, the shell files it sits beside.

## Repo Landmines

Verified facts about this codebase. Check them before assuming.

- `FilterBar.vue` is `position: sticky; top: 70px` — pinned to the top nav's height.
  Removing the nav without fixing this leaves it stuck to nothing.
- `Backlog.vue` exists but has **no route** in `main.js`. Do not add a sidebar link
  to it without adding the route. `Restocking.vue` *is* routed (`/restocking`) and
  needs a sidebar link.
- `client/index.html` loads **no webfont**. `App.vue` declares `Inter` in its
  font-family stack, so the app has always fallen back to system fonts. Any typeface
  choice requires adding a `<link>` to `index.html`.
- `nav.reports` is missing from `en.js` and `ja.js`; `App.vue` hardcodes `Reports`.
- All six modals redeclare `.modal-overlay` in their own scoped blocks.
- The app has **zero `@media` queries**. Phase 3 introduces the first ones.
- `Dashboard.vue` **redeclares `.page-header` locally at line 730** inside its scoped
  block, shadowing the global rule. Reconcile it in Phase 5 rather than tokenizing
  both copies and leaving them to drift.
- **Removing `text-transform: uppercase` exposes the source string's real case.**
  Labels written lowercase in `en.js` (e.g. `trends: { increasing: 'increasing' }`)
  looked fine while CSS shouted them and read as broken once it stopped. After the
  anti-tell pass, re-read the rendered labels and fix the *strings*, not the CSS.
  Sibling blocks like `status:` are already Title Case — match them. Fragments that
  sit mid-sentence (`'units short'`, `'margin'`) stay lowercase.
- The four `FilterBar` selects need ~800px in one row. The content column must let
  them **wrap**, or the last filters are clipped off-screen at narrow widths —
  independent of whether the sidebar collapsed.
- A stored `localStorage['sidebar-collapsed']` preference overrides viewport
  auto-collapse permanently. Clear it before testing responsive behavior, or you
  will test the wrong path.
- `purchase_orders.json` is empty, so `has_purchase_order` is always `false` — the
  backlog UI has no populated state to style against.

## Red Flags — stop

- About to edit a `.vue` file without `vue-expert`
- About to verify by describing what the page "should" look like
- About to add an emoji, an icon package, or Tailwind
- About to add a key to `en.js` only
- About to call the redesign done without changing a filter and watching a view react
- About to skip a view because "it inherits the global styles"
- Normalizing a file's `<script>` style. The repo is **mixed** — preserve what each
  file already uses (see Script Conventions). Nobody asked you to unify it.
