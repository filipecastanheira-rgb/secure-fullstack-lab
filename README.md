# Secure Fullstack Lab

A full-stack application built as a **security portfolio project** — focused
on demonstrating security controls, evidence, and risk reasoning around a
working system, not just the system itself.

The application is the vehicle. The security work is the product.

## Goal

Build, deploy, and harden a real web application end-to-end — frontend,
backend, database, reverse proxy, TLS, firewall — and then **attack it,
detect the attacks, fix the findings, and map everything back to recognised
frameworks** (OWASP Top 10 / ASVS, ISO 27001 Annex A, CIS Controls, NIS2
supply-chain requirements).

The deliverable is not "I built an app". It is:

- a threat model with prioritised risks,
- a risk register with residual risk,
- a security pipeline that produces evidence on every push,
- vulnerabilities deliberately introduced, detected, and fixed,
- hardening as code, measured against a benchmark,
- backup and restore with measured RTO/RPO,
- incident response playbook with a simulated exercise and post-mortem.

## Scope

**In scope:**

- Full-stack app: Vue 3, FastAPI, SQLite (PostgreSQL path preserved)
- Authentication (JWT), authorisation (RBAC), rate limiting
- Reverse proxy with TLS (internal CA)
- Server hardening (SSH, UFW, Fail2Ban, auditd)
- Security pipeline: SAST, SCA, secrets scanning, DAST
- Threat model, GRC documents, control mapping
- Detection: structured logs, correlation, attack scenarios
- Backups with measured RTO/RPO
- Backend containerised (Podman) with supply-chain scanning

**Out of scope for this repository** (deliberate, documented decisions):

- **SIEM stack (Wazuh, Loki/Grafana)** — the lab runs on small VMs. Log
  aggregation is done with `journalctl`, `auditd`, and lightweight
  correlation scripts. A full SIEM is a separate project.
- **Full containerisation** — the deployment (systemd + Nginx) is stable
  and proven. Only the backend is containerised, to demonstrate supply-chain
  practices without rebuilding what already works.
- **Cloud deployment** — the lab is explicitly not exposed to the Internet;
  that is a design decision that gives the threat model coherence. A cloud
  version exists as a separate project, with its own posture assessment.

This deliberate narrowing is intentional and documented. It reflects
engineering judgment, not missing capability.

## Stack

| Layer             | Technology              | Status      |
|-------------------|-------------------------|-------------|
| Frontend          | Vue 3 + Vite            | ✅ working  |
| Backend           | FastAPI (Python)        | ✅ working  |
| Database          | SQLite + SQLAlchemy     | ✅ working  |
| Reverse proxy     | Nginx                   | ✅ working  |
| TLS               | Internal CA (OpenSSL)   | ✅ working  |
| Process manager   | systemd                 | ✅ working  |
| Firewall          | UFW                     | ✅ working  |
| SSH hardening     | OpenSSH (key-only)      | ✅ working  |
| Intrusion prevent | Fail2Ban                | ✅ working  |
| Auth              | JWT + RBAC              | ⏳ next     |
| CI/CD             | GitHub Actions          | ⏳ planned  |
| SAST              | Bandit                  | ⏳ planned  |
| SCA               | pip-audit, npm audit    | ⏳ planned  |
| Secrets scanning  | gitleaks                | ⏳ planned  |
| DAST              | OWASP ZAP               | ⏳ planned  |
| Supply chain      | Podman, Trivy, Syft, cosign | ⏳ planned |
| Config as code    | Ansible                 | ⏳ planned  |
| Benchmark         | Lynis (CIS)             | ⏳ planned  |

## Architecture (current state)

    Kali (client / attacker)          Ubuntu (server)
    ────────────────────────          ─────────────────────────
                                       ┌─────────────────────┐
    Firefox ─── HTTPS ───────────────▶ │ Nginx  :443         │
                                       │  ├─ /        → Vue  │
                                       │  └─ /api/*   →      │
                                       └──────────┬──────────┘
                                                  │
                                                  ▼
                                       ┌─────────────────────┐
                                       │ FastAPI  :8000      │
                                       │  (localhost only)   │
                                       └──────────┬──────────┘
                                                  │ SQLAlchemy
                                                  ▼
                                       ┌─────────────────────┐
                                       │ SQLite (lab.db)     │
                                       └─────────────────────┘

    Hardening layer (host):
      UFW          — 22 (from Kali only), 80, 443
      Fail2Ban     — bans IPs on repeated SSH auth failures
      SSH          — key-only, no root, allowlist of users

## Environment

The lab runs on **isolated virtual networks inside VMware**:

- **Ubuntu VM** at `192.168.1.173` — hosts the application, Nginx, database.
- **Kali VM** at `192.168.1.125` — client, browser, security testing.
- Traffic between VMs stays on dedicated lab segments behind a virtual
  firewall/router. The lab is **not exposed to the Internet** and is **not
  a 24/7 service** — it runs when working on it.

The IPs above are lab-specific. The application's hardcoded references live
in exactly two places:

- [`frontend/src/config.js`](frontend/src/config.js) — API base URL
- [`backend/app/main.py`](backend/app/main.py) — no longer needed after
  Nginx unified the origin

## Documentation

- [`docs/JOURNAL.md`](docs/JOURNAL.md) — development journal: decisions,
  issues, lessons, one section per working session.
- [`deploy/`](deploy/) — deployment artefacts: systemd units, Nginx config,
  hardening files.
- `docs/threat-model.md` — STRIDE analysis (planned)
- `docs/risk-register.md` — risks with likelihood, impact, treatment (planned)
- `docs/security-policy.md` — vulnerability management, patching (planned)
- `docs/incident-response.md` — IR playbook (planned)
- `docs/control-mapping.md` — mapping to OWASP / ISO 27001 / NIS2 (planned)

## Roadmap

### Phase 1 — Application (done)

- [x] Vue frontend working
- [x] FastAPI backend working
- [x] Vue ↔ FastAPI over HTTP + JSON
- [x] Persistent data (SQLite + SQLAlchemy)
- [x] Asset CRUD with validation (Pydantic)

### Phase 2 — Deployment (done)

- [x] systemd services for the API
- [x] Nginx as reverse proxy (single entry point)
- [x] Vue built for production, served as static files
- [x] HTTPS with internal CA (own PKI)
- [x] HTTP → HTTPS redirect
- [x] Security headers (HSTS, X-Frame-Options, CSP, etc.)

### Phase 3 — Hardening (done)

- [x] SSH key-only authentication
- [x] Root login disabled, user allowlist
- [x] UFW firewall (deny incoming, three rules)
- [x] Fail2Ban with custom SSH filter
- [x] Configuration versioned in `deploy/hardening/`

### Phase 4 — Authentication and authorisation

- [ ] User model with argon2 password hashing
- [ ] JWT authentication (login, refresh)
- [ ] Role-based access control (at least two roles)
- [ ] Rate limiting on authentication endpoints
- [ ] Tests covering auth flows

### Phase 5 — Threat model and GRC

- [ ] Asset inventory and trust boundaries
- [ ] STRIDE analysis with prioritised threats
- [ ] Risk register (likelihood, impact, treatment, residual risk)
- [ ] Simplified Statement of Applicability
- [ ] Vulnerability and patch management policy
- [ ] Incident response playbook
- [ ] Simulated incident exercise with post-mortem
- [ ] Control mapping (OWASP Top 10 / ASVS, ISO 27001 Annex A, NIS2)

### Phase 6 — Security pipeline (CI/CD)

- [ ] GitHub Actions workflow triggered on push
- [ ] Python lint (ruff) and JS lint (eslint)
- [ ] Backend tests (pytest)
- [ ] SAST: Bandit
- [ ] SCA: pip-audit and npm audit
- [ ] Secrets scanning: gitleaks
- [ ] DAST: OWASP ZAP baseline against the running lab
- [ ] Reports published as workflow artefacts

### Phase 7 — Deliberate vulnerabilities

- [ ] Introduce SQL injection, IDOR, and misconfigured CORS
- [ ] Detect each with the pipeline and/or manual testing
- [ ] Fix each with a documented commit
- [ ] Before/after evidence in the JOURNAL

### Phase 8 — Detection and monitoring

- [ ] Structured JSON logging in FastAPI
- [ ] auditd on the host
- [ ] GoAccess for Nginx access logs
- [ ] Correlation script: detect repeated auth failures and suspicious patterns
- [ ] Attack scenarios executed from Kali, with what the logs show

### Phase 9 — Configuration as code

- [ ] Ansible playbooks for SSH, UFW, Fail2Ban, auditd
- [ ] Lynis baseline run and score recorded
- [ ] Hardening applied via playbook, score re-measured
- [ ] Before/after documented

### Phase 10 — Backup and restore

- [ ] Automated backup of `lab.db`
- [ ] Defined RTO and RPO
- [ ] Restore performed for real, with measured duration
- [ ] Procedure documented

### Phase 11 — Supply chain (backend container)

- [ ] Containerfile for the FastAPI backend
- [ ] Podman running non-root, read-only filesystem
- [ ] Trivy scan of the image
- [ ] SBOM with Syft (CycloneDX format)
- [ ] Image signing with cosign

### Phase 12 — Final polish

- [ ] README updated to reflect final state
- [ ] `SECURITY.md` with disclosure policy
- [ ] Dependabot enabled
- [ ] MIT license
- [ ] Git history cleaned of anything sensitive
- [ ] "What I Learned" section completed

## Running locally

### Backend (production-style)

    sudo systemctl start secure-fullstack-api.service

### Backend (development, with auto-reload)

    cd backend
    source .venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

### Frontend (development)

    cd frontend
    npm run dev -- --host 0.0.0.0

### Frontend (production build, served by Nginx)

    cd frontend
    npm run build
    # Nginx serves frontend/dist/ automatically

Then open:

    https://192.168.1.173

The certificate is issued by an internal CA. The CA must be installed on
clients (see `deploy/hardening/README.md`).

## What I Learned with This Project

Written progressively. Each entry is a concept or decision that changed how
I think — not a list of technologies.

**Diagnose layer by layer, not by guessing.**
When the browser could not reach the frontend, testing network → firewall →
service → browser, in order, isolated the problem in minutes. The same
approach is the basis of any incident investigation.

**CORS is a browser policy, not a server bug.**
`curl` worked; the browser did not. The browser was enforcing Same-Origin
Policy on a cross-port request. Understanding where enforcement happens
changes how you interpret symptoms.

**Separate what is stored from what is exposed.**
SQLAlchemy models describe the database; Pydantic schemas describe the API
contract. They are different files for a reason — mixing them is how
sensitive fields leak through APIs.

**Centralise configuration before it becomes a problem.**
The backend URL was hardcoded in two frontend files. Moving it to
`config.js` took five minutes and prevented a much larger problem when the
lab network changes.

**Process management is not optional.**
`nohup ... &` keeps a process alive across terminal sessions but does not
restart it on crash, does not start it on boot, and does not centralise
logs. systemd does all three. The difference between a hobby project and a
service is exactly this.

**A reverse proxy changes the security model.**
When Nginx unified the frontend and API behind one port, CORS disappeared
entirely — not because we configured it better, but because the request was
no longer cross-origin. Architecture determines which controls are needed.

**TLS is not "turn on HTTPS".**
Building a small internal CA (CA key, CA cert, server key, CSR, signed
cert, SAN) made it concrete: what a certificate actually asserts, why SAN
matters and CN does not, why the private key never leaves the server, and
why installing the CA on clients is an act of trust, not configuration.

**Defense in depth is a design choice, not a checklist.**
SSH key-only, UFW, Fail2Ban, and Nginx security headers each defend against
different things. None of them alone would be enough. The interesting part
is understanding which one catches which class of attack.

**Order of operations matters in security changes.**
Before disabling password authentication, we tested that key authentication
worked. Before enabling UFW, we defined the SSH allow rule. Every change
that could lock you out needs a verified way back in — in our case, the
VMware console.

**Bans block the whole IP, not just the port.**
When Fail2Ban banned the Kali IP after repeated SSH failures, all traffic
from Kali — including HTTPS — was blocked. Worth knowing before it happens
in a real environment.

**Tools do not integrate by default.**
Fail2Ban uses raw iptables by default, but UFW manages its own chains, so
the ban would have had no effect. The fix (`banaction = ufw`) is one line,
but only if you know it is needed. Integration between tools is a design
task, not a side effect.

**`DROP` and `REJECT` are not the same.**
UFW drops packets silently. The client sees a timeout, not a refusal. Slower
for legitimate users, but reveals nothing to a scanner. Whether that is the
right trade-off depends on the context.

## Security

See [`SECURITY.md`](SECURITY.md) (planned) for the disclosure policy.

The repository is currently **private**. It will be made public once the
final polish phase is complete. The lab's private IP addresses are
documented intentionally — they only exist inside an isolated virtual
network and cannot be reached from the Internet.

## License

MIT — see [`LICENSE`](LICENSE) (to be added in the final polish phase).
