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


---

## Scope note — what this repository does and does not cover

This repository documents **the Secure Fullstack Lab application** — its code,
its deployment, its security hardening. It does **not** document the home
network it runs on.

Reasons:

- The project runs on **isolated virtual networks** inside VMware. The home
  network is never touched by this application.
- The lab is **not a 24/7 service** — it is started when working on it, and
  stopped afterwards.
- Documenting personal infrastructure here would mix concerns and expose
  details that do not belong in a project repository.

Anything network-specific to the lab (VM names, internal segments, firewall
rules) is deliberately **out of scope** for this repository. The code only
knows what it needs to know: the URLs and origins declared in
`frontend/src/config.js` and `ALLOWED_ORIGINS` in `backend/app/main.py`.

**Operational policy during offensive-security testing** (future sessions):

- The lab's outbound route to the Internet will be disabled while running
  scans or exploits.
- Only the isolated lab networks are reachable during those tests.
- No traffic that resembles an attack leaves the lab under any circumstance.


---

## Session 5 — systemd services + repository scope

**Goal:** stop losing the FastAPI and Vite processes whenever a terminal is
closed. Replace manual `nohup ... &` with proper service management.

**Why systemd, not nohup:**

`nohup` keeps a process alive across terminal sessions, but it does not:
- restart the process if it crashes,
- start it at boot,
- give a single command to start/stop/restart,
- centralize logs.

systemd does all of the above and is the standard service manager on modern
Linux. Learning it is a prerequisite for any real deployment.

**Two services created** in `/etc/systemd/system/`:

| Service                          | Runs                          | Port |
|----------------------------------|-------------------------------|------|
| `secure-fullstack-api.service`   | FastAPI (uvicorn)             | 8000 |
| `secure-fullstack-web.service`   | Vue (Vite dev server)         | 5173 |

**Copies kept in the repository** at `deploy/systemd/` so the configuration
is versioned. The real files still live in `/etc/systemd/system/` — the ones
in the repo are backups/installers for other machines (see
`deploy/README.md`).

**Key design decisions in the service files:**

- **`User=filipe` / `Group=filipe`** — the services run as a normal user,
  never as root. The API only needs a high port and read access to project
  files; no privilege escalation required.
- **`WorkingDirectory=`** — set to the backend/frontend folder. Critically,
  this makes the relative `sqlite:///./lab.db` resolve to the right file.
- **`ExecStart=` uses absolute paths** — systemd does not expand `~` or
  environment variables from the user's shell. For the frontend we call
  `node_modules/.bin/vite` directly instead of `npm run dev`, so systemd
  tracks a single process instead of two (npm → node → vite).
- **`Restart=on-failure` + `RestartSec=3`** — the service restarts
  automatically if it crashes, but stays stopped if we stop it deliberately.
- **No `--reload` in production** — the service does not auto-reload on code
  changes. To apply changes: `sudo systemctl restart secure-fullstack-api`.
  This matches production behaviour and avoids the multi-process reloader.

**Verification — resilience test:**

Killed the API process with `kill -9`. systemd detected the failure and
restarted the service automatically within ~3 seconds, with a new PID. The
logs recorded the entire sequence:

    Failed with result 'signal'
    Scheduled restart job, restart counter is at 1
    Started secure-fullstack-api.service

**Result:** frontend and backend run as managed services, start on boot, and
recover automatically. No more "why did it stop again?".

**Scope decision — what this repository contains:**

The repository documents **the application** — code, deployment, hardening.
It does **not** document the home network. Reasons:

- The lab runs on isolated virtual networks (VMware LAN Segments behind an
  OPNsense VM router). The home network is never touched by this project.
- It is not a 24/7 service — it is started when working on it.
- Personal infrastructure details do not belong in a project repository.

Network-specific details of the lab (VM names, segments, firewall rules) are
deliberately out of scope. The code only knows what it needs: `config.js` on
the frontend, `ALLOWED_ORIGINS` in `backend/app/main.py`.

**Operational policy during offensive-security testing (future sessions):**
the lab's outbound route to the Internet will be disabled while running scans
or exploits. Nothing that resembles an attack leaves the lab.

**Next step:**

- Nginx as reverse proxy (replace the Vite dev server with a build + static
  serving; unify the app under a single port).
- Then: HTTPS in the lab, then hardening (SSH, UFW, Fail2Ban).


---

## Session 6 — Nginx as reverse proxy

**Goal:** unify the app behind a single port, remove the Vite dev server from
production, and eliminate CORS as a concern.

**Before:**

    Browser ──▶ :5173  (Vite dev server)
    Browser ──▶ :8000  (FastAPI)      ← cross-origin → CORS required

**After:**

    Browser ──▶ :80  (Nginx)
                        │
                        ├── /          → frontend/dist/  (static)
                        └── /api/*     → proxy → FastAPI :8000
                                                    │
                                                    ▼
                                                  SQLite

**Steps taken:**

1. Installed Nginx with `apt`. Ubuntu's default package enables it at boot
   via systemd automatically (`Created symlink .../nginx.service`).
2. Built the frontend for production with `npm run build`. Output:
   - `dist/index.html`
   - `dist/assets/index-<hash>.css`
   - `dist/assets/index-<hash>.js`
   The hash in filenames means the browser can cache them forever.
3. Created the site configuration in
   `/etc/nginx/sites-available/secure-fullstack`. It:
   - serves static files from `frontend/dist/`
   - proxies `/api/*` to `http://127.0.0.1:8000`
   - falls back to `index.html` for SPA routes (`try_files $uri $uri/ /index.html`)
   - uses dedicated logs (`secure-fullstack.access.log` and `.error.log`)
   - sets `X-Real-IP` and `X-Forwarded-For` so the API sees the real client IP
4. Enabled the site and disabled the default one:
   - `ln -s /etc/nginx/sites-available/secure-fullstack /etc/nginx/sites-enabled/`
   - `rm /etc/nginx/sites-enabled/default`
5. Validated with `nginx -t`, then reloaded (`systemctl reload nginx` — no
   downtime, unlike `restart`).
6. Changed `frontend/src/config.js` to use **relative paths**
   (`API_BASE_URL = ''`) so the frontend always talks to the same origin.
7. Added a `server.proxy` block to `vite.config.js` for local development
   (`/api` → `http://127.0.0.1:8000`), so `npm run dev` keeps working.
8. Removed `CORSMiddleware` from `backend/app/main.py`. Same origin now —
   CORS is no longer needed. Left a comment explaining the decision and when
   it would have to come back.
9. Stopped, disabled, and deleted `secure-fullstack-web.service`. The Vite
   dev server is no longer run as a service.
10. Versioned the Nginx config at `deploy/nginx/secure-fullstack`.

**Issue encountered:** Nginx returned `500 Internal Server Error` on first
try. Error log showed:

    stat() ".../dist/index.html" failed (13: Permission denied)

**Cause:** Ubuntu home directories are mode `drwxr-x---`. Nginx runs as
`www-data`, which is neither the owner nor in the owner's group — so it
cannot traverse `/home/filipe/`.

**Fix (temporary):**

    sudo chmod o+x /home/filipe

This grants traverse-only permission (not listing). It works, but is not the
production-correct approach. In a later hardening session, `dist/` will be
moved to `/var/www/secure-fullstack/` and this permission will be revoked.

**Issue encountered (second):** after configuring Nginx, the browser showed
`NetworkError`. The frontend build still contained the old hardcoded URL
(`http://192.168.1.173:8000`), because it had been built *before* editing
`config.js`.

**Lesson:** the `dist/` folder is a **build artefact**. Any change to the
frontend source requires `npm run build` before the browser will see it.
This is exactly why `dist/` is git-ignored — it is generated, not source.

**Key concepts learned:**

- **Reverse proxy** — Nginx is a single entry point that routes to different
  backends by path. Same-origin from the browser's perspective.
- **`proxy_set_header X-Real-IP` / `X-Forwarded-For`** — without these, the
  API sees every request as coming from `127.0.0.1`. With them, real client
  IPs are preserved for logs and auditing.
- **SPA fallback** — `try_files $uri $uri/ /index.html` is required for Vue
  Router to handle client-side URLs.
- **`nginx -t` before reload** — always validate config syntax before
  applying. A bad config with `restart` can take the site down.
- **Content-hashed assets** — Vite's `index-<hash>.js` filenames enable
  `expires 1y; immutable`, so repeat visits are instant.
- **`chmod o+x` on a directory** — grants traverse, not list. Different
  permission bit meaning than on files.

**Result:** one URL, one port, no CORS, faster frontend, everything managed
by systemd.

**Next step:**

- HTTPS in the lab environment (self-signed or internal CA, since there is
  no public domain).
- Then: hardening (SSH, UFW, Fail2Ban).
