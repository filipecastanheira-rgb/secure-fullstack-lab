# Secure Fullstack Lab — Development Journal

Chronological log of decisions, commands and issues found throughout the project.
Purpose: (1) document for portfolio, (2) restore context, (3) learn from mistakes.

---

## Current architecture

    Frontend (Vue + Vite)   →   Backend (FastAPI)   →   [soon: SQLite]
    http://192.168.1.173:5173     http://192.168.1.173:8000

Machines:
- Ubuntu (VMware) — 192.168.1.173 — hosts the project
- Kali (VMware) — 192.168.1.125 — client / browser / testing

---

## Session 1 — Bootstrapping frontend and backend

**Goal:** have Vue and FastAPI running and reachable from Kali.

- FastAPI backend responding at `/` with `{"message": "Secure Fullstack Lab API is running"}`.
- Vue frontend running with `npm run dev -- --host 0.0.0.0`.
- Initial `App.vue` only displayed "You did it!" (Vite template).

**Issue 1:** Firefox on Kali could not open `http://192.168.1.173:5173`.
**Diagnosis (layer by layer):**
1. `ss -ltnp | grep 5173` on Ubuntu → Vite listening on `0.0.0.0:5173` (OK).
2. `curl` on Ubuntu → `HTTP/1.1 200 OK` (OK).
3. `ping` from Kali → replies (network OK).
4. `curl` from Kali → `HTTP/1.1 200 OK` (network + firewall + Vite OK).
**Conclusion:** the issue was browser-side (cache/refresh). Fixed with `Ctrl+Shift+R`.

**Lesson:** always diagnose layer by layer — network → firewall → service → browser.

---

## Session 2 — Connecting Vue to FastAPI

**Goal:** Vue performs a `fetch` to FastAPI and displays the response on screen.

**Backend (`backend/main.py`):**
- Added `CORSMiddleware` with allowed origins:
  - `http://localhost:5173`
  - `http://192.168.1.173:5173`
- New endpoint: `GET /api/hello` → `{"message": "Hello from FastAPI 👋"}`.

**Frontend (`frontend/src/App.vue`):**
- `ref` for reactive state (`message`).
- `onMounted` to trigger `fetch` when the component mounts.
- `await fetch('http://192.168.1.173:8000/api/hello')` + `await res.json()`.
- `{{ message }}` in the template to display the response.

**Issue 2:** `NetworkError when attempting to fetch resource` in the browser.
**Cause:** FastAPI had died in the meantime (killed with the terminal).
**Diagnosis:** `curl -H "Origin: http://192.168.1.173:5173" -i ...` showed `access-control-allow-origin` while the server was alive → CORS was fine.
**Solution:** start FastAPI and Vite with `nohup ... &` so they survive the terminal closing.

**Result:** Firefox on Kali shows `Hello from FastAPI 👋` — Vue ↔ FastAPI working. ✅

---

## Useful commands

Start FastAPI in background:

    cd ~/secure-fullstack-lab/backend
    source .venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ~/fastapi.log 2>&1 &

Start Vite in background:

    cd ~/secure-fullstack-lab/frontend
    nohup npm run dev -- --host 0.0.0.0 > ~/vite.log 2>&1 &

View logs:

    tail -f ~/fastapi.log
    tail -f ~/vite.log

Check what is using a port:

    sudo ss -ltnp | grep <port>

Kill a process:

    kill <PID>

---

## Architecture decisions

- **Explicit CORS** (no `"*"`), because we will use credentials later.
- **`/api` prefixes** on endpoints, to separate API from pages.
- **SQLite first, PostgreSQL later** — code will be written with SQLAlchemy so migration is just swapping the connection string.
- **`nohup` in development** — temporary solution; in production we will use systemd/supervisor.

---

## Next step

- Data persistence with SQLite + SQLAlchemy.



---

## Session 3 — Persistent data with SQLite + SQLAlchemy

**Goal:** replace in-memory data with a real database, keeping the door open
to swap SQLite for PostgreSQL later without rewriting business code.

**Backend restructure:**

    backend/
    ├── app/
    │   ├── __init__.py      # marks "app" as a Python package
    │   ├── main.py          # FastAPI entry point + endpoints
    │   ├── database.py      # SQLAlchemy engine, session, Base, get_db()
    │   ├── models.py        # ORM models (Asset)
    │   └── schemas.py       # Pydantic schemas (AssetCreate, AssetRead)
    ├── lab.db               # SQLite file (gitignored)
    └── .venv/

**Design decisions:**

- **SQLAlchemy 2.0 syntax** (`Mapped[...]` + `mapped_column(...)`) instead of
  the legacy `Column(...)` style — this is what modern tutorials and docs use.
- **Separate `models.py` and `schemas.py`.** Models describe the *database*;
  schemas describe the *API contract*. Mixing them causes information
  disclosure (sensitive DB fields leaking through JSON responses).
- **`lifespan` context manager** instead of the deprecated `@app.on_event`.
  On startup it calls `Base.metadata.create_all(bind=engine)`.
- **`Depends(get_db)`** for session injection — each request opens a session
  and closes it in a `finally` block, even on exceptions.
- **`created_at` uses `lambda: datetime.now(timezone.utc)`** and not the
  bare function reference, otherwise all rows would share the same timestamp
  (Python evaluates the default only once).
- **Uvicorn command changed** from `main:app` to `app.main:app` because
  `main.py` moved into the `app/` package.
- **`db.refresh(asset)` after `commit()`** to fetch the DB-generated values
  (`id`, `created_at`) before returning the object — otherwise they would be
  missing from the response.

**Endpoints added:**

- `GET /api/assets` → returns the full list of assets, ordered by id.
- `POST /api/assets` → creates a new asset; returns `201 Created` with the
  row as it was stored.

**Automatic validation (Pydantic):**

- `hostname` shorter than 1 character → `422 Unprocessable Entity`
- The request never reaches the endpoint function. Validation happens before.

This is a defense-in-depth pattern: constraints live in one place (the schema)
and the API rejects invalid input automatically.

**Verification commands:**

    # empty list
    curl -s http://192.168.1.173:8000/api/assets

    # create
    curl -s -X POST http://192.168.1.173:8000/api/assets \
      -H "Content-Type: application/json" \
      -d '{"hostname":"ubuntu-lab","ip_address":"192.168.1.173","os":"Ubuntu 24.04"}'

    # list again — the new row must be present
    curl -s http://192.168.1.173:8000/api/assets

    # invalid payload — expect 422
    curl -s -X POST http://192.168.1.173:8000/api/assets \
      -H "Content-Type: application/json" \
      -d '{"hostname":"","ip_address":"10.0.0.1","os":"Kali"}'

**Next step:**

- Connect the Vue frontend to the assets endpoints (list + create form).
- Then: deployment on Ubuntu with systemd/supervisor.


---

## Session 4 — Frontend ↔ Assets API + network safety decision

**Goal:** give the user a real interface to interact with the assets API —
list existing assets and create new ones — without refreshing the page.

**Frontend structure (new components):**

    frontend/src/
    ├── App.vue                    # orchestrator: state + data fetching
    ├── config.js                  # central API endpoints (new)
    └── components/
        ├── AssetList.vue          # table of assets (presentational)
        └── AssetForm.vue          # form to create assets

**Component communication:**

    App.vue  ──── props (assets) ─────▶  AssetList.vue
       ▲
       │
       └──── event (created) ─────────  AssetForm.vue

- **props** flow parent → child (data).
- **emits** flow child → parent (events).
- `<script setup>` makes imported components available in the template
  without explicit registration.

**Vue concepts used:**

- `ref()` for reactive state (arrays, strings, booleans).
- `onMounted()` to run a function when the component appears — used to load
  the initial asset list.
- `v-model` for two-way binding on form inputs.
- `v-for` + `:key` to render the table rows.
- `v-if` / `v-else-if` / `v-else` to handle three UI states: loading, error,
  success.
- `defineProps` / `defineEmits` macros for component contracts.
- `@submit.prevent` to stop the browser's default form submit (which would
  reload the whole page and break the SPA).
- `:disabled="loading"` to prevent double-submits while a request is in flight.
- `:assets="assets"` — the colon means the value is a JavaScript expression,
  not a literal string.

**Centralized configuration (`frontend/src/config.js`):**

Before this session, the backend URL `http://192.168.1.173:8000` was hardcoded
in two places. Now it lives in one file:

    export const API_BASE_URL = 'http://192.168.1.173:8000'
    export const API_ENDPOINTS = {
      assets: `${API_BASE_URL}/api/assets`,
      hello:  `${API_BASE_URL}/api/hello`,
    }

Same idea on the backend: `ALLOWED_ORIGINS` is now a single constant at the
top of `app/main.py`, referenced by the CORS middleware.

**Why this matters:** the lab will eventually be re-provisioned on a
Host-only network with different IPs. Centralizing the base URL means only
one line changes when the network changes.

**Network safety decision (IMPORTANT):**

Both VMs currently run in VMware **Bridged** mode, meaning they can reach
each other AND the home network / Internet through the same router that the
host uses. This is convenient during development (apt, pip, npm, git push)
but is **not safe** for offensive-security testing.

**Commitment, until the lab is properly isolated:**

- Only non-offensive commands are run from the Kali VM:
  `curl`, `ping`, `apt`, `npm`, `git`, `nmap` **only against `127.0.0.1`
  or against our own IPs** (`192.168.1.173`, `192.168.1.125`).
- No subnet scans, brute-force, exploits, or sniffing.
- The home network must never see traffic that looks like an attack.

**Planned fix (Session 5 or later):** migrate the lab to a VMware
**Host-only** network with two network adapters per VM:

    eth0  — Host-only (VMnet1) — lab traffic (isolated)
    eth1  — NAT                — Internet, only when needed

This will be a milestone for the portfolio, and will be documented in the
hardening section.

**Verification commands:**

    # List assets from the terminal (should match what the browser shows)
    curl -s http://192.168.1.173:8000/api/assets

    # Create an asset via curl
    curl -s -X POST http://192.168.1.173:8000/api/assets \
      -H "Content-Type: application/json" \
      -d '{"hostname":"kali-attacker","ip_address":"192.168.1.125","os":"Kali Linux"}'

**Result:** Vue shows the asset table updated live after each form submit —
no manual refresh needed. Full-stack round-trip confirmed. ✅

**Next step:**

- Migrate the lab to an isolated Host-only network (security).
- Then: deployment on Ubuntu with systemd/supervisor.
