# Risk Register — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.4
**Last updated:** 2026-10-22
**Inputs:** `docs/threat-model.md` (STRIDE analysis, findings #1–#6)

---

## 1. Purpose

This register tracks the risks identified in the threat model, their
classification, the treatment decision, and the residual risk once the
planned controls are in place.

It is a **living document**. Entries are added when the threat model
produces a finding, and updated when the treatment is implemented and
verified. When a finding is closed, the entry is not deleted — the
residual risk is recorded and the entry moves to §6 (Closed risks).

The register supports the requirements of:

- **ISO 27001 A.5.7, A.5.9, A.8.8** — threat intelligence, asset
  inventory, technical vulnerability management
- **NIS2 Article 21** — risk-management measures
- **GDPR Article 32** — security of processing

---

## 2. Scoring method

Risk = **Likelihood × Impact**, both on a scale of 1 to 5.

| Product | Severity |
|---------|----------|
| 1–4     | Low      |
| 5–9     | Medium   |
| 10–16   | High     |
| 17–25   | Critical |

### Likelihood

| Value | Meaning |
|-------|---------|
| 1     | Very unlikely — requires conditions that almost never occur |
| 2     | Unlikely — requires multiple simultaneous failures |
| 3     | Possible — plausible scenario within a year |
| 4     | Likely — expected scenario |
| 5     | Almost certain — occurs without intervention |

### Impact

| Value | Meaning |
|-------|---------|
| 1     | Negligible — no real consequences |
| 2     | Minor — nuisance, recoverable |
| 3     | Moderate — confidentiality or integrity affected, contained |
| 4     | Serious — significant data or service compromise |
| 5     | Catastrophic — total or irreversible compromise |

### Treatment options

- **Mitigate** — apply a control that reduces likelihood or impact
- **Accept** — cost of control exceeds benefit
- **Transfer** — shift the risk to a third party (insurance, outsourcing)
- **Avoid** — cease the activity that generates the risk

### Residual risk

The risk that remains **after** the treatment is applied. It is never
zero. The purpose of recording it is to show that the treatment reduces
the risk to an acceptable level, not that it eliminates it.

---

## 3. Active risks

### R-03 — CA private key stored unencrypted on the running server

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.7, Finding #5 |
| Description  | The CA private key (`~/pki/ca.key`) was generated with `-nodes` (no passphrase) and is stored on the same host that serves the application. |
| Likelihood   | **3** — depends on compromise of the host, which is the same precondition as R-02. Note that treating R-02 reduces the probability of R-03 as well, because the account that can read `ca.key` will no longer be the same account that runs the application. |
| Impact       | **5** — the CA key allows issuing a valid certificate for any identity. Any client that trusts the CA trusts everything the attacker signs. This is qualitatively worse than server key compromise (see threat model §7.7.1). |
| Severity     | **High (15)** |
| Treatment    | **Mitigate** |
| Control      | (1) Apply a passphrase to `ca.key` (`openssl rsa -aes256 -in ca.key -out ca.key.enc`). (2) Move the encrypted key off the running server to an offline location. (3) Consider generating a fresh key on an offline machine and reissuing the existing server certificate, instead of migrating the current one. |
| Phase        | Phase 10 (backup and restore) — the offline key handling pairs with the backup procedure. |
| Residual     | **Low (4)** — the key is encrypted at rest and not present on the running host. A compromised operator machine can still decrypt it, but that requires a second factor. |


### R-04 — GitHub account exposure (supply chain and history tampering)

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.8, Finding #6 |
| Description  | The GitHub account that hosts the repository has no 2FA, no signed commits, and no branch protection on `main`. The account is protected by password + device verification via email. The repository is private during development and only made public when complete. |
| Likelihood   | **2** — requires multiple simultaneous failures: (a) discover the password (unique, 15+ chars, stored in a password manager), (b) compromise the email account to intercept the device-verification code, (c) ideally the password manager or an unlocked device with an active session. |
| Impact       | **2** — while the repository is private, exposure gives the attacker a copy of code that will become public anyway. The only residual impact is **pre-publication advantage**: the attacker learns the architecture and can look for weaknesses ahead of the public. Once the repository is public, impact rises to 4 (supply chain); once treated (2FA + signed commits + branch protection), falls back to 2. |
| Severity     | **Low (4)** during development; **Medium (8)** if published without the planned controls. |
| Treatment    | **Mitigate** |
| Control (prevention) | (1) Enable 2FA on the GitHub account. (2) Configure GPG or SSH-signed commits and require them. (3) Branch protection on `main`: no force-push, no deletion, require signed commits. (4) Enable Dependabot. (5) Run `gitleaks` against the full history before public release. |
| Control (detection)  | See §R-04.1 below. |
| Control (containment)| See §R-04.2 below. |
| Control (recovery)   | Repository backup per the 3-2-1 rule: local clone on the Ubuntu host, remote on GitHub, and offline copy on an external disk kept disconnected. `[planned: phase 10]`. |
| Phase        | Prevention: Phase 12 (pre-publication polish). Backup: Phase 10. Detection and containment: documented in §R-04.1 and §R-04.2. |
| Residual     | **Low (4)** — the repository is private, the password is strong and unique, device verification is active, and push notifications are enabled. The remaining risk is pre-publication advantage in the (unlikely) event of a full account compromise. |

**Why this is not zero.** Zero risk does not exist in a risk register. The repository being private reduces *impact* (no supply chain until publication) but does not eliminate the *likelihood* of account compromise. A notification is a detection control, not a prevention control: the attacker has a time window between the action and the operator's response, and any data they have already cloned cannot be un-cloned. The controls reduce the exposure; they do not erase it.

#### R-04.1 — Detection controls

1. **Email notifications on push** — `[implemented]`. Any push to the
   repository triggers an email to the address configured in the
   repository settings. The notification contains the commit SHA, author,
   branch, changed files, and commit message.

2. **Out-of-band delivery** — `[implemented]`. The notification address is
   the operator's mobile device, not only the workstation. This reduces the
   detection window from hours (when at the workstation) to minutes,
   regardless of where the operator is.

3. **GitHub security log** — available and reviewed periodically. Retains
   90 days of activity on personal accounts. Covers events not reported by
   push notifications: additions of SSH keys, creation of personal access
   tokens, password changes, 2FA state changes.

#### R-04.2 — Containment procedure

If a push notification is received that does not correspond to an expected
action, the operator follows these steps in order:

1. **Verify on GitHub, not via the email.** Open
   `github.com/filipecastanheira-rgb/secure-fullstack-lab/commits/main`
   in a browser session already authenticated, and confirm whether the
   commit exists. Do not click links in the notification email — the
   notification itself could be spoofed.

2. **Change visibility to private** (if the repository is already public).
   This is the first action because it limits who can see the potentially
   altered state. It does not undo an already-cloned copy, but it stops
   the exposure from spreading.

3. **Revoke all credentials** for the account:
   - All deploy keys
   - All personal access tokens
   - The SSH key used for pushes from the Ubuntu host
   - Any active sessions in the account settings

4. **Rotate the account password** and **enable 2FA** immediately, if not
   already enabled.

5. **Review the commit history** with `git log -p` against a trusted local
   clone, to identify what was changed and whether the local copy still
   holds the pre-incident state.

6. **Record the incident** — date, detection time, actions taken, duration
   of exposure. This feeds the incident-response playbook
   (`docs/incident-response.md`, planned).

**Note.** This procedure is documented in the risk register for
convenience. It will be moved to the incident-response playbook once that
document exists, with a reference back to this entry.

### R-06 — SSH sessions are not recorded

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.7, Finding #4 |
| Description  | The SSH daemon records authentication events, but not the commands executed inside an authenticated session. There is no session recording, and `auditd` is not configured to watch sensitive paths. |
| Likelihood   | **2** — for this finding to matter, an attacker must already have valid SSH access. The key now requires a passphrase (mitigation applied in Session 9), so the attacker needs both the key file and the passphrase. |
| Impact       | **3** — loss of non-repudiation. An authenticated operator can deny an action and there is no recording to contradict them. Indirect impact on incident response and forensics. |
| Severity     | **Medium (6)** |
| Treatment    | **Mitigate** |
| Control      | (1) Install and configure `auditd` with watches on `/etc/`, `/home/<user>/secure-fullstack-lab/backend/`, and `~/pki/`. (2) Optionally, `tlog` for `sudo` session recording. (3) Ship audit logs off-host so a compromised host cannot erase its own evidence. |
| Phase        | Phase 8 (detection and monitoring). |
| Residual     | **Low (3)** — commands executed as `filipe` are recorded, changes to sensitive paths are logged. Sessions running as a future `secure-app` user still escape this (see R-02). |

### R-07 — No pagination on collection endpoints

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.2 (D2) and §7.4 (D2) |
| Description  | `GET /api/assets` returns the entire table as a single JSON response. With a growing dataset, the query and the response become increasingly expensive. |
| Likelihood   | **3** — the current dataset is small, but the roadmap includes a data-volume exercise in Phase 7 and Phase 10. Growth is expected. |
| Impact       | **2** — performance degradation, potential client timeout. No data loss or confidentiality impact. |
| Severity     | **Medium (6)** |
| Treatment    | **Mitigate** |
| Control      | Add `limit` and `offset` query parameters to the collection endpoint. Return a pagination envelope (`items`, `total`, `limit`, `offset`) instead of a bare list. |
| Phase        | Phase 4 (authentication) — the schema changes anyway when ownership is added. |
| Residual     | **Low (2)** — pagination is enforced. A client can still request large pages, but the server controls the maximum. |

### R-08 — Correlation-check service runs a user-writable script as root

| Field        | Value |
|--------------|-------|
| Source       | Review of `deploy/monitoring/correlation-check.service` (Session 25); related to R-02 |
| Description  | The systemd unit runs `correlation-check.sh` as `root` every 5 minutes, but the script lives in `/home/<user>/secure-fullstack-lab/deploy/monitoring/` and is writable by `filipe`. Anyone who can execute code as `filipe` (for example a malicious npm package during `npm install`) can edit the script and have it run as root within five minutes, without knowing the `sudo` password. This reopens the escalation path that R-02 closed. |
| Likelihood   | **2** — the attacker must already run code as `filipe`. The lab is not Internet-facing, but a compromised development dependency is a realistic route. |
| Impact       | **5** — root on the host exposes the CA private key, all credentials and the whole system. |
| Severity     | **High (10)** |
| Treatment    | **Mitigate** |
| Control      | (1) Install the script to `/usr/local/sbin/` owned by `root:root`, mode `0755`, and point `ExecStart` there, so `filipe` can no longer edit what root executes. (2) Optionally run the unit as a dedicated unprivileged user in the `adm` and `systemd-journal` groups, which is enough to read the Nginx log and the journal, and remove root from this path entirely. (3) Record the install step in the Ansible playbooks. |
| Phase        | Follow-up to Phase 8 (detection and monitoring). |
| Residual     | **Low (3)** — with a root-owned script, editing it already requires root, so there is no escalation left to gain (likelihood 1, impact 3). |
| Status       | **Mitigated (2026-10-19)** — the script is installed at `/usr/local/sbin/correlation-check.sh` (`root:root`, `0755`) and the unit's `ExecStart` points there. After any change to the script in the repository, it must be reinstalled with `sudo install`. |

### R-09 — Backup and GoAccess services run user-writable scripts as root

| Field        | Value |
|--------------|-------|
| Source       | External repository audit (2026-10-20); same class as R-08 |
| Description  | `backup.service` and `goaccess-report.service` ran `backup.sh` and `generate-goaccess-report.sh` as `root` from `/home/<user>/secure-fullstack-lab/deploy/`, a path writable by `filipe`. Anyone able to run code as `filipe` could edit either script and have it executed as root on the next timer run. The backup script also copies the JWT secret and deletes old files (`find -delete`) as root. R-08 was fixed for `correlation-check` only; the other two units were not reviewed at the time. |
| Likelihood   | **2** — the attacker must already run code as `filipe` (for example a malicious npm package). |
| Impact       | **5** — root on the host, plus access to the database and JWT secret copied by the backup. |
| Severity     | **High (10)** |
| Treatment    | **Mitigate** |
| Control      | Install both scripts to `/usr/local/sbin/` (`root:root`, `0755`) and point `ExecStart` there. Sweep of every unit in `/etc/systemd/system/` for `/home/<user>` paths: no other unit executes code from the home directory. |
| Phase        | Follow-up to Phases 8 and 10 (monitoring, backup). |
| Residual     | **Low (3)** — editing the scripts now requires root. |
| Status       | **Mitigated (2026-10-20)** — verified on the VM: `backup.service` created a new backup and `goaccess-report.service` regenerated the report, both from `/usr/local/sbin/`. After a change to either script in the repository, it must be reinstalled with `sudo install`. Lesson: when a risk is found in one unit, review all units of the same kind. |

### R-10 — Backup directory owned by the application user

| Field        | Value |
|--------------|-------|
| Source       | External repository audit (finding F-01); confirmed by test on 2026-10-22 |
| Description  | `/var/backups/secure-fullstack` was owned by `secure-app`, the user the application runs as. As `secure-app`, creating and deleting a file in the directory succeeded, so a compromised application could delete or replace the backups and their `.sha256` files. It could not read the database and secret backups: those files are `root:root`, mode 0640 and 0600. A related hypothesis (a symbolic link planted for the root-run script to follow) was not tested separately; it required the same write access to the directory, which the control removes. The backup README claimed that a compromise of the application could not delete its own backups; the test showed otherwise. |
| Likelihood   | **2** — the attacker must first compromise the application process. |
| Impact       | **3** — integrity and availability of the backups are affected, not confidentiality. Moderate: the live database is not touched, and the damage matters when combined with the loss or corruption of the live data. |
| Severity     | **Medium (6)** |
| Treatment    | **Mitigate** |
| Control      | Directory set to `root:root`, mode 0700 on the VM. `backup.sh` now creates it with `install -d -m 700 -o root -g root`, which also resets the permissions of an existing directory. |
| Phase        | Follow-up to Phase 10 (backup and restore). |
| Residual     | **Low (3)** — the application user has no access to the directory (likelihood 1, impact 3). |
| Status       | **Mitigated (2026-10-22)** — verified on the VM: after the change, `touch` as `secure-app` fails with exit 1. With the directory deliberately reset to `secure-app` 0750, `backup.service` (run at 08:56:33) restored `root:root` 0700 and finished with status 0/SUCCESS. The script is installed in `/usr/local/sbin/` and identical to the repository version. |

---

## 4. Accepted risks and deferred best practices

This section has two purposes: record risks that were identified in the threat model and **explicitly accepted** without a planned control, and record **recognised industry best practices that are not applied** in this context, with the rationale.

Documenting what was **not done** is as important as documenting what was. A control framework that only lists what is implemented fails the question *"why did you not implement X?"*.

### 4.1 Accepted risks

| Ref | Risk | Rationale for acceptance |
|-----|------|--------------------------|
| AR-01 | Nginx exposes its exact version in the `Server` header | The lab is not Internet-facing. The marginal benefit of `server_tokens off` is low relative to the operational cost of re-applying it after every Nginx upgrade. Re-evaluate if the lab is ever exposed. |
| AR-02 | No `Host` header validation in Nginx | Single-site deployment. The impact of a spoofed `Host` header is negligible until a second site exists on the same Nginx instance. |
| AR-03 | No OCSP or CRL for issued certificates | Certificates are few, long-lived, and the lab has a short operational lifetime. Revocation infrastructure is not justified. |
| AR-04 | Verbose Pydantic validation errors returned to clients | The 422 responses describe the schema. In this lab, this aids the developer and does not expose anything not already documented in the OpenAPI schema exposed by FastAPI. |
| AR-05 | SQLite write serialisation under concurrent load | Acceptable for the lab. PostgreSQL removes the constraint in production; the SQLAlchemy layer makes migration a connection-string change. |
| AR-06 | No second reviewer on pull requests to `main` ("Require approvals" disabled on 2026-10-19) | Single-maintainer repository: nobody else can approve, and a rule that cannot be satisfied gets bypassed. Pull requests and passing status checks (lint, tests, SAST, SCA, secrets scanning, DAST) remain mandatory, so every change is still gated by CI and leaves a record. See also DP-08. Re-evaluate if a second maintainer joins. |

### 4.2 Deferred best practices

Recognised practices that are **not applied** in this context, with rationale. Not "gaps" — intentional decisions.

| Ref | Best practice | Why not applied here | Where it would apply |
|-----|---------------|----------------------|----------------------|
| DP-01 | Backup on an external disk kept offline (3-2-1 rule) | Not yet acquired for this lab; the local clone and GitHub currently provide two copies. | Phase 10 — backup and restore. |
| DP-02 | HSM or dedicated hardware for the CA private key | The cost of a HSM is not justified for a lab CA with two certificates. The CA key is protected by the same account as the rest of the operator's files. | Production PKI; a small hardware token (YubiKey) can serve as a light alternative. |
| DP-03 | Automatic rotation of service credentials | The lab has no service accounts yet. Rotating nothing rotates automatically. | Phase 9 (configuration as code) introduces service accounts; rotation policy then applies. |
| DP-04 | WAF in front of Nginx | Overhead of tuning rules, false positives, and operational cost is not justified for an isolated lab with no public exposure. | Public-facing deployments. Not a substitute for application-layer controls in any case. |
| DP-05 | Centralised SIEM (Wazuh, Loki/Grafana, or equivalent) | The lab runs on small VMs; a SIEM stack requires resources beyond what the environment supports. Detection is implemented with `auditd`, `journalctl`, and lightweight correlation scripts. | Larger environments. Explicitly out of scope for this repository. |
| DP-06 | High availability (multiple servers, load balancing) | The lab runs on a single VM. Adding HA would not demonstrate additional security concepts at this scale. | Production deployments with availability requirements. |
| DP-07 | External penetration test | Out of scope for a personal lab. The DAST phase (OWASP ZAP) provides partial coverage. | Production systems; annually or before major releases. |
| DP-08 | Separation of duties (developer vs operator vs auditor) | A single-person lab cannot separate roles. The principle is acknowledged and applied to accounts where possible (admin / daily-use / service), but not to people. | Organisational contexts. Documented for awareness. |
| DP-09 | Containerisation of the frontend and reverse proxy | The current deployment (systemd + Nginx) is stable and proven. Only the backend is containerised, to demonstrate supply-chain tooling without rebuilding what already works. | Would apply to a fresh deployment; the concept is demonstrated in the backend phase. |
| DP-10 | Cloud deployment with posture assessment (Prowler, ScoutSuite) | Contradicts the design premise of the lab (isolated, no public exposure). A separate project. | A future cloud-security repository. |

## 5. Risk distribution

Snapshot of the register as of **2026-10-07**, after R-01 and R-05 closure.

### Current state

| Severity  | Active | Closed | Accepted |
|-----------|--------|--------|----------|
| Critical  | 0      | 0      | 0        |
| High      | 3      | 0      | 0        |
| Medium    | 2      | 1      | 0        |
| Low       | 1      | 0      | 0        |
| Accepted  | —      | —      | 5        |

**Active risks:** R-03 (High), R-04 (Low, during development),
R-06 (Medium), R-07 (Medium).

**Closed risks:** R-01, R-02, R-05.

**Accepted risks:** AR-01 to AR-05.

### Residual projection

Once every active risk is treated as planned:

| Severity  | Active | Residual |
|-----------|--------|----------|
| Critical  | 0      | 0        |
| High      | 2      | 0        |
| Medium    | 2      | 0        |
| Low       | 1      | 4        |

Every active risk has a treatment plan that reduces it to Low. No risk
is left untreated at High or Medium severity after the roadmap completes.

### Observations

- **Three risks closed so far.** R-01 (loopback binding), R-02
  (privilege separation), and R-05 (rate limiting). All three followed
  the same pattern: identified in the threat model, classified in the
  register, treated, verified with evidence, and moved to §6 with the
  commit reference.
- **The gap between current and residual is the roadmap.** Each remaining
  phase (10, 11, 12) closes one or more risks. The register makes the
  mapping explicit so progress is measurable.
- **Closure is not deletion.** A closed risk stays in §6 with its full
  history. The entry is a permanent record that the risk existed, was
  assessed, and was resolved. The identifier (R-01, R-02, R-05) is never
  reused.
- **R-02 was the highest-severity item in the register.** Its closure
  moved the highest active severity from High (15) to High (15) — but
  the *count* of high-severity risks dropped from three to two, and the
  two that remain are different in nature: R-03 is about a single file
  (the CA key), R-04 is about a single account (GitHub). Neither has
  the systemic reach that R-02 had.
- **Accepted risks do not change** with the roadmap. They were accepted
  by design, and their rationale stands (see §4.1). If the context
  changes — for example, if the lab is ever exposed to the Internet —
  the acceptance is revisited.

---

## 6. Closed risks

Risks whose treatment has been **implemented and verified**. The entry
records the commit, the verification method, and the date of closure.

### R-01 — FastAPI listens on all network interfaces

| Field        | Value |
|--------------|-------|
| Original severity | High (12) |
| Residual     | **Low (4)** — the API is only reachable from the host itself |
| Closed on    | 2026-10-05 |
| Commit       | `f0bd5ee` — "fix(api): bind FastAPI to loopback; close R-01 in risk register" |
**Control implemented.**

The systemd unit `ExecStart` was changed from:

    uvicorn app.main:app --host 0.0.0.0 --port 8000

to:

    uvicorn app.main:app --host 127.0.0.1 --port 8000

**Rationale.** Nginx runs on the same host as the API. It reaches the API
through the loopback interface (`127.0.0.1`), so binding to `0.0.0.0` was
never required. Binding to loopback ensures that **even if UFW is disabled**
— for troubleshooting, for example — the API remains unreachable from any
network interface. The defence no longer depends on a single layer.

**Verification.**

1. `ss -ltnp | grep 8000` on the host now shows:

        LISTEN 0 2048 127.0.0.1:8000 ... uvicorn

   Previously: `0.0.0.0:8000`.

2. `https://<UBUNTU_IP>` in the Kali browser continues to work — the
   full application (Vue frontend, API proxy to FastAPI) loads and the
   assets table is populated. The Nginx → FastAPI path is unaffected.

3. From the Kali VM, `nc -zv -w 3 <UBUNTU_IP> 8000` returns
   `Connection timed out`. This was already true before the change (UFW
   blocked it), and remains true now that nothing is listening on the
   network interface at all.

**Post-closure notes.**

- The change is captured in `deploy/systemd/secure-fullstack-api.service`
  once the file is re-copied to the repository.
- The threat model entry **§7.2** that first flagged this (Finding #1)
  remains valid — it is the origin of this risk, and is preserved for
  traceability.
---


### R-05 — No rate limiting at any layer

| Field        | Value |
|--------------|-------|
| Original severity | Medium (9) |
| Residual     | **Low (3)** — the login endpoint is protected at the edge; abuse cost is significantly higher |
| Closed on    | 2026-10-07 |
| Commits      | `d30a1ba` (auth dependencies), `3a17149` (Nginx rate limiting) |

**Control implemented.**

Rate limiting was added at the Nginx edge, in two distinct zones:

    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m   rate=60r/m;

- **`login`** — 5 requests per minute, burst of 3. Applied to a
  `location = /api/auth/login` block with exact-match semantics, so it
  is not shadowed by the broader `/api/` location.
- **`api`** — 60 requests per minute, burst of 20. Applied to all other
  `/api/` endpoints.

Both zones use `limit_req_status 429` so that exceeded limits return
`429 Too Many Requests` instead of the Nginx default `503`.

**Why two zones and not one.**

A single zone cannot serve both purposes. A rate tuned for login (5 per
minute) would break normal application usage (listing assets, fetching
the current user, submitting forms). A rate tuned for the application
(60 per minute) would allow a script to attempt thousands of password
combinations per hour against the login endpoint. Differentiating the
two is what makes the control fit for purpose.

**Why the exact-match location matters.**

Nginx matches locations by specificity: the more specific prefix wins.
`location = /api/auth/login` is an exact match and takes precedence over
`location /api/`. Without the exact-match modifier, the login endpoint
would fall under the general `api` zone and inherit the 60r/m rate —
which would defeat the purpose of the stricter zone.

**Verification.**

The login endpoint was probed with a loop of 10 requests from a single
client:

    for i in $(seq 1 10); do
      curl -s -o /dev/null -w "%{http_code}" \
        -X POST https://<UBUNTU_IP>/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"teste@example.com","password":"..."}'
    done

Observed result:

    Pedido 1: 401    ← authentication rejected by FastAPI, Nginx allowed
    Pedido 2: 401
    Pedido 3: 401
    Pedido 4: 401
    Pedido 5: 429    ← Nginx refused (rate limit + burst exhausted)
    Pedido 6: 429
    ... (429 for remaining requests)

The transition from 401 to 429 confirms that:

1. The rate bucket is keyed by client IP and counts correctly.
2. The burst allowance is exhausted before blocking begins.
3. Requests are refused with `429`, not delayed (via `nodelay`).
4. The refusal is generated by Nginx (response body is HTML), not by the
   FastAPI application (which would return JSON). The request never
   reaches the backend.

**Post-closure notes.**

- **Per-IP limitation.** The rate limit is applied per source IP. Behind
  NAT, multiple legitimate users share the same IP and would share the
  same bucket. In the current lab, each client has a distinct IP, so the
  limitation is theoretical. In a production deployment, additional
  application-level rate limiting keyed by authenticated user id would be
  necessary. This is recorded as a known limitation, not a gap — the
  network-level control is doing what it should.
- **Distributed attacks remain out of scope.** A botnet with many IPs
  could distribute the load and stay under the limit per IP. Mitigating
  that requires infrastructure beyond the scope of this lab (CDN with
  global rate limiting, or a WAF).
- **`limit_conn_zone` not used.** The original control description also
  mentioned connection limits. Only request limits were implemented,
  because connection exhaustion is addressed at the TCP level by the
  Nginx worker configuration and by UFW. Reconsidered if evidence of
  connection-level abuse appears.


### R-02 — No privilege separation (closed)

| Field        | Value |
|--------------|-------|
| Original severity | High (15) |
| Residual     | **Low (3)** — the application runs as a dedicated unprivileged user with no access to the PKI directory, the SSH key, or sudo |
| Closed on    | 2026-10-17 |
| Commits      | `a00da9e` (manual migration), Phase 9 Ansible playbook (reproducible) |

**Control implemented.**

The application was moved out of the operator's account and into a
dedicated system user, `secure-app`, with no shell, no `sudo`, and no
home directory. The process, the code, the venv, the database, and the
JWT secret were all relocated:

| Item | Before | After |
|------|--------|-------|
| Process user | `filipe` | `secure-app` |
| Code | `~/secure-fullstack-lab/backend/` | `/opt/secure-fullstack/backend/` |
| Venv | `~/.../.venv` | `/opt/secure-fullstack/venv/` |
| Database | `~/.../backend/lab.db` | `/var/lib/secure-fullstack/lab.db` |
| JWT secret | `~/.../backend/.jwt_secret` | `/var/lib/secure-fullstack/.jwt_secret` |
| Frontend | `~/.../frontend/dist/` | `/var/www/secure-fullstack/` |
| Nginx root | `/home/<user>/...` | `/var/www/secure-fullstack` |
| `/home/<user>` | `drwxr-x--x` (`o+x`) | `drwxr-x---` |

**Why this closes the risk.** Before, a compromise of the application
was a compromise of `filipe` — and therefore of the CA private key in
`~/pki/`, the SSH key from Kali, and `sudo`. After, a compromise of the
application is a compromise of `secure-app`, which can read its own
code and its own data and nothing else.

**Verified:**

- `/api/hello` responds on both `127.0.0.1:8000` and `https://<UBUNTU_IP>`
- Login works (secure-app reads `users` and `.jwt_secret`)
- Asset creation works (secure-app writes to `lab.db`)
- The Vue SPA loads from `/var/www/`
- `/home/<user>` is `drwxr-x---` — no other user can traverse
- The Ansible playbook reproduces this state from scratch, with
  `changed=0` on a second run

**Residual risk.** `secure-app` can still read its own code and its own
database. An attacker who compromises the application has access to
the assets inventory and can modify it. This is inherent to any
application that processes data: the process must be able to reach the
data. What the separation removes is the **escalation** from "the app"
to "the host and its credentials".

---

## 7. Revision history

| Date       | Version | Change |
|------------|---------|--------|
| 2026-10-04 | 1.0     | Initial register. Consolidated findings #2 and #3 into R-02. Added R-05 (rate limiting) and R-07 (pagination) from threat model entries that did not generate formal findings. |
| 2026-10-19 | 1.1     | Added R-08 (correlation-check service runs a user-writable script as root) and AR-06 (no second reviewer on `main`). |
| 2026-10-19 | 1.2     | R-08 mitigated: correlation-check script installed root-owned under `/usr/local/sbin/`. |
| 2026-10-20 | 1.3     | Added R-09 (backup and GoAccess services ran user-writable scripts as root), mitigated the same day after an external audit. |
| 2026-10-22 | 1.4     | Added R-10 (backup directory owned by the application user, external audit finding F-01), mitigated the same day. |
