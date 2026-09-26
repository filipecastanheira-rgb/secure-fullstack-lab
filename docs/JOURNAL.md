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
