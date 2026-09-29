# Secure Fullstack Lab

Full-stack application built as a hands-on lab for development, deployment and security (DevSecOps).

## Goal

Build a complete web application — frontend, backend, database — and harden it along the way with real security, automation and observability practices, **without relying on paid cloud services**.

## Stack

| Layer          | Technology          | Status        |
|----------------|---------------------|---------------|
| Frontend       | Vue 3 + Vite        | ✅ working    |
| Backend        | FastAPI (Python)    | ✅ working    |
| Database       | SQLite → PostgreSQL | ✅ working    |
| Reverse proxy  | Nginx               | ⏳ planned    |
| HTTPS          | Let's Encrypt       | ⏳ planned    |
| CI/CD          | GitHub Actions      | ⏳ planned    |
| Security       | Bandit, SCA, ZAP    | ⏳ planned    |

## Architecture (current state)

    Kali (client)              Ubuntu (server)
    ─────────────              ────────────────
    Browser  ─── HTTP ──▶      Vue (Vite)  :5173
                                  │
                                  │ fetch /api/*
                                  ▼
                                FastAPI     :8000
                                  │
                                  │ SQLAlchemy
                                  ▼
                                SQLite (lab.db)

## Environment

This project runs on an **isolated VMware lab environment**:

- **Ubuntu (VMware)** — hosts frontend, backend and database.
- **Kali (VMware)** — client, browser, security testing.
- The lab runs on dedicated virtual networks, **not exposed to the internet**.
- It is **not a 24/7 service** — it is a learning lab, started when needed.

IP addresses used in the code are specific to this lab and are centralized in
[`frontend/src/config.js`](frontend/src/config.js) and in the `ALLOWED_ORIGINS`
constant in [`backend/app/main.py`](backend/app/main.py).

## Running locally (development)

### Backend

    cd backend
    source .venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

### Frontend

    cd frontend
    npm run dev -- --host 0.0.0.0

Then open from any machine on the lab network:

    http://192.168.1.173:5173

## Documentation

- [`docs/JOURNAL.md`](docs/JOURNAL.md) — development journal (decisions, issues, solutions).

## Roadmap

- [x] Vue frontend working
- [x] FastAPI backend working
- [x] Vue ↔ FastAPI (HTTP + JSON)
- [x] Persistent data (SQLite + SQLAlchemy)
- [ ] Deployment on Ubuntu (systemd/supervisor)
- [ ] Nginx as reverse proxy
- [ ] HTTPS
- [ ] SSH hardening / UFW / Fail2Ban
- [ ] CI/CD with GitHub Actions
- [ ] SAST (Bandit)
- [ ] SCA (dependencies)
- [ ] DAST (OWASP ZAP)
- [ ] Logging and monitoring
- [ ] Backups
- [ ] Final documentation and security review

## What I Learned with This Project

<!-- This section is written progressively. Each entry reflects a real lesson
     learned while building the project — not a list of technologies, but
     concepts and decisions that changed how I work. -->

**Session 1 — Diagnose layer by layer.**
When the browser could not reach the frontend, guessing did not help. Testing
network → firewall → service → browser, in order, isolated the problem in
minutes. Same approach applies to any connectivity issue, and later it will be
the basis for incident response.

**Session 2 — CORS is a browser policy, not a server bug.**
`curl` worked, the browser did not. The difference was Same-Origin Policy —
the browser was refusing a cross-port request, not the server. Learning where
CORS lives (client-side enforcement) explained why terminal tools behave
differently from real users.

**Session 3 — Separate what is stored from what is exposed.**
SQLAlchemy models (database shape) and Pydantic schemas (API contract) are
deliberately different files. Mixing them is how sensitive fields leak through
APIs. This is the same reasoning behind defense-in-depth.

**Session 4 — Centralize configuration before it becomes a problem.**
The backend URL was hardcoded in two frontend files and CORS origins were
inline in the backend. Moving them to `config.js` and `ALLOWED_ORIGINS` was a
five-minute change that prevents a much bigger problem when the lab network
is re-provisioned.

## License

Personal learning project.
