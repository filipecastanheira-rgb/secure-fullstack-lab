# Secure Fullstack Lab

Full-stack application built as a hands-on lab for development, deployment and security (DevSecOps).

## Goal

Build a complete web application — frontend, backend, database — and harden it along the way with real security, automation and observability practices, **without relying on paid cloud services**.

## Stack

| Layer          | Technology          | Status        |
|----------------|---------------------|---------------|
| Frontend       | Vue 3 + Vite        | ✅ working    |
| Backend        | FastAPI (Python)    | ✅ working    |
| Database       | SQLite → PostgreSQL | ⏳ next       |
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

## Environment

- **Ubuntu (VMware)** — `192.168.1.173` — hosts backend, frontend and, in the future, database and Nginx.
- **Kali (VMware)** — `192.168.1.125` — client, browser, security testing.

## Running locally (development)

### Backend

    cd backend
    source .venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

### Frontend

    cd frontend
    npm run dev -- --host 0.0.0.0

Then open from any machine on the LAN:

    http://192.168.1.173:5173

## Documentation

- [`docs/JOURNAL.md`](docs/JOURNAL.md) — development journal (decisions, issues, solutions).

## Roadmap

- [x] Vue frontend working
- [x] FastAPI backend working
- [x] Vue ↔ FastAPI (HTTP + JSON)
- [ ] Persistent data (SQLite → PostgreSQL)
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

## License

Personal learning project.
