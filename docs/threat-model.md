# Threat Model — Secure Fullstack Lab

**Method:** STRIDE
**Version:** 1.0 (draft)
**Owner:** Filipe Castanheira
**Last updated:** 2026-10-25

---

## 1. Scope and assumptions

### 1.1 Purpose

This document identifies and prioritises the threats against the Secure
Fullstack Lab application, its data, and its supporting infrastructure.
It exists to:

- inform the design of controls (authentication, authorisation, logging),
- drive the security pipeline (what to test automatically),
- feed the risk register with concrete, prioritised items,
- provide auditable evidence of risk reasoning for the portfolio.

### 1.2 Modelling assumptions

**Principle: the lab simulates production.**

The system is modelled and built **as if it were going to production**.
Isolation, absence of public exposure, and temporary lifetime are *not*
accepted as reasons to lower the bar. If a practice is standard in
production environments, it is implemented here, or explicitly deferred
with a technical justification.

This means:

- Personal data protection obligations (GDPR) are treated as applicable.
- Availability, integrity, and confidentiality are treated as real
  requirements, not as best-effort.
- The system is treated as persistent, not disposable.
- Controls that exist only for compliance optics are rejected; controls
  that address real threats are kept even when the lab cannot be reached
  from the Internet.

The purpose is twofold: to build a portfolio artefact that reflects real
engineering practice, and to force the deeper understanding that comes
from implementing a control in full rather than in outline.

### 1.2.1 Deferred items — what this principle does NOT mean

The principle above does not mean "implement everything immediately". It
means "every deferred item must have a technical reason, not an
environmental excuse". The following deferrals are accepted, each with a
specific rationale:

| Deferred item                          | Rationale for deferral                                                |
|----------------------------------------|-----------------------------------------------------------------------|
| Service account for the application    | Requires re-mapping file ownership, systemd unit, and Nginx perms.    |
|                                        | Cost/benefit improves after authentication introduces real users.     |
| SSH certificate authority              | Depends on privilege separation being in place first (Finding #3);    |
|                                        | otherwise the SSH CA key inherits the same trust collapse.            |
| Containerisation of frontend + proxy   | The current deployment is stable and proven; re-doing it gains no     |
|                                        | new concept. Only the backend is containerised, for supply chain.     |
| Full SIEM (Wazuh, Loki/Grafana)        | Hardware constraint (VM RAM). A separate project; logging in this lab |
|                                        | is implemented with auditd, journalctl, and correlation scripts.      |
| Cloud deployment                       | Contradicts the design premise (isolated lab). Separate repository.   |

**Passphrase on the operator's SSH key** is *not* deferred. It is applied
immediately as a partial mitigation for S4 (key theft), even though the
final mitigation (SSH certificates) is deferred.

### 1.3 Status markers

Every control referenced in this document is tagged with its status:

- `[implemented]` — exists in the current system
- `[planned]` — exists in the roadmap, not yet built
- `[gap]` — identified but not scheduled

The gap list (§10) is the input to the risk register.

### 1.4 Out of scope

- Physical security of the host laptop (mitigated by OS-level disk
  encryption, fingerprint login, and the device remaining at home).
- The home network infrastructure (documented separately, not part of this
  repository).
- Cloud deployment (a separate project).

---

## 2. System description

### 2.1 High-level architecture (target state)

    ┌──────────────────────────────────────────────────────────────┐
    │                    Untrusted network                          │
    │            (lab segment / would be the Internet)              │
    └────────────────────────┬─────────────────────────────────────┘
                             │
                             │ HTTPS (TLS 1.2/1.3)
                             │
                  ┌──────────▼───────────┐
                  │   Nginx  :443        │   [implemented]
                  │   • TLS termination  │
                  │   • static assets    │
                  │   • /api/* proxy     │
                  │   • security headers │
                  └──────────┬───────────┘
                             │
                             │ HTTP (localhost only)
                             │
                  ┌──────────▼───────────┐
                  │   FastAPI  :8000     │   [implemented]
                  │   • REST API         │
                  │   • Pydantic schemas │
                  │   • JWT auth         │   [implemented]
                  │   • RBAC             │   [implemented]
                  │   • rate limiting    │   [implemented]
                  └──────────┬───────────┘
                             │
                             │ SQLAlchemy
                             │
                  ┌──────────▼───────────┐
                  │   SQLite (lab.db)    │   [implemented]
                  └──────────────────────┘

    Host-level controls (Ubuntu server):

    ┌──────────────────────────────────────────────────────────────┐
    │ UFW          :22 (Kali only), :80, :443          [implemented]│
    │ Fail2Ban     SSH brute-force protection          [implemented]│
    │ sshd         key-only, no root, allowlist        [implemented]│
    │ auditd       system call auditing                [planned]    │
    │ Structured logs (JSON) in FastAPI                [planned]    │
    └──────────────────────────────────────────────────────────────┘

### 2.2 Components

| Component    | Role                                    | Trust level  |
|--------------|-----------------------------------------|--------------|
| Nginx        | TLS endpoint, static files, API proxy   | High         |
| FastAPI      | Application logic, auth, data access    | High         |
| SQLAlchemy   | ORM layer                               | High         |
| SQLite       | Data store                              | High         |
| Vue SPA      | Browser application                     | Low (client) |
| systemd      | Process supervision                     | High         |
| UFW          | Host firewall                           | High         |
| Fail2Ban     | Brute-force mitigation                  | High         |
| PKI (CA)     | Certificate issuance                    | Critical     |

### 2.3 Primary data flows

1. **User → Nginx → static files.** Browser fetches the Vue SPA over HTTPS.
2. **User → Nginx → FastAPI → SQLite.** Browser calls `/api/*`; Nginx
   proxies to FastAPI, which reads/writes SQLite via SQLAlchemy.
3. **Administrator → SSH → Ubuntu.** Key-based SSH from the Kali VM.
4. **FastAPI → SQLite (file).** Direct file access on the same host.

### 2.4 Deployment context

- Two VMs on isolated VMware segments.
- No Internet exposure; no public DNS; no public certificates.
- Internal CA issued by us (not a public CA).
- Not a 24/7 service — started when working on it.

---

## 3. Data classification

### 3.1 Classification labels

| Label        | Definition                                            |
|--------------|-------------------------------------------------------|
| Public       | Safe to disclose to anyone                            |
| Internal     | Not sensitive, but not for external distribution      |
| Confidential | Would cause harm if disclosed                         |
| Restricted   | Would cause serious harm; strict need-to-know         |

### 3.2 Data inventory

| Data                              | Classification | Notes                                     |
|-----------------------------------|----------------|-------------------------------------------|
| Asset list (hostname, IP, OS)     | Internal       | Operational inventory; no personal data   |
| User accounts (email, name)       | Confidential   | Personal data — GDPR applies  [planned]   |
| Password hashes (argon2id)        | Restricted     | Compromise = credential reuse risk        |
| JWT signing keys                  | Restricted     | Compromise = impersonation of any user    |
| Session tokens                    | Restricted     | Short-lived but sensitive                 |
| CA private key (`ca.key`)         | Restricted     | Compromise = forge any certificate        |
| Server private key (`server.key`) | Restricted     | Compromise = impersonation of server      |
| `lab.db` file                     | Confidential   | Contains all of the above                 |
| Audit logs                        | Confidential   | Contain user identifiers, source IPs      |
| Application logs                  | Internal       | Structured; may contain user IDs          |
| Source code                       | Public         | Portfolio repository (once public)        |
| Configuration (Nginx, UFW)        | Internal       | Reveals architecture if leaked            |

### 3.3 Data lifecycle

| Phase     | Treatment                                                  |
|-----------|------------------------------------------------------------|
| Collection| Only data strictly necessary (data minimisation)           |
| Storage   | SQLite on the VM disk; no encryption seen (see AR-07)      |
| Access    | Restricted to app process (UID) and admins (sudo)          |
| Retention | No personal data currently; once users exist: 24 months    |
| Deletion  | User deletion request triggers cascade delete  [planned]   |
| Backup    | Daily snapshot of `lab.db` and JWT secret; 7-day retention |

### 3.4 GDPR relevance

Once user accounts exist (Phase 4), the system processes **personal data**:

- Email address, name (if collected)
- Login timestamps and source IPs
- Potentially session metadata

Applicable GDPR principles:

- **Art. 5** — lawfulness, purpose limitation, data minimisation
- **Art. 15-22** — data subject rights (access, rectification, erasure)
- **Art. 32** — security of processing (encryption, access control)
- **Art. 33-34** — breach notification (72 hours to supervisory authority)

For a Portuguese deployment, the supervisory authority is **CNPD**.

**Current status:** `[planned]` — the system does not yet process personal
data. This section is a design constraint for Phase 4, not a present
obligation.


---

## 4. Assets

Assets are the things we are protecting. They fall into four groups:
**data**, **services**, **credentials**, and **supporting infrastructure**.
Each asset is linked to its classification (§3.2) where applicable.

### 4.1 Data assets

| ID   | Asset                          | Classification | Where it lives            |
|------|--------------------------------|----------------|---------------------------|
| A-01 | Asset inventory                | Internal       | SQLite                    |
| A-02 | User accounts (email, name)    | Confidential   | SQLite            [planned]|
| A-03 | Password hashes (argon2id)     | Restricted     | SQLite            [planned]|
| A-04 | `lab.db` (all of the above)    | Confidential   | Filesystem                |
| A-05 | JWT signing keys               | Restricted     | Env / filesystem  [planned]|
| A-06 | CA private key (`ca.key`)      | Restricted     | `~/pki/`                  |
| A-07 | Server private key             | Restricted     | `/etc/nginx/ssl/`         |
| A-08 | Application and audit logs     | Confidential   | Journald / files  [planned]|

### 4.2 Service assets

| ID   | Asset                          | Availability req. | Notes                     |
|------|--------------------------------|-------------------|---------------------------|
| A-10 | Nginx (TLS endpoint)           | High              | Single entry point        |
| A-11 | FastAPI application            | High              | Business logic            |
| A-12 | SQLite database engine         | High              | Single point of failure   |
| A-13 | SSH access to Ubuntu           | Medium            | Administrative channel    |

### 4.3 Access assets

| ID   | Asset                          | Notes                                         |
|------|--------------------------------|-----------------------------------------------|
| A-20 | Administrative SSH access      | Kali only, key-based         [implemented]    |
| A-21 | VMware console access          | Break-glass, no app-layer auth                |
| A-22 | GitHub repository              | Code integrity and history   [private]        |
| A-23 | `sudo` on the Ubuntu host      | Root-equivalent on the server                 |

### 4.4 Integrity-critical assets

These are not about confidentiality. These are things whose **tampering**
would break the security of everything else:

| ID   | Asset                          | Why it matters                                |
|------|--------------------------------|-----------------------------------------------|
| A-30 | `sshd_config` and hardening files | Tampering reopens closed attack surface    |
| A-31 | UFW rules                      | Tampering exposes internal services           |
| A-32 | Nginx configuration            | Tampering can redirect or downgrade traffic   |
| A-33 | Fail2Ban rules and filter      | Tampering disables a layer of defence         |
| A-34 | systemd unit files             | Tampering alters what runs and how            |
| A-35 | Audit and access logs          | Tampering destroys forensic evidence          |
| A-36 | Git history                    | Tampering hides what really happened          |

**Note on A-36 (Git history):** if an attacker can rewrite the history of
the repository (for example, by compromising a maintainer's SSH key), they
can retroactively hide the introduction of a backdoor. This is a real
concern in software supply chain attacks, and it is why signed commits and
branch protection exist.

---

## 5. Trust boundaries

A trust boundary is a line across which the **level of trust changes**.
Every boundary is a place where an attacker can try to cross from a
less-trusted zone into a more-trusted one.

### 5.1 Boundary diagram

    ┌────────────────────────────────────────────────────────────┐
    │  ZONE 1 — Untrusted                                        │
    │  Lab network / would be the Internet                       │
    │                                                            │
    │  Actor: browser on Kali                                    │
    └────────────────────────────┬───────────────────────────────┘
                                 │
                   (B1) HTTPS :443 — TLS + headers
                                 │
    ┌────────────────────────────▼───────────────────────────────┐
    │  ZONE 2 — DMZ (edge)                                       │
    │  Nginx                                                     │
    │                                                            │
    │  Trusts: nothing from Zone 1 except well-formed requests   │
    └────────────────────────────┬───────────────────────────────┘
                                 │
                   (B2) HTTP localhost :8000 — no auth
                                 │
    ┌────────────────────────────▼───────────────────────────────┐
    │  ZONE 3 — Application                                      │
    │  FastAPI + SQLAlchemy                                      │
    │                                                            │
    │  Trusts: Nginx headers (X-Real-IP, X-Forwarded-For)        │
    └────────────────────────────┬───────────────────────────────┘
                                 │
                   (B3) File system access
                                 │
    ┌────────────────────────────▼───────────────────────────────┐
    │  ZONE 4 — Data                                             │
    │  SQLite, keys, config                                      │
    └────────────────────────────────────────────────────────────┘

    Separate administrative boundaries:

    ┌──────────────┐   (B4) SSH :22    ┌──────────────────────┐
    │  Kali        │ ────────────────▶ │  Ubuntu — privileged │
    │  (operator)  │   key-only        │  shell               │
    └──────────────┘                   └──────────────────────┘

    ┌──────────────┐   (B5) VMware     ┌──────────────────────┐
    │  Host laptop │ ────────────────▶ │  Ubuntu — console    │
    │  (physical)  │   no app auth     │  full access         │
    └──────────────┘                   └──────────────────────┘

    ┌──────────────┐   (B6) git push   ┌──────────────────────┐
    │  Ubuntu      │ ────────────────▶ │  GitHub repository   │
    │  (developer) │   SSH key         │  code + history      │
    └──────────────┘                   └──────────────────────┘

### 5.2 Boundary descriptions

**B1 — Untrusted network → Nginx.**
The only application-facing ingress. Everything from outside the host must
cross here. Controls at this boundary:

- TLS 1.2/1.3 with our CA                                 `[implemented]`
- Security headers (HSTS, CSP, X-Frame-Options, …)        `[implemented]`
- Rate limiting on application endpoints                  `[gap]`
- WAF rules                                               `[gap]` — deliberately
  out of scope; the lab is not Internet-facing

**B2 — Nginx → FastAPI.**
Internal boundary, currently over plain HTTP on localhost. The trust
assumption is that only Nginx talks to FastAPI. Two problems to note:

- `[gap]` **FastAPI listens on `0.0.0.0:8000`.** Although UFW blocks
  external access, the service itself binds to all interfaces. If UFW is
  ever disabled, or a new network interface appears, FastAPI becomes
  reachable directly, bypassing Nginx (and therefore bypassing TLS, CSP,
  and any future rate limiting at the edge). This is **Finding #1**.
- `[gap]` **No shared secret between Nginx and FastAPI.** Anything that
  can reach `localhost:8000` is treated as trusted.

**B3 — FastAPI → SQLite / filesystem.**
The application process runs as user `filipe`, with the same privileges as
the human operator. There is no separation between the app and its data
at the OS level. `[gap]` — a dedicated service account with restricted
file permissions would be more correct.

**B4 — Operator → Ubuntu over SSH.**
Administrative boundary. Controls at this boundary:

- Key-only authentication (no passwords)                  `[implemented]`
- `PermitRootLogin no`                                    `[implemented]`
- `AllowUsers filipe`                                     `[implemented]`
- UFW: SSH allowed only from `<KALI_IP>` (Kali)       `[implemented]`
- Fail2Ban: bans after repeated failures                  `[implemented]`

**B5 — Physical host → VM console.**
The break-glass boundary. Whoever is at the keyboard of the host laptop
has, via VMware, full console access to the VM with no application-layer
authentication. This cannot be mitigated by software in the VM. Controls:

- Host OS disk encryption                                  external
- Host OS fingerprint + password login                     external
- Device remains at home                                   external

This boundary is acknowledged as **out of scope** for software mitigations,
but is recorded here because it dominates every other control: if B5 is
lost, all other boundaries are irrelevant.

**B6 — Developer machine → GitHub.**
Supply chain boundary. What crosses here becomes the canonical version of
the source code. Controls:

- SSH key authentication to GitHub                         `[implemented]`
- Conventional commits                                     `[implemented]`
- Signed commits                                           `[gap]`
- Branch protection on `main`                              `[gap]`
- Dependabot alerts                                        `[planned]`
- Secret scanning (gitleaks in CI)                         `[planned]`

---

## 6. Threat actors

Who might attack this system, and why. Each actor has different
capabilities and different motivations, which is why the mitigations
differ.

| ID   | Actor                            | Capability   | Motivation                |
|------|----------------------------------|--------------|---------------------------|
| T-01 | External attacker on lab network | Low–Medium   | Opportunistic, scanning   |
| T-02 | Malicious insider (user account) | Medium       | Data theft, sabotage      |
| T-03 | Compromised admin workstation    | High         | Lateral movement          |
| T-04 | Supply chain attacker            | Medium–High  | Backdoor, persistence     |
| T-05 | Automated bot / scanner          | Low          | Mass exploitation         |
| T-06 | Physical attacker on host laptop | High         | Full compromise           |

### 6.1 Notes on actor selection

**T-01 — External attacker on lab network.**
This is the "would be the Internet" actor. In the lab, the only machine on
the untrusted segment is the Kali VM. In production this would be any host
on the Internet. The threats are the standard ones: scanners, credential
stuffing, exploitation of known CVEs, resource exhaustion.

**T-02 — Malicious insider.**
Once authentication exists (Phase 4), users will exist. An insider is a
user who attempts to access data they should not see — this is where
**IDOR** and **broken access control** threats live. This actor is the
reason RBAC matters.

**T-03 — Compromised admin workstation.**
If the Kali VM (or any operator machine) is compromised, the attacker
inherits the operator's SSH key. This is why `AllowTcpForwarding no` and
`AllowAgentForwarding no` matter — they limit what a compromised client
can do with its own credentials.

**T-04 — Supply chain attacker.**
Two angles:
1. Compromise of a dependency (PyPI, npm) — mitigated by SCA scanning and
   pinned versions.
2. Compromise of the developer's GitHub account — mitigated by signed
   commits and branch protection.

**T-05 — Automated bot / scanner.**
Distinct from T-01 because the motivation is not targeted — it is mass
opportunism. The defences that matter most are the ones that work without
human judgment: UFW, Fail2Ban, key-only SSH, absence of default credentials.

**T-06 — Physical attacker.**
Out of scope for software mitigations, but recorded because it dominates
every other control. If the host laptop is taken, disk encryption is the
only barrier between the attacker and `~/pki/ca.key`. Full-disk encryption
on the laptop is therefore a **critical compensating control**.



---

## 7. STRIDE analysis

Each component is analysed against the six STRIDE categories. Threats
are labelled (e.g. `S1`, `T2`) so they can be referenced elsewhere —
in the risk register, in tests, and in the vulnerability exercise.

**Format:**

- **Description** — what the threat is
- **Scenario** — how it would manifest in *this* system
- **Status** — `[implemented]` / `[planned]` / `[gap]`
- **Finding** — if there is an actionable gap, it gets a `Finding #N` label

---

### 7.1 Nginx (TLS endpoint and reverse proxy)

#### S — Spoofing

**S1. No client authentication at the TLS layer.**
Nginx proves its own identity to the client (the certificate), but does not
verify the identity of the client. Any party with a connection to the
lab network can reach the endpoint.
*Scenario:* an attacker on the lab segment — a second VM, or the Kali VM
itself if compromised — connects directly. No credential is required.
*Status:* `[gap]` — mutual TLS would mitigate, but is not required for a
public web application. Accepted risk.

**S2. No `Host` header validation.**
The single `server` block accepts any value for the HTTP `Host` header.
There is no catch-all block that rejects unknown hosts.
*Scenario:* a request with `Host: evil.example.com` is accepted. On a
single-site deployment the impact is low, but it breaks a hygiene rule and
would matter in a multi-tenant setup.
*Status:* `[gap]` — add a default `server` block that returns 444 (drop)
for unknown Host values.

#### T — Tampering

**T1. Transit integrity.**
TLS provides integrity. Responses modified in transit are detected by the
client.
*Status:* `[implemented]`

**T2. Configuration integrity.**
If an attacker gains write access to `/etc/nginx/`, they can modify what is
served or redirect the API proxy to a server they control.
*Scenario:* requires root or the `filipe` account (which has `sudo`). This
is the same trust problem as Finding #2.
*Status:* `[gap]` — file integrity monitoring (AIDE, or `auditd` watches)
would detect changes. It would not prevent them, but detection is what
matters here.

**T3. Static content integrity.**
The built frontend is served from `/var/www/secure-fullstack/`, owned by
`www-data:www-data` with mode `drwxr-xr-x` (checked 2026-10-21). The
operator account can no longer overwrite the served files, but the Nginx
user owns them, so a compromised Nginx worker could still modify them.
*Status:* `[implemented partial]` — files moved out of the home directory
and not writable by the operator account. Residual: ownership by
`www-data` instead of `root`.

#### R — Repudiation

**R1. Logs are not protected.**
`access_log` and `error_log` live in `/var/log/nginx/`. They can be edited
or deleted by root. They are not shipped anywhere else.
*Scenario:* an attacker with root access erases the lines that prove they
were there.
*Status:* `[gap]` — off-host log shipping would mitigate. Out of scope for
this lab, but recorded.

**R2. Real client IP preserved.**
`X-Real-IP` and `X-Forwarded-For` are set on every proxied request, so the
API knows the actual client IP, not `127.0.0.1`.
*Status:* `[implemented]`

#### I — Information disclosure

**I1. Server version exposed.**
The `Server: nginx/1.28.3 (Ubuntu)` header reveals the exact version.
*Scenario:* an attacker scans, sees the version, looks up the CVEs, tries
the one that applies.
*Status:* `[gap]` — `server_tokens off;` hides it. Trivial fix.

**I2. No authentication on API endpoints.**
Any client on the lab network can list and create assets.
*Status:* `[implemented]` — all API endpoints now require a valid JWT.

**I3. User enumeration at the login endpoint.**
Once authentication exists, a login endpoint that distinguishes "user does
not exist" from "wrong password" allows an attacker to enumerate valid
accounts.
*Status:* `[implemented]` — the login endpoint returns a generic "Invalid email or password" for all failure cases, preventing user enumeration.

#### D — Denial of service

**D1. No rate limiting at the edge.**
An attacker can send thousands of requests per second. Nginx will hold
longer than FastAPI, but the backend will eventually saturate.
*Status:* `[gap]` — `limit_req_zone` and `limit_conn_zone` are the Nginx
directives. Planned for Phase 4 / 6.

**D2. Slowloris.**
Slow-header clients occupy connection slots.
*Status:* `[gap]` — mitigations: `client_header_timeout`,
`client_body_timeout`, `send_timeout`.

**D3. UFW partially protects.**
Port 8000 is blocked and port 22 is restricted. Ports 80 and 443 are open
to the lab network.
*Status:* `[implemented]` partial.

#### E — Elevation of privilege

**E1. Path traversal on static files.**
A crafted URL could attempt `../../../etc/passwd`.
*Status:* `[implemented]` — `try_files` handles path resolution safely in
the current Nginx version.

**E2. SSRF through `/api/`.**
If the API ever accepts a URL from the client and fetches it, the attacker
can use the server as a proxy to reach internal resources.
*Status:* `[planned]` — code review in Phase 4 to ensure no such endpoint
exists.

**E3. Proxy misconfiguration.**
A mistake in `proxy_pass` path handling could expose routes that were not
intended.
*Status:* `[implemented]` — the current configuration is correct.

---

### 7.2 FastAPI (application logic, authentication, data access)

#### S — Spoofing

**S1. No client identity.**
FastAPI does not identify the client at all. Every request is treated as
equally trustworthy. This is not a spoofing *vulnerability* — it is the
absence of any identity to spoof.
*Scenario:* a client on the lab network calls any endpoint with no
credential, and the API treats the call as legitimate.
*Status:* `[implemented]` — JWT-based authentication is in place.

**S2. JWT forgery — `alg: none` (future).**
Once JWT is introduced, a misconfigured server may accept a token whose
header declares `"alg": "none"`, allowing an attacker to craft an unsigned
token that is accepted.
*Scenario:* attacker intercepts their own JWT, changes the payload to
`{"sub": "admin"}`, removes the signature, changes the header to `none`,
and sends it.
*Status:* `[implemented]` — the implementation explicitly passes `algorithms=["HS256"]` to `jwt.decode()`, closing the `alg: none` vector.

**S3. JWT forgery — weak signing key (future).**
If the signing key is short or guessable, the attacker can compute a valid
signature for any payload.
*Status:* `[implemented]` — the key is 64 bytes from `secrets.token_urlsafe`, stored in `backend/.jwt_secret` (mode `0600`, gitignored).

**S4. JWT theft (future).**
If an attacker can read the token from the browser (XSS, shared device,
log leakage), they can impersonate the user until the token expires.
*Status:* `[partial]` — short-lived access tokens (15 min) are in place, along with a strict CSP. Refresh tokens were added after this section was first written (as of 2026-10-25: 7-day lifetime, accepted only by `/api/auth/refresh`, no revocation list; the token presented stays valid until it expires, and only deactivating the account stops further refreshes). `HttpOnly` cookies are not yet implemented.

#### T — Tampering

**T1. Input validation via Pydantic.**
Malformed input is rejected before reaching the endpoint function.
*Scenario:* client sends `{"hostname": 12345}` — number instead of string.
Pydantic rejects with HTTP 422.
*Status:* `[implemented]`

**T2. Mass assignment — currently protected.**
`AssetCreate` declares exactly three fields. Any extra fields in the
request are ignored by Pydantic.
*Scenario:* client sends `{"hostname": "x", "ip_address": "y", "os": "z",
"role": "admin"}` — the `role` field is dropped.
*Status:* `[implemented]` — must remain true as the schemas grow.

**T3. SQL injection — protected by SQLAlchemy.**
SQLAlchemy parameterises queries by default, so client-supplied strings are
never interpreted as SQL.
*Scenario:* client sends `hostname = "'; DROP TABLE assets; --"` — stored
literally as a string, never executed.
*Status:* `[implemented]` — must be re-verified in Phase 7 with a
deliberate test case.

**T4. JWT payload tampering (future).**
If the server does not verify the signature, an attacker can change
`role: user` to `role: admin` in the payload.
*Status:* `[implemented]` — the signature is verified in `decode_token`; any payload change invalidates it.

#### R — Repudiation

**R1. No audit trail.**
No user actions are logged with identity. If someone deletes an asset, there
is no record of who did it.
*Status:* `[gap]` — structured logging with user context is planned for
Phase 8.

**R2. Required logging fields.**
To support non-repudiation, each security-relevant event must capture:
- Who (authenticated subject)
- What (operation)
- When (timestamp, trustworthy source)
- Where from (source IP)
- Outcome (success or failure)

*Status:* `[planned: phase 8]`

#### I — Information disclosure

**I1. Open read endpoints.**
`GET /api/assets` returns the full list to anyone who asks.
*Status:* `[implemented]` — endpoints require a valid JWT.

**I2. Verbose validation errors.**
Pydantic's 422 responses describe the exact schema, including field names,
types, and constraints. Helpful for debugging; also helpful for an attacker
mapping the API.
*Status:* `[gap]` — in production, consider returning a generic error and
logging the detail server-side.

**I3. Debug mode.**
If the API runs with debug enabled, HTTP 500 responses include stack traces
with file paths and variable contents.
*Status:* `[implemented]` — not running in debug mode.

**I4. Log leakage.**
If logs record passwords, tokens, or sensitive fields in clear text, anyone
with log access can read them.
*Status:* `[planned: phase 8]` — logging policy must define what must
never be logged.

#### D — Denial of service

**D1. No rate limiting on the API.**
Any client can issue unlimited requests. A simple loop saturates the
backend within seconds.
*Status:* `[gap]` — `limit_req_zone` in Nginx and per-endpoint limits for
authentication. Planned for Phase 4.

**D2. Unbounded collection endpoints.**
`GET /api/assets` returns the whole table. With a very large table, both
the server and the client would suffer.
*Status:* `[gap]` — pagination is required before the data volume grows.

**D3. SQLite write serialisation.**
SQLite serialises writes. High POST volume blocks the write path.
*Status:* `[known limitation]` — acceptable for the lab. PostgreSQL
removes this constraint in production.

#### E — Elevation of privilege

**E1. Not applicable yet.**
Without authentication there are no distinct privilege levels. Every
client has the same effective power.
*Status:* `[not applicable]` — will change in Phase 4.

**E2. IDOR — Insecure Direct Object Reference (future).**
Once objects belong to users, an endpoint like `GET /api/assets/{id}` must
verify ownership, not just existence.
*Scenario:* user A requests `/api/assets/42`, which belongs to user B. If
the endpoint only filters by ID, user A reads user B's data.
*Status:* `[partial: phase 7]` — authentication exists; the IDOR test will be introduced in Phase 7 to demonstrate detection and fix.

**E3. Mass assignment on update (future).**
A permissive update schema could allow a user to set fields they should
not control (e.g. `role`, `owner_id`).
*Status:* `[implemented]` — `UserCreate` restricts `role` to `Literal["user", "admin"]`; Pydantic ignores undeclared fields.

**E4. JWT role tampering (future).**
Same as T4, from the privilege perspective: a forged token with an elevated
role grants elevated access.
*Status:* `[implemented]` — signature verification prevents payload tampering.

---

### 7.3 Authorization levels (cross-cutting note)

Not every STRIDE item above is about the same kind of control. There are
three distinct levels at which authorisation must be enforced, and they are
**independent**:

| Level | Question                                     | Where it lives        |
|-------|----------------------------------------------|-----------------------|
| L1    | Can this subject call this endpoint?         | Auth dependency, RBAC |
| L2    | Can this subject see this row?               | Query filter (IDOR)   |
| L3    | Can this subject see this field of this row? | Response schema       |

A system that implements only L1 is vulnerable to IDOR. A system that
implements L1 and L2 but leaks sensitive fields is vulnerable to
information disclosure at the field level. All three are required.

This is why the response schemas (`AssetRead`, `UserSelfRead`,
`UserAdminRead`) are separate from the ORM models — the schema is the
mechanism for L3.



---

### 7.4 SQLite (data store)

**Note on the nature of SQLite.** SQLite is not a network service. It is a
library that reads and writes a single file. There is no user
authentication, no network listener, and no concept of roles inside the
database. The security of the data therefore depends entirely on:

- the permissions of the file on disk,
- the identity of the process that opens it,
- the queries the application issues.

This is why this section has fewer applicable STRIDE entries than Nginx or
FastAPI, and why the *surrounding* layers carry most of the weight.

#### S — Spoofing

**S1. Not applicable.**
SQLite does not identify callers. There is no identity to spoof.
*Status:* `[not applicable]`

#### T — Tampering

**T1. The file can be edited directly.**
Anyone with filesystem access can open `lab.db` with the `sqlite3` CLI and
modify rows. There is no integrity check on the file contents.
*Scenario:* an attacker running as `filipe` changes a `hostname` value.
The API cannot detect the change.
*Status:* `[gap]` — detection via file-hash monitoring or an `auditd`
watch on `lab.db`. Detection, not prevention.

**T2. Sidecar files (`-wal`, `-shm`).**
In WAL mode SQLite keeps auxiliary files next to the database. Editing
those has the same effect as editing the main file.
*Status:* `[gap]` — same mitigation as T1.

#### R — Repudiation

**R1. No audit trail inside the database.**
No triggers record who changed what. If a row is deleted directly in the
database, there is no record.
*Status:* `[gap]` — application-level structured logging (Phase 8) and/or
SQLite audit triggers.

#### I — Information disclosure

**I1. File readable by the application user.**
`lab.db` lives in `/var/lib/secure-fullstack/`, owned by
`secure-app:secure-app` with mode `0640`, in a directory with mode `0750`
(checked 2026-10-21). The operator account is not in the `secure-app`
group, so it cannot read the database directly. Any process running as
`secure-app` can read the entire dataset, which is expected because it is
the application user. The operator can still reach the data through
`sudo` or equivalent privileged access, the same trust problem as
Finding #2.
*Status:* `[implemented partial]` — database moved out of the home
directory and readable only by the application user and root. Residual:
operator privileged access.

**I2. Backups unprotected (future).**
When backups are implemented (Phase 10), copies of `lab.db` will exist.
If stored in plaintext on an accessible path, this is a data leak.
*Status:* `[planned]`

**I3. Temporary files during writes.**
SQLite may create temporary files during writes. An attacker able to read
them in real time could observe data in transit within the filesystem.
*Status:* `[gap]` — restrict the directory to the application user only.

#### D — Denial of service

**D1. Writes are serialised.**
SQLite allows concurrent reads but serialises writes. High-volume POST
traffic blocks the write path.
*Status:* `[known limitation]` — acceptable for the lab. PostgreSQL
removes the constraint in production.

**D2. Unbounded reads.**
`GET /api/assets` returns the whole table. With a large dataset, the query
and the resulting JSON become expensive.
*Status:* `[gap]` — pagination (already recorded under FastAPI D2).

**D3. File corruption.**
An abrupt termination during a write (e.g. `kill -9`) can, in rare cases,
corrupt the database.
*Status:* `[implemented partial]` — SQLite's journal/WAL mode protects
against most cases. `PRAGMA integrity_check` is available to verify.

#### E — Elevation of privilege

**E1. Not applicable directly.**
SQLite has no privilege model. Read access is total or nothing.

**E2. SQL injection via dynamically built queries.**
SQLAlchemy parameterises queries by default, but a developer can bypass
that protection by building SQL strings manually.
*Status:* `[gap]` — code review and a deliberate injection test case in
Phase 7.

---

### 7.5 Cross-component finding: no privilege separation

**Finding #3 — the application runs as the human operator.**

The FastAPI process, the `lab.db` file, the human operator's shell, the SSH
key from Kali, and the CA private key in `~/pki/` all share the same
account: `filipe`.

    filipe (single account)
      ├── owns lab.db
      ├── runs uvicorn
      ├── has sudo
      ├── owns ~/pki/ca.key
      ├── receives the Kali SSH key
      └── is the human user

There is no isolation between "the application", "the data", and "the
operator". A single compromise of `filipe` compromises everything.

**Correct design (production):**

    secure-app (system user, no shell, no sudo)
      ├── runs uvicorn
      └── owns lab.db only

    filipe (human)
      ├── has sudo
      ├── owns ~/pki/
      └── manages the host

**Rationale.** This is the same principle as "run as non-root" — but
applied *within* the host. Each component gets the minimum privilege it
needs. Finding #2 and Finding #3 are related: both are about the app
running with more privilege than necessary.

**Status:** `[planned]` — will be addressed in a future hardening phase
after authentication is introduced.

**Why it is deferred:** changing the service account now would require
migrating `lab.db` ownership, updating the systemd unit, adjusting the
Nginx static file permissions, and re-testing everything — for no
functional benefit until users exist. The cost/benefit changes once the
authentication phase is complete.


---

### 7.6 SSH (administrative access to the Ubuntu server)

**Note on the nature of SSH.** SSH is the only interactive administrative
channel into the host. It is also the only service where the client is
authenticated cryptographically. This makes it the strongest boundary in
the system — and the one where the most controls are already in place.

#### S — Spoofing

**S1. Client authentication by key only.**
The server accepts authentication exclusively via public key. Password
authentication is disabled. An attacker cannot impersonate a legitimate
operator without possession of the private key.
*Status:* `[implemented]`

**S2. Root login disabled.**
`PermitRootLogin no` prevents any attempt to log in as root, regardless
of authentication method. All administrative actions require logging in
as `filipe` first, then using `sudo`. This produces an audit trail.
*Status:* `[implemented]`

**S3. User allowlist.**
`AllowUsers filipe` rejects every other account before authentication
even starts. A new user added to the host does not automatically gain
SSH access.
*Status:* `[implemented]`

**S4. Key compromise — residual risk.**

If the private key on the Kali VM is stolen, the attacker gains SSH
access. UFW, Fail2Ban, and every other control are irrelevant at this
point: the key is the identity.

*Scenario:* the Kali VM is compromised, or the key file is exfiltrated.
The attacker can connect from any IP permitted by UFW.

**Mitigations — status:**

- **Passphrase on the private key** — `[implemented]`. The key file on
  disk is now encrypted. An attacker who exfiltrates the file alone cannot
  use it without the passphrase. This closes the "file copied" scenario
  but not the "session already open" or "passphrase intercepted" scenarios.

- **SSH certificates with short lifetimes** — `[planned]`. A dedicated SSH
  CA issues certificates valid for a fixed short period (hours). The static
  key stops being an identity and becomes a key *pair* used only to request
  short-lived certificates. This reduces the attack window from
  "indefinite" to "hours", and enables revocation without rotating
  credentials on every host.

  **Deferred because of ordering.** Implementing the SSH CA before fixing
  Finding #3 (privilege separation) would add critical material to the
  same account that already holds the TLS CA key. The cost of the ordering
  mistake is higher than the benefit of the earlier implementation.

- **Periodic key rotation** — operational discipline, not a technical
  control. Recommended as a companion to the SSH CA once it exists.

*Status:* `[implemented partial]` — passphrase applied; SSH CA deferred to
a later hardening phase, after Finding #3 is addressed.

#### T — Tampering

**T1. Configuration integrity.**
`/etc/ssh/sshd_config.d/99-hardening.conf` defines the current policy. If
an attacker gains write access to it, they can re-enable password login or
re-allow root.
*Scenario:* an attacker with root access edits the file, restarts the
service, and reopens the attack surface. No alarm is raised.
*Status:* `[gap]` — an `auditd` watch on `/etc/ssh/` would detect the
change. Detection, not prevention.

**T2. Host key stability.**
The server's host key is what the client sees on first connection. If the
host key changes unexpectedly, the client refuses to connect — this is the
mechanism behind the "host key has changed" warning.
*Status:* `[implemented]`

#### R — Repudiation

**R1. Authentication events are logged.**
`sshd` writes authentication events to the systemd journal. Both successful
and failed attempts are recorded with the source IP and the key fingerprint
used.
*Status:* `[implemented]`

**R2. Session activity is not logged centrally.**
Once a session is authenticated, the commands executed inside it are not
captured. There is no `sudo` audit beyond the default journal entries.
*Status:* `[planned]` — `auditd` in a later phase.

#### I — Information disclosure

**I1. Key fingerprints visible in the logs.**
The `sshd` log contains the fingerprint of every key that attempted
authentication. This is useful for detection but is itself information: an
attacker with log access learns which keys are in use.
*Status:* `[accepted]` — this is normal and desirable; logs are protected
by their own layer.

**I2. Banner and version disclosure.**
The SSH banner reveals the OpenSSH version. There is no `Banner` directive
disclosing anything further.
*Status:* `[gap]` — could be minimised, but the marginal benefit is low
for an internal service.

#### D — Denial of service

**D1. Fail2Ban mitigates brute-force.**
Repeated authentication failures from a single IP result in a temporary ban
via UFW. Verified end-to-end in Session 8: after 5 failed attempts the IP
was banned and the ban appeared as a UFW rule.
*Status:* `[implemented]`

**D2. `LoginGraceTime` and `MaxAuthTries`.**
Authentication attempts are time-limited (30 seconds) and rate-limited
(3 per connection), which limits the resource cost of an attacker holding
connections open.
*Status:* `[implemented]`

**D3. UFW limits reachability to one source IP.**
Only `<KALI_IP>` (the Kali VM) can reach port 22. This is a strong
constraint — but note that UFW filters *by source IP*, and IP spoofing is
technically possible in limited scenarios.
*Status:* `[implemented]` — note that this and D1 are **independent**
layers. UFW filters by origin; Fail2Ban filters by behaviour. If one is
bypassed, the other still applies.

#### E — Elevation of privilege

**E1. `sudo` requires the account password.**
An attacker who gains access as `filipe` via the SSH key still needs the
account password to run commands with `sudo` — assuming a password is set
and not cached.
*Status:* `[implemented]` — but see Finding #4 below.

**E2. TCP forwarding disabled.**
`AllowTcpForwarding no` prevents an authenticated user from using the
Ubuntu host as a jump host to reach other machines on the lab network.
This is a common lateral-movement technique.
*Status:* `[implemented]`

**E3. Agent forwarding disabled.**
`AllowAgentForwarding no` prevents the client's SSH agent from being
reachable from the server, which would allow an attacker on the server to
use the client's other keys.
*Status:* `[implemented]`

---

### 7.7 Cross-component finding: no session recording

**Finding #4 — SSH activity is not recorded beyond authentication.**

`sshd` logs the fact that an authentication succeeded. It does not log the
commands executed inside the session. If an attacker gains SSH access and
performs actions, the only evidence is what those actions leave behind
(filesystem changes, journal entries from the commands themselves).

**Why this matters for non-repudiation.** An authenticated operator can
deny performing an action, and there is no session recording to contradict
them.

**Mitigation (future):**
- `auditd` with a comprehensive set of watches on sensitive paths
- `tlog` or equivalent session recording for `sudo` sessions
- Centralised log shipping so an attacker cannot tamper with logs locally

**Status:** `[planned]` — in the hardening-extension phase after
authentication is complete.

**Note on scope.** This is a lower-priority finding than Findings #1-#3
because it depends on an attacker already having SSH access, which
requires the private key. It is recorded for completeness and to inform
the design of the detection phase.


---

### 7.7 PKI (internal Certificate Authority)

**Note on the nature of the CA.** The CA is not a running service. It is
the pair (`ca.key`, `ca.crt`) that signs every certificate this lab
issues. It exists only when we run `openssl` to sign something. Its value
is entirely in *what can be signed with it*.

#### S — Spoofing

**S1. Any certificate signed by the CA is trusted.**
A client that trusts `ca.crt` trusts every certificate signed by `ca.key`,
without further verification. This is by design: trust propagates from the
CA to everything it issues.
*Scenario:* if an attacker has `ca.key`, they can sign a certificate for
any hostname or IP address that any trusting client will accept.
*Status:* `[implemented]` — this is the correct PKI model. The threat is
not the propagation, it is the compromise of the CA key.

**S2. No revocation mechanism.**
If `server.crt` is compromised, there is no way to tell clients to stop
trusting it. CRL and OCSP are not configured.
*Scenario:* a stolen `server.key` can be used for MITM for as long as the
certificate remains valid (825 days).
*Status:* `[gap]` — for a lab, acceptable. In production, OCSP or short
certificate lifetimes are required.

#### T — Tampering

**T1. The `ca.key` file can be modified or replaced.**
An attacker with write access to `~/pki/` can substitute a different key.
The new key would then be used for all future issuances, silently.
*Status:* `[gap]` — file integrity monitoring (`auditd` watch on `~/pki/`).

**T2. The `ca.crt` distributed to clients could be replaced.**
If the CA certificate installed on Kali is replaced with a different one,
any certificate signed by the *new* CA is trusted instead.
*Scenario:* requires access to the Kali VM (boundary B5).
*Status:* `[gap]` — detection would require comparing fingerprints manually.

#### R — Repudiation

**R1. Issued certificates are not logged.**
No record exists of which certificates have been issued, with what subject,
SAN, or validity period. `ca.srl` holds the last serial number but nothing
else.
*Status:* `[gap]` — for a lab with two certificates, negligible. In a real
PKI, a log of issuances is standard.

#### I — Information disclosure

**I1. `ca.key` is readable by `filipe`.**
The CA private key is stored unencrypted (generated with `-nodes`) in
`~/pki/`. Any process running as `filipe` can read it.
*Scenario:* a compromised process running as `filipe` exfiltrates the key
and can then forge any certificate.
*Status:* `[gap]` — this is the **single most critical asset in the lab**.
Mitigations: (a) encrypt the key with a passphrase; (b) store it offline
when not in use; (c) move it to a separate account or a dedicated CA host.

**I2. `ca.key` is present on the running server.**
The CA key lives on the same machine that serves the application.
Best practice is to keep the CA offline — used only to sign, never present
on a production host.
*Status:* `[gap]` — accepted for the lab. Documented here so the
deviation is intentional and visible.

#### D — Denial of service

**D1. Loss of `ca.key` invalidates the entire trust chain.**
If the CA key is lost, no new certificates can be issued, and there is no
way to re-sign existing ones. The entire PKI must be rebuilt.
*Scenario:* accidental deletion, failed backup, disk corruption.
*Status:* `[gap]` — backup of `~/pki/` is planned for Phase 10.

**D2. Loss of `ca.crt` on clients.**
If the CA certificate is removed from a client's trust store, every
certificate issued by that CA is rejected.
*Status:* `[gap]` — same remediation as D1.

#### E — Elevation of privilege

**E1. `ca.key` compromise = arbitrary trust.**
An attacker with the CA private key can issue a valid certificate for
**any** identity. They can impersonate the application, the host, or any
other service that trusts this CA.
*Scenario:* attacker issues a certificate for `<UBUNTU_IP>` with a
stolen private key, redirects traffic, and the client trusts the
certificate silently.
*Status:* `[gap]` — the only mitigations are: keep the key safe, encrypt
it, and never put it on a host that serves untrusted content.

---

#### 7.7.1 Why CA compromise is qualitatively worse than server key compromise

This is a distinction worth making explicit. The two keys are not
equivalent:

| If the attacker has...   | They can...                                              |
|--------------------------|----------------------------------------------------------|
| `server.key`             | Impersonate *this one server* to clients                 |
| `ca.key`                 | Issue a valid certificate for *any* identity             |

**Server key compromise is bounded.** The attacker can only pretend to be
the server the certificate belongs to. If the certificate is revoked (when
revocation exists), the attack stops.

**CA key compromise is unbounded.** The attacker can mint certificates for
hostnames that do not exist yet, for IPs they do not control, for services
they have never touched. Any client that trusts the CA trusts all of them.
Revoking the CA means revoking everything at once.

This is why real-world PKIs keep the CA key **offline**, use a
**hardware security module**, require **multiple operators**, and log every
issuance. This lab does none of those things — it is documented as a
deviation.

**Finding #5 — the CA private key is stored unencrypted on the running
server.**

Severity: high. Treatment: encrypt the key, and consider moving it
off-host when not in use. Deferred to the hardening-extension phase.

---

### 7.8 GitHub (source of truth for the code)

**Note on the nature of this component.** GitHub is the only component in
the system that is **not under our physical control**. The application,
the database, the certificates, and the SSH service are all on the Ubuntu
host. The repository lives on servers operated by Microsoft.

This changes the threat model. Controls that exist on the host (UFW,
Fail2Ban, file permissions) do not apply here. The only controls available
are the ones GitHub provides, plus the discipline of the operator.


#### 7.8.1 Repository visibility policy

The repository is **private during development** and is only made public when
the project is complete. This is a deliberate design decision, not a
convenience.

**What it gives:**

- Time to complete the pre-publication hygiene (full history scan with
  `gitleaks`, license, security policy, README polish) without pressure.
- Reduced exposure while the code is still changing: no forks, no scrapers,
  no half-finished snapshots indexed by search engines.
- A single, explicit moment when the repository becomes visible — chosen by
  the operator, not by accident.

**What it does NOT give:**

- It does not make the account invisible. An attacker who compromises the
  GitHub account (via password, SSH key, or session) can clone the private
  repository exactly as if it were public. "Private" means "not indexed",
  not "not accessible".
- It does not eliminate the impact of pre-publication exposure. An attacker
  who obtains the code before public release has an information advantage:
  time to study the architecture and prepare.

**Impact of the policy on the risk model:**

| Repository state | Impact of exposure |
|------------------|-------------------|
| Private during development | Low — the code will be public eventually; exposure only grants pre-publication advantage |
| Public without 2FA / signed commits / branch protection | High — supply chain attack; malicious code published in the operator's name |
| Public after full treatment | Low — no force-push, signed commits, and detection in place |

**Conclusion:** the private-during-development policy reduces the impact of
exposure to a manageable level, but does not remove the need for the
prevention controls planned for Phase 12. The two are complementary.


#### S — Spoofing

**S1. Authentication is by SSH key.**
Access to the repository is via an SSH key on the Ubuntu host, or via the
web interface with a password.
*Status:* `[implemented]` — key-based.

**S2. Two-factor authentication not enabled.**
The GitHub account has no 2FA configured. If the account password is
compromised, the attacker gains access.
*Scenario:* credential stuffing, phishing, or password reuse on another
site.
*Status:* `[gap]` — enable 2FA. This is a one-time change with a
material impact on the account.

**S3. The SSH key used for GitHub has no passphrase.**
Same class of risk as the SSH operator key. If the Ubuntu host is
compromised, the GitHub access is inherited.
*Status:* `[gap]` — apply the same passphrase treatment as the Kali key.

#### T — Tampering

**T1. `git push --force` can rewrite history.**
The owner of the repository can force-push and rewrite the commit history
of `main`. Anyone cloning afterwards sees the new history; the old one is
gone unless someone has a local copy.
*Scenario:* an attacker with access to the account rewrites history to hide
the introduction of a backdoor.
*Status:* `[gap]` — **branch protection** on `main` prevents force-push
even by the owner, unless the protection is explicitly disabled.

**T2. Commits are not signed.**
There is no cryptographic proof that a commit was authored by the
legitimate operator. GitHub attributes commits by the email address in the
commit, which is trivial to fake.
*Scenario:* an attacker pushes a commit with the operator's email set in
`user.email` — GitHub shows it as "authored by Filipe".
*Status:* `[gap]` — GPG or SSH-signed commits would close this.

**T3. No integrity check on cloned copies.**
If someone clones the repo to work on it, they have no way to verify the
code has not been altered since the last trusted commit.
*Status:* `[gap]` — signed commits and tags address this.

#### R — Repudiation

**R1. GitHub has its own audit log.**
Repository actions (pushes, settings changes, branch operations) are
recorded by GitHub and visible in the account settings.
*Status:* `[implemented]` — but only for the last 90 days on the free tier.

**R2. No local mirror of the audit log.**
If the GitHub account is compromised and the audit log is accessed by the
attacker, they can hide their activity by deleting the events.
*Status:* `[gap]` — periodic export of the audit log would help.

#### I — Information disclosure

**I1. Public repository.**
The repository is public, so the code is intentionally disclosed. The
relevant risk is leaking secrets or environment details through the
repository or its history. See I2 and I3.
*Status:* `[implemented partial]` — no secrets detected in history (see
I2). Residual: environment details in history (see I3).

**I2. Secrets in history.**
If any secret was ever committed — even if removed later — it remains in
the history and is recoverable with `git log -p`.
A full-history scan was run locally with the official `gitleaks` image
and its default rules on 2026-10-22: 117 commits scanned, no leaks
found. The commit count matched `git rev-list --count --no-merges --all`
after `git fetch --all --prune`.
*Status:* `[implemented partial]` — default rules only, so a secret in
an unusual format could be missed. Residual: no recurring full-history
scan.

**I3. `.gitignore` protects new files, not old ones.**
The extended `.gitignore` we added prevents *future* commits of keys and
certificates. It does not remove anything that was committed previously.
The full-history scan in I2 covers secrets. It does not cover environment
details: earlier commits contain private (RFC 1918) addresses of the lab
network, home-directory paths and the operator account name (checked on
2026-10-22 with `git log --all -S`: 28 and 22 commits touched the address
and the path). Most documentation no longer contains them, but some
configuration files and the journal still do.
The addresses belong to the lab network behind the OPNsense VM, not to the
home network, and the lab addressing is usually changed when a project
ends. That is not a commitment. Rewriting the history of a public
repository with signed commits and merged pull requests has real costs.
*Status:* `[accepted]` — accepted by the project owner on 2026-10-22.
Residual: lab addresses, paths and the operator account name remain
readable in history and in some current configuration files.

#### D — Denial of service

**D1. GitHub can suspend the account.**
Policy violations, a compromised account reported by others, or a billing
issue can result in suspension. The repository becomes unavailable to
clones and CI.
*Status:* `[accepted]` — nothing can be done about this; the mitigation
is a local clone on the Ubuntu host, which we have.

**D2. Dependency on a third party.**
The canonical version of the source code lives on Microsoft-operated
servers. This is a deliberate trade-off.
*Status:* `[accepted]` — mitigated by keeping a local `git` clone, which
already exists.

#### E — Elevation of privilege

**E1. The account owner can do anything.**
The owner of the repository can delete the repo, add collaborators, modify
protected branches (with the setting enabled), and push to `main`.
This is by design, but it means that compromising the account compromises
all repositories under it.
*Status:* `[implemented]` — by design.

**E2. A compromised GitHub account is a supply-chain attack vector.**
If the account is compromised, the attacker can publish code in the
operator's name. Anyone who trusts the operator will trust the code.

*The cost is not only the loss of the repository.* It is that the
operator's **name** becomes associated with malicious code. For a
portfolio repository, this is a reputational and trust problem, not just a
technical one. A portfolio that says "trust my security work" cannot afford
to be the vector of a supply-chain attack.

**Finding #6 — the GitHub account lacks 2FA, signed commits, and branch
protection.**

Severity: high (for a public-facing portfolio repository). Treatment:
enable 2FA, enable signed commits, add branch protection to `main`, enable
Dependabot, and scan the full history with `gitleaks` before the repo is
made public.

Deferred to the pre-publication phase (Phase 12). These controls make no
difference while the repo is private, but become critical the moment it is
visible.
