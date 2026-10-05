# Risk Register — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.0
**Last updated:** 2026-10-04
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

### R-02 — No privilege separation (application runs as the human operator)

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.5, Findings #2 and #3 (consolidated) |
| Description  | The FastAPI process, the `lab.db` file, the CA private key (`~/pki/ca.key`), the human operator's shell, the SSH key from Kali, and `sudo` access all share the same account: `filipe`. There is no isolation between "the application", "the data", and "the operator". |
| Likelihood   | **3** — the application runs as `filipe`, so any compromise of the application inherits `filipe`'s privileges. The attack surface (unauthenticated API) increases the probability, but a successful exploit of the application is not trivial. |
| Impact       | **5** — a compromise of `filipe` is a compromise of the host. The attacker inherits: the database, the CA private key, SSH access from Kali, and `sudo`. Everything falls in one step. |
| Severity     | **High (15)** |
| Treatment    | **Mitigate** |
| Control      | (1) Create a dedicated system user `secure-app` with no login shell and no `sudo`. (2) Transfer `lab.db` ownership to this user. (3) Update the systemd unit to run the service as `secure-app`. (4) Adjust Nginx static file permissions accordingly. (5) Move the CA private key out of `~/pki/` — ideally off-host. |
| Phase        | Phase 9 (configuration as code) — the migration is scriptable and pairs naturally with Ansible. |
| Residual     | **Low (4)** — compromise of the app process is contained. Compromise of the operator account still affects `sudo` and the PKI, but no longer the application data or the runtime. |

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
| Control (detection)  | (1) **Email notifications on push** — `[implemented]`. Any push triggers an email to the configured address. (2) Periodic review of the GitHub security log (90-day retention on personal accounts). |
| Control (containment)| Documented procedure for the "account compromise" scenario: make the repository private again (if already public), revoke all deploy keys and personal access tokens, rotate the SSH key, change the account password, review the commit history for unreviewed changes. This procedure belongs in `docs/incident-response.md` (planned). |
| Control (recovery)   | Repository backup per the 3-2-1 rule: local clone on the Ubuntu host, remote on GitHub, and offline copy on an external disk kept disconnected. `[planned: phase 10]`. |
| Phase        | Prevention controls: Phase 12 (pre-publication polish). Backup: Phase 10. Detection and containment: documented in the incident-response playbook when written. |
| Residual     | **Low (4)** — the repository is private, the password is strong and unique, device verification is active, and push notifications are enabled. The remaining risk is pre-publication advantage in the (unlikely) event of a full account compromise. |

**Why this is not zero.** Zero risk does not exist in a risk register. The repository being private reduces *impact* (no supply chain until publication) but does not eliminate the *likelihood* of account compromise. A notification is a detection control, not a prevention control: the attacker has a time window between the action and the operator's response, and any data they have already cloned cannot be un-cloned. The controls reduce the exposure; they do not erase it.
### R-05 — No rate limiting at any layer

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.1 (D1) and §7.2 (D1) |
| Description  | Neither Nginx nor the FastAPI application implements rate limiting. Any client can send unlimited requests. A simple loop saturates the backend within seconds. |
| Likelihood   | **3** — requires an attacker on the lab network, but any attacker with access to the endpoint will attempt resource exhaustion as a first step. |
| Impact       | **3** — availability loss, contained. The host can be restarted, and the lab is not a production service. Impact will rise once authentication is added and login endpoints become the target of credential brute force. |
| Severity     | **Medium (9)** |
| Treatment    | **Mitigate** |
| Control      | (1) Add `limit_req_zone` and `limit_conn_zone` in Nginx at the edge. (2) Add per-endpoint limits for authentication endpoints in the application, once they exist. |
| Phase        | Phase 4 (authentication) for the login endpoints; Phase 6 (pipeline) for the Nginx configuration. |
| Residual     | **Low (4)** — the attack surface is reduced and the cost of abuse is raised significantly. Distributed attacks remain possible but out of scope for a lab. |

### R-06 — SSH sessions are not recorded

| Field        | Value |
|--------------|-------|
| Source       | Threat model §7.7, Finding #4 |
| Description  | The SSH daemon records authentication events, but not the commands executed inside an authenticated session. There is no session recording, and `auditd` is not configured to watch sensitive paths. |
| Likelihood   | **2** — for this finding to matter, an attacker must already have valid SSH access. The key now requires a passphrase (mitigation applied in Session 9), so the attacker needs both the key file and the passphrase. |
| Impact       | **3** — loss of non-repudiation. An authenticated operator can deny an action and there is no recording to contradict them. Indirect impact on incident response and forensics. |
| Severity     | **Medium (6)** |
| Treatment    | **Mitigate** |
| Control      | (1) Install and configure `auditd` with watches on `/etc/`, `/home/filipe/secure-fullstack-lab/backend/`, and `~/pki/`. (2) Optionally, `tlog` for `sudo` session recording. (3) Ship audit logs off-host so a compromised host cannot erase its own evidence. |
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

Snapshot of the register as of **2026-10-05**, after R-01 closure.

### Current state

| Severity  | Active | Closed | Accepted |
|-----------|--------|--------|----------|
| Critical  | 0      | 0      | 0        |
| High      | 3      | 1      | 0        |
| Medium    | 3      | 0      | 0        |
| Low       | 0      | 0      | 0        |
| Accepted  | —      | —      | 5        |

**Active risks:** R-02 (High), R-03 (High), R-04 (Low, during
development), R-05 (Medium), R-06 (Medium), R-07 (Medium).

**Closed risks:** R-01.

**Accepted risks:** AR-01 to AR-05.

### Residual projection

Once every active risk is treated as planned:

| Severity  | Active | Residual |
|-----------|--------|----------|
| Critical  | 0      | 0        |
| High      | 3      | 0        |
| Medium    | 3      | 0        |
| Low       | 0      | 6        |

Every active risk has a treatment plan that reduces it to Low. No risk
is left untreated at High or Medium severity after the roadmap completes.

### Observations

- **The gap between current and residual is the roadmap.** Each remaining
  phase (4, 9, 10, 12) closes one or more risks. The register makes that
  mapping explicit so progress is measurable, not impressionistic.
- **R-01 is the first risk closed.** It demonstrates the full cycle:
  identified in the threat model, classified here, treated, verified, and
  recorded with evidence. Subsequent closures follow the same format.
- **Accepted risks do not change** with the roadmap. They were accepted
  by design, and their rationale stands (see §4.1). If the context changes
  — for example, if the lab is ever exposed to the Internet — the
  acceptance is revisited.
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
| Commit       | *(preencher após commit)* |

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

2. `https://192.168.1.173` in the Kali browser continues to work — the
   full application (Vue frontend, API proxy to FastAPI) loads and the
   assets table is populated. The Nginx → FastAPI path is unaffected.

3. From the Kali VM, `nc -zv -w 3 192.168.1.173 8000` returns
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

## 7. Revision history

| Date       | Version | Change |
|------------|---------|--------|
| 2026-10-04 | 1.0     | Initial register. Consolidated findings #2 and #3 into R-02. Added R-05 (rate limiting) and R-07 (pagination) from threat model entries that did not generate formal findings. |
