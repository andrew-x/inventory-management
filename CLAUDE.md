# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System — a Claude Code workshop demo. Vue 3 + Vite frontend (port 3000), FastAPI backend (port 8001), JSON mock data loaded into memory (no database, no persistence).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

There are additional `CLAUDE.md` files in `client/` and `server/` with framework-level conventions for each side.

## Critical Tool Usage Rules

### Subagents
- **vue-expert**: **MANDATORY — any time you create or significantly modify a `.vue` file, delegate to vue-expert.** Also for reactivity issues and client-side state.
- **code-reviewer**: after writing significant code.
- **Explore**: for codebase structure questions and pattern searches.
- **general-purpose**: complex multi-step tasks that don't fit the above.

### Skills
- **backend-api-test**: use when writing or modifying tests in `tests/backend/`.

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations. Exception: creating local branches — use `git checkout -b`, not `mcp__github__create_branch`.
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing, against `http://localhost:3000` (frontend) and `http://localhost:8001` (API).

## Commands

```bash
./scripts/start.sh            # both servers + dep install; logs to /tmp/inventory-*.log
./scripts/stop.sh             # stops both, falls back to killing ports 3000/8001
```

macOS/Linux only. On Windows run the two servers manually:

```bash
cd server && uv venv && uv sync && uv run python main.py    # :8001, docs at /docs
cd client && npm install && npm run dev                      # :3000
npm run build                                                # -> client/dist/
```

### Tests

The test suite has no project file of its own — it must borrow the `server` project's venv, which holds the dev dependencies. **`cd tests && uv run pytest` fails** (`Failed to spawn: pytest`); use:

```bash
cd tests && uv run --project ../server pytest                       # all (94 tests)
cd tests && uv run --project ../server pytest backend/test_inventory.py
cd tests && uv run --project ../server pytest backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory
cd tests && uv run --project ../server pytest --cov=../server --cov-report=html
```

`tests/pytest.ini` sets `testpaths = backend` and `-v`, so paths are relative to `tests/`. `conftest.py` puts `server/` on `sys.path` and exposes a `client` fixture (FastAPI `TestClient`).

There is **no linter, formatter, type checker, or frontend test runner configured** in this repo. The `/test` and `/optimize` slash commands ask for linting anyway — don't invent a lint step; say it isn't set up.

## Architecture

### Filter system — the backbone of the app

Four filters (Time Period, Location/warehouse, Category, Order Status) live in `FilterBar.vue`, rendered once in `App.vue` above `<router-view>`, and drive every view.

`client/src/composables/useFilters.js` is a **module-scope singleton**: the four `ref`s are declared outside `useFilters()`, so every component that calls it shares the same state. There is no store; this is the global state.

Flow: `FilterBar` mutates the shared refs → each view `watch`es the subset of refs its endpoint supports → calls `getCurrentFilters()` → `client/src/api.js` drops any `'all'` values → FastAPI query params → `apply_filters()` / `filter_by_month()` in `server/main.py` → Pydantic `response_model` validation → view stores raw data in `ref`s and derives everything else in `computed`.

Each view watches only what its endpoint accepts — respect this when adding views:

| View | Watches | Endpoint filters |
|---|---|---|
| Dashboard, Orders | all four | warehouse, category, status, month |
| Inventory, Demand, Backlog | location, category | warehouse, category |
| Restocking | location, category | warehouse, category |
| Spending | period only | none (endpoint ignores params) |

Filter value conventions:
- `'all'` is the sentinel for "no filter", stripped in `api.js` **and** re-checked in `apply_filters` — both layers must keep that check.
- `FilterBar` emits **lowercase** category values (`"circuit boards"`); the backend lowercases both sides. Warehouse and status are matched the same way, so casing in the data files matters less than consistency.
- Period is `YYYY-MM` and matched as a **substring** of `order_date`. `server/main.py`'s `QUARTER_MAP` also accepts `Q1-2025`–`Q4-2025`, but `FilterBar` only exposes months — quarters are reachable via the API only.
- **Inventory has no date field**, so the month filter is silently ignored there. Don't add a period watcher to `Inventory.vue` expecting it to work.

### Restocking

`Restocking.vue` sets a budget; `GET /api/restock/recommendations` joins each demand forecast to its inventory item, sizes an order against **`quantity_on_hand`** (not `current_demand`, which is units demanded), ranks by urgency, and greedily fills the budget. Three things are easy to get wrong:

- Urgency **must** be ranked through `URGENCY_RANK`, never by sorting the strings — Python orders them `high < low < medium`.
- The fill walks the **whole** ranked list rather than stopping at the first item that does not fit, so cheap low-priority items can use up leftover budget.
- `POST /api/restock-orders` accepts only `item_sku` + `quantity`; costs and lead times are recomputed server-side.

Lead times are derived in `main.py` from `WAREHOUSE_LEAD_TIME_DAYS` + `CATEGORY_LEAD_TIME_MODIFIER` — no lead-time field exists in any data file. A restock order can span warehouses, so `GET /api/restock-orders` filters on its **lines**, not a scalar order field; reusing `apply_filters` there would hide orders the user just placed.

### Data

`server/mock_data.py` reads `server/data/*.json` once at import time into module-level lists. Everything is in memory and, apart from `restock_orders` and `purchase_orders` below, read-only — edits to JSON require a server restart, and nothing written at runtime survives. `server/generate_data.py` regenerates the datasets.

The server runs `uvicorn.run(app, ...)` with **no `reload=True`**, so it does not hot-reload. Any change to `server/` — code or JSON — needs a restart to take effect. The Vite client does hot-reload.

Current shape: 32 inventory items, 250 orders spanning `2025-01` to `2025-12`, 21 demand forecasts, 3 warehouses (San Francisco, London, Tokyo), 5 categories (Circuit Boards, Sensors, Actuators, Controllers, Power Supplies), 4 statuses (Delivered, Shipped, Processing, Backordered). `purchase_orders.json` is an empty array, so `has_purchase_order` on `/api/backlog` starts `false` for every item and only flips for orders raised during the current run.

**Every `item_sku` in `demand_forecasts.json` must exist in `inventory.json`.** Restocking joins the two to get `unit_cost`, `warehouse`, `category`, and `quantity_on_hand` — a forecast for an unstocked SKU is silently dropped from the plan. `tests/backend/test_misc_endpoints.py` enforces this, along with "at least 5 stable forecasts, each under 2% change".

`restock_orders` and `purchase_orders` are the **two mutable datasets**. `POST /api/restock-orders` and `POST /api/purchase-orders` append to their module-level lists, so unlike everything else here they change at runtime — and are lost on restart. Anything reading them must tolerate an empty list, and any test that writes needs the matching autouse fixture in `tests/backend/conftest.py` — `clear_restock_orders` / `clear_purchase_orders` — each of which clears **in place**; rebinding the name would not work.

Adding or renaming a JSON field requires updating the matching Pydantic model in `server/main.py`, or `response_model` validation will reject the payload.

### Endpoints implemented in `server/main.py`

- `GET /api/inventory` (warehouse, category), `GET /api/inventory/{id}`
- `GET /api/orders` (warehouse, category, status, month), `GET /api/orders/{id}`
- `GET /api/demand`, `GET /api/backlog` — no filters
- `GET /api/restock/recommendations` (budget, warehouse, category) — budget-constrained restocking plan
- `POST /api/restock-orders`, `GET /api/restock-orders` (warehouse, category)
- `POST /api/purchase-orders`, `GET /api/purchase-orders/{backlog_item_id}` — one PO per backlog item; a second is a 409
- `GET /api/dashboard/summary` — all four filters
- `GET /api/spending/{summary,monthly,categories,transactions}` — no filters; `categories` derives each `percentage` from the amounts
- `GET /api/reports/{quarterly,monthly-trends}` — computed from orders, no filters

### Frontend calls endpoints the backend does not implement

`client/src/api.js` calls these, and **no route exists for any of them** — they 404 at runtime (callers log to console and degrade):

- `GET/POST/DELETE/PATCH /api/tasks` — used by `App.vue`/`TasksModal.vue`; the task list falls back to the hardcoded tasks in `useAuth.js`

This gap is a workshop build-it exercise. Implement the routes rather than removing the client calls.

The purchase-order routes used to be listed here. They are implemented now, along with the `PurchaseOrderModal.vue` the dashboard renders — the component was missing entirely, so every "Create PO" button in Inventory Shortages was dead.

### i18n and currency

`client/src/composables/useI18n.js` is another module-scope singleton (en/ja), persisting to `localStorage['app-locale']`. Currency is derived from locale, not chosen separately: `ja` → JPY, everything else → USD, converted at a hardcoded `USD_TO_JPY = 150` in `client/src/utils/currency.js`.

Two distinct translation paths — new UI copy goes in **both** `client/src/locales/en.js` and `ja.js` under the same key, while **data values** (product names, customer names, warehouses) go through `translateProductName` / `translateCustomerName` / `translateWarehouse` lookup maps inside `useI18n.js`.

## Gotchas

1. Use stable `v-for` keys (`sku`, `id`, `month`), never the array index.
2. Validate dates before `.getMonth()` / date math — order data has optional `actual_delivery`.
3. Update Pydantic models whenever JSON structure changes.
4. Revenue goals in `Dashboard.vue`: $800K for a single month, ×12 = $9.6M when the period filter is `all`.
5. All views are Composition API via `setup()` with an explicit return — don't mix in Options API.

## Stale documentation

Don't trust these without checking; fix them if you touch the area:
- `tests/README.md` claims a `test_orders.py`; that file doesn't exist. Check its test count against a real run (94 as of the purchase-order work) — it has been wrong before. Its documented run command is also the one that fails (see Tests above).
- `.claude/hooks/README.md` documents a `PostToolUse` hook wired in `.claude/settings.local.json` and a `user-prompt-submit.sh`. Neither exists — `settings.local.json` has no `hooks` section and only `post-tool-use.sh` is on disk.

## Design System

Slate/gray palette (`#0f172a`, `#64748b`, `#e2e8f0`); status colors green/blue/yellow/red. Charts are hand-written SVG, layouts use CSS Grid, styles are `scoped` per component with global styles in `client/src/App.vue`. **No emojis in the UI.**
