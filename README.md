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
| Auth              | JWT + RBAC              | ✅ working  |
| CI/CD             | GitHub Actions          | ✅ working  |
| SAST              | Bandit                  | ✅ working  |
| SCA               | pip-audit               | ✅ working  |
| Secrets scanning  | gitleaks                | ✅ working  |
| DAST              | OWASP ZAP               | ✅ working  |
| Supply chain      | Podman, Trivy, Syft, cosign | ✅ working  |
| Config as code    | Ansible                 | ✅ working  |
| Benchmark         | Lynis (CIS)             | ✅ working  |

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

- **Ubuntu VM** at `<UBUNTU_IP>` — hosts the application, Nginx, database.
- **Kali VM** at `<KALI_IP>` — client, browser, security testing. Addresses in this repository are placeholders; the real ones are intentionally not published.
- Traffic between VMs stays on dedicated lab segments behind a virtual
  firewall/router. The lab is **not exposed to the Internet** and is **not
  a 24/7 service** — it runs when working on it.

The IPs above are lab-specific. The application's hardcoded references live
in exactly two places:

- [`frontend/src/config.js`](frontend/src/config.js) — API base URL
- [`backend/app/main.py`](backend/app/main.py) — no longer needed after
  Nginx unified the origin

## Container & Supply Chain

The FastAPI backend also runs as a **Podman rootless** container, alongside
the systemd deployment, to demonstrate supply-chain practices without
disturbing the proven setup. The container is evidence that the backend
can be shipped as a scannable artefact — it is not the production path.

- **Image:** `localhost/secure-fullstack-api:0.3`
- **Containerfile:** [`deploy/container/Containerfile`](deploy/container/Containerfile)
- **Instructions:** [`deploy/container/README.md`](deploy/container/README.md)
- **Scan:** `trivy image --image-src podman localhost/secure-fullstack-api:0.3`
  (0 Python CVEs; 166 OS CVEs inherited from base, tracked as upstream)
- **SBOM (Syft) and signing (cosign):** signed and committed (`sbom.cdx.json.sigstore`)

## Documentation

- [`docs/JOURNAL.md`](docs/JOURNAL.md) — development journal. One section per working session: decisions, issues, lessons learned. The most honest artefact in the repository.
- [`docs/threat-model.md`](docs/threat-model.md) — STRIDE analysis of the system. Covers six components (Nginx, FastAPI, SQLite, SSH, PKI, GitHub), six trust boundaries, and six formal findings.
- [`docs/risk-register.md`](docs/risk-register.md) — active, accepted, and deferred risks. Each entry classified by likelihood × impact, with treatment and residual risk. Includes closed risks with commit references.
- [`docs/password-policy.md`](docs/password-policy.md) — credential requirements, lifecycle, and the two-speed rotation model. Mapped to NIST SP 800-63B and ISO 27001 A.5.17.
- [`docs/incident-response.md`](docs/incident-response.md) — five playbooks (GitHub compromise, host compromise, CA key compromise, physical loss, data exfiltration) following NIST SP 800-61 Rev. 2.
- [`docs/control-mapping.md`](docs/control-mapping.md) — evidence mapping of the project's controls to OWASP Top 10, OWASP ASVS, and NIS2 Article 21(2). The ISO/IEC 27001:2022 Annex A mapping is in the Statement of Applicability (`docs/statement-of-applicability-v2.md`).
- [`deploy/`](deploy/) — deployment artefacts: systemd units, Nginx configuration, hardening files, and installation notes.


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

### Phase 4 — Authentication and authorisation (complete)

- [x] User model with argon2id password hashing
- [x] JWT authentication (login endpoint)
- [x] JWT refresh tokens with type separation (access vs refresh)
- [x] Role-based access control (two roles: user, admin)
- [x] Rate limiting on authentication endpoints (Nginx, per-IP)
- [x] Tests covering auth flows (19 pytest tests)

### Phase 5 — Threat model and GRC (complete)

- [x] Asset inventory and trust boundaries
- [x] STRIDE analysis with prioritised threats
- [x] Risk register (likelihood, impact, treatment, residual risk)
- [x] Password policy with NIST-aligned rotation
- [x] Incident response playbook (5 scenarios, NIST SP 800-61)
- [x] Control mapping (OWASP Top 10, ASVS, NIS2)
- [x] Statement of Applicability (ISO 27001 Annex A, 93 controls)
- [x] Vulnerability and patch management policy
- [x] Simulated incident exercise with post-mortem

### Phase 6 — Security pipeline (CI/CD) (complete)

- [x] GitHub Actions workflow triggered on push
- [x] Python lint (ruff) and JS lint (eslint + oxlint)
- [x] Backend tests (pytest, 19 tests)
- [x] SAST: Bandit
- [x] SCA: pip-audit
- [x] Secrets scanning: gitleaks (full history)
- [x] DAST: OWASP ZAP baseline against the running lab
- [x] Six parallel jobs; total runtime ~2 minutes

### Phase 7 — Deliberate vulnerabilities (complete)

- [x] SQL injection — introduced, detected by bandit (B608), fixed, **regression test added**
- [x] IDOR — introduced, **missed by all scanners**, fixed, regression test added
- [x] Misconfigured CORS — introduced, **missed by all scanners**, fixed, regression test added
- [x] Before/after evidence in `docs/vuln-exercise-{sqli,idor,cors}.md`
- [x] Confirmed limitation: 1 of 3 vulnerabilities detected by CI; the other 2 required human analysis and written tests
- [x] Every exercise has a regression test (33 tests in the suite)

### Phase 8 — Detection and monitoring (complete)

- [x] Structured JSON logging in FastAPI
- [x] auditd on the host (15 rules, including privilege escalation)
- [x] GoAccess for Nginx access logs (report generated; not served publicly)
- [x] Correlation script: reads Nginx and FastAPI logs to detect abuse patterns
- [x] Alert when the rate limiter begins rejecting requests (systemd timer, 5-min cadence)
- [x] Attack scenarios executed with what the logs show (`429_BURST` alert from a simulated credential attack)
- [x] Systemd timers for automatic execution (GoAccess hourly, correlation every 5 minutes)

### Known gaps

Items acknowledged as incomplete. Recorded here so they are visible
rather than silently pending.

- [x] **Frontend authentication.** Login form, auth service and logout
  on 401 are implemented, and the asset table loads after login
  (Session 25).
- [ ] **No automatic token refresh in the frontend.** The request
  interceptor logs the user out on 401 instead of using the refresh
  token.
- [ ] **Login endpoint logs user_id: null on success.** The structured
  logging middleware reads `request.state.user_id`, which is only set by
  `get_current_user`. The login endpoint does not use that dependency
  (it is public), so successful logins are not attributed in the logs.
  Small fix: the login endpoint should set `request.state.user_id` after
  authenticating the user.
- [ ] **Refresh token revocation is not implemented.** A leaked refresh
  token remains valid until its 7-day expiry: the refresh endpoint
  reissues tokens but does not invalidate the one that was presented.
  A `jti` claim with a persistent denylist, or a token version counter
  per user, would close this. Noted since Phase 4; not yet scheduled.
- [x] **Statement of Applicability is complete.** Canonical format
  covering all 93 Annex A controls. See
  `docs/statement-of-applicability-v2.md`.
- [ ] **SoA justifications to review.** An external audit found some
  "Not Applicable" justifications weak (for example, vulnerability
  management should be "Applicable").
- [x] **`correlation-check.sh` time window.** The Nginx log is now
  filtered to the last 5 minutes, so an alert stops firing once the
  burst is over (Session 25).

### Phase 9 — Configuration as code (complete)

- [x] Ansible playbooks for SSH, UFW, Fail2Ban, auditd
- [x] Lynis baseline run and score recorded (71 → 73)
- [x] Hardening applied via playbook, score re-measured
- [x] Before/after documented

### Phase 10 — Backup and restore (complete)

- [x] Automated backup of `lab.db` and `.jwt_secret` (daily, systemd timer at 03:00)
- [x] SHA256 integrity verification on each backup
- [x] Retention: 7 days
- [x] **Real restore test performed** (database removed, restored, login verified)
- [x] **RTO measured: 1.394 seconds**
- [x] **RPO defined: 24 hours**
- [x] Documented in `deploy/backup/README.md`

### Phase 11 — Supply chain (backend container) — complete, two hardening items deferred

- [x] Containerfile for the FastAPI backend (base `python:3.14-slim`)
- [x] Podman running non-root (`appuser`, UID 10001, rootless)
- [x] Trivy scan of the image (0 Python CVEs; 166 OS CVEs inherited from base)
- [ ] **Read-only root filesystem** — deferred; SQLite requires a writable journal directory. Hardening path recorded in `docs/JOURNAL.md` (Session 24)
- [ ] **Data volume hardening** — currently `chmod 777` as a workaround for Podman rootless UID remap. Correct fix: `podman unshare chown 10001:10001` or `--userns=keep-id`
- [x] SBOM with Syft (CycloneDX format) — `deploy/container/sbom.cdx.json`
- [x] Image signing with cosign — `deploy/container/sbom.cdx.json.sigstore`

### Phase 12 — Final polish

- [x] README updated to reflect final state
- [x] `SECURITY.md` with disclosure policy
- [x] Dependabot enabled
- [x] MIT license
- [x] Git history cleaned of anything sensitive
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

    https://<UBUNTU_IP>

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

See [`SECURITY.md`](SECURITY.md) for the disclosure policy.

The repository is **public**. The lab's private IP addresses are
documented intentionally — they only exist inside an isolated virtual
network and cannot be reached from the Internet.

## License

MIT — see [`LICENSE`](LICENSE).
