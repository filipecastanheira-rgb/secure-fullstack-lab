# Control Mapping — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.0
**Effective date:** 2026-10-05
**Classification:** Internal

---

## 1. Purpose

This document maps the controls implemented in the Secure Fullstack Lab to
recognised security frameworks. Its purpose is to make the relationship
between what is built and what standards require **explicit**, rather than
implicit.

Three reasons this document exists:

1. **For the operator.** A control is only meaningful if it can be traced
   to a requirement. Mapping prevents the trap of implementing for the
   sake of implementing.
2. **For an auditor.** Reviewing whether a framework is satisfied means
   reading what the system actually does. The mapping saves the effort of
   reverse-engineering the code and configuration.
3. **For a reviewer of the portfolio.** It shows the work is grounded in
   standards, not improvised.

### 1.1 Status vocabulary

| Marker            | Meaning                                              |
|-------------------|------------------------------------------------------|
| `[implemented]`   | The control exists in the current system.            |
| `[planned: N]`    | Scheduled for Phase N of the roadmap.                |
| `[partial]`       | Partially implemented; the gap is noted.             |
| `[accepted]`      | Recognised, not applied, with rationale.             |
| `[n/a]`           | Not applicable, with rationale.                      |

---

## 2. OWASP Top 10 — 2021

The OWASP Top 10 is the most widely referenced web application security
framework. It defines ten categories of the most critical risks.

### A01:2021 — Broken Access Control

**Risk.** Users acting outside their intended permissions. Includes IDOR,
privilege escalation, and missing authorization checks.

**Status.** `[implemented]`

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| Endpoint-level authorization dependency (RBAC)          | `[implemented]` — `require_admin` in `backend/app/dependencies.py` |
| Row-level ownership verification (IDOR protection)      | `[implemented]` — asset queries filter on `owner_id`; tests in `backend/tests/test_asset_authorization.py` |
| Field-level response schemas                            | `[implemented]` — Pydantic schemas separate from ORM models |
| Deny-by-default in API access                           | `[implemented]` — `backend/tests/test_routes_policy.py` fails if a route outside the public list does not require authentication |
| Deliberate IDOR vulnerability introduced and fixed      | `[implemented]` — see `docs/vuln-exercise-idor.md` (2026-10-10, status Fixed) |

**Update 2026-10-23.** This section previously stated that the API had
no authentication and that RBAC, ownership checks and deny-by-default
were planned for Phase 4. They are implemented and covered by tests in
`backend/tests/`; the statuses above were checked against the code on
this date. The test results were not re-run for this update.

**Reference.** Threat model §7.3 (three levels of authorization);
risk register R-02.

### A02:2021 — Cryptographic Failures

**Risk.** Failures related to cryptography, including weak algorithms,
poor key management, and unprotected data in transit or at rest.

**Status.** `[implemented]`

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| TLS 1.2/1.3 for all client traffic                      | `[implemented]` |
| HTTP redirected to HTTPS                                | `[implemented]` |
| Internal PKI for certificate issuance                   | `[implemented]` |
| Modern cipher suites only (no TLS 1.0/1.1)              | `[implemented]` |
| Key separation (CA key vs server key)                   | `[implemented]` |
| CA private key encrypted at rest                        | `[planned: phase 10]` — risk R-03 |
| SSH key passphrase                                      | `[implemented]` |
| Argon2id password hashing for user accounts             | `[planned: phase 4]` |

**Reference.** Threat model §7.7 (PKI); risk register R-03.

### A03:2021 — Injection

**Risk.** User-supplied data interpreted as code or commands. Includes SQL
injection, command injection, and template injection.

**Status.** `[implemented]`

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| Parameterized queries via SQLAlchemy ORM                | `[implemented]` |
| Input validation via Pydantic schemas                   | `[implemented]` |
| No raw SQL string concatenation                         | `[implemented]` |
| Deliberate SQL injection introduced and fixed           | `[planned: phase 7]` |

**Reference.** Threat model §7.2 T3; risk register R-05 for context.

### A04:2021 — Insecure Design

**Risk.** Missing or ineffective control design. Threat modelling,
secure design patterns, and reference architectures fall here.

**Status.** `[implemented]`

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| Threat model (STRIDE) per component                     | `[implemented]` |
| Risk register with treatment and residual risk          | `[implemented]` |
| Trust boundaries explicitly documented                  | `[implemented]` |
| Data classification with lifecycle                      | `[implemented]` |
| Incident response playbook                              | `[implemented]` |
| Password policy                                         | `[implemented]` |

**Reference.** All documents in `docs/`.

### A05:2021 — Security Misconfiguration

**Risk.** Default credentials, verbose errors, unnecessary features
enabled, missing hardening.

**Status.** `[implemented]` with accepted exceptions

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| SSH key-only, no password                               | `[implemented]` |
| Root login disabled                                     | `[implemented]` |
| User allowlist on SSH                                   | `[implemented]` |
| UFW deny-by-default                                     | `[implemented]` |
| FastAPI bound to loopback                               | `[implemented]` |
| Nginx security headers (HSTS, CSP, X-Frame-Options, etc.) | `[implemented]` |
| Debug mode disabled in production                       | `[implemented]` |
| Server version disclosed in `Server` header             | `[accepted]` — AR-01 in the risk register |
| No `Host` header validation                             | `[accepted]` — AR-02 |
| Auditd not configured                                   | `[planned: phase 8]` |

### A06:2021 — Vulnerable and Outdated Components

**Risk.** Using libraries, frameworks, or services with known
vulnerabilities.

**Status.** `[partial]` — npm audit and SBOM generation are not implemented.

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| SCA scan of Python dependencies (pip-audit)             | `[implemented]` — job "Security (bandit, pip-audit)" in `.github/workflows/ci.yml` |
| SCA scan of Node dependencies (npm audit)               | `[planned: phase 6]` — not implemented: no `npm audit` in `.github/workflows/ci.yml` or `frontend/package.json` (checked 2026-10-23) |
| Dependabot enabled                                      | `[implemented]` — update pull requests merged (see `docs/JOURNAL.md`, Session 25); no `.github/dependabot.yml` is committed, so the configuration is not versioned |
| Pinned dependency versions                              | `[implemented]` — lockfiles committed |
| SBOM generation (CycloneDX via Syft)                    | `[planned: phase 11]` |

**Update 2026-10-23.** The pip-audit and Dependabot rows were
previously `[planned]` (phase 6 and phase 12). They were checked
against the CI workflow and the repository history on this date; the
CI run results were not re-checked. The npm audit and SBOM rows are
unchanged and confirmed as not implemented.

### A07:2021 — Identification and Authentication Failures

**Risk.** Weak authentication, credential stuffing, session management
failures.

**Status.** `[partial]` — GitHub account MFA is still planned.

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| Password policy with NIST-aligned rotation              | `[implemented]` — policy written |
| Password manager with MFA                               | `[implemented]` — operator posture |
| SSH key authentication instead of password              | `[implemented]` |
| Argon2id hashing for application users                  | `[implemented]` — `PasswordHasher` in `backend/app/security.py` |
| JWT with strong key and fixed algorithm                 | `[implemented]` — HS256 fixed on encode and decode; 64-byte random secret |
| Rate limiting on authentication endpoints               | `[implemented]` — in Nginx, not in the application: login zone at 5 requests per minute (`deploy/nginx/secure-fullstack`, same values active on the VM on 2026-10-23) |
| MFA on GitHub account                                   | `[planned: phase 12]` |

**Update 2026-10-23.** The Argon2id, JWT and rate-limiting rows were
previously `[planned: phase 4]`. They were checked against the code and
the active Nginx configuration on this date.

**Reference.** `docs/password-policy.md`.

### A08:2021 — Software and Data Integrity Failures

**Risk.** Code and infrastructure that do not protect against integrity
violations. Includes insecure CI/CD, unsigned updates, and insecure
deserialization.

**Status.** `[planned: phase 6 and phase 12]`

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| CI pipeline with integrity checks                       | `[planned: phase 6]` |
| Signed commits (GPG or SSH)                             | `[planned: phase 12]` |
| Branch protection on `main`                             | `[planned: phase 12]` |
| Signed container images (cosign)                        | `[planned: phase 11]` |
| GitHub email notifications on push                      | `[implemented]` |

### A09:2021 — Security Logging and Monitoring Failures

**Risk.** Insufficient logging, monitoring, and alerting. Incidents go
undetected.

**Status.** `[planned: phase 8]`

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| Structured JSON logging in the API                      | `[planned: phase 8]` |
| Auditd on the host                                      | `[planned: phase 8]` |
| GoAccess for Nginx access log analysis                  | `[planned: phase 8]` |
| Correlation script for repeated auth failures           | `[planned: phase 8]` |
| Fail2Ban active with custom filter                      | `[implemented]` |
| GitHub push notifications                               | `[implemented]` |

### A10:2021 — Server-Side Request Forgery (SSRF)

**Risk.** The server fetches a resource based on a user-supplied URL,
allowing access to internal resources.

**Status.** `[n/a]` — no SSRF surface exists

| Control                                                 | Status |
|---------------------------------------------------------|--------|
| No endpoint accepts a URL from the client               | `[implemented]` |
| Code review for SSRF introduced by future features      | `[planned: phase 4]` |

**Rationale.** The current API has no endpoint that fetches a
user-supplied URL. The risk is noted for future phases — any endpoint
that adds such a capability must be reviewed against this category.

---

## 3. OWASP ASVS — key chapters

The Application Security Verification Standard (ASVS) is more granular
than the Top 10. This section covers the chapters most relevant to the
project.

| ASVS Chapter | Title                          | Status        | Notes |
|--------------|--------------------------------|---------------|-------|
| V1           | Architecture, Design, Threat Modelling | `[implemented]` | Threat model in `docs/threat-model.md` |
| V2           | Authentication                 | `[planned: phase 4]` | |
| V3           | Session Management             | `[planned: phase 4]` | JWT with short-lived access tokens |
| V4           | Access Control                 | `[planned: phase 4]` | RBAC + IDOR tests |
| V5           | Validation, Sanitization, Encoding | `[implemented]` | Pydantic on input, JSON on output |
| V6           | Stored Cryptography            | `[partial]`   | TLS in place; CA key encryption planned |
| V7           | Error Handling and Logging     | `[planned: phase 8]` | |
| V8           | Data Protection                | `[implemented]` | Classification in threat model §3 |
| V9           | Communication Security         | `[implemented]` | TLS 1.2/1.3 only |
| V10          | Malicious Code                  | `[planned: phase 11]` | Image signing, SBOM |
| V11          | Business Logic                 | `[partial]`   | Validation present; rate limiting missing |
| V12          | Files and Resources            | `[n/a]`       | No file upload or resource endpoints |
| V13          | API and Web Service            | `[partial]`   | REST surface; auth pending |
| V14          | Configuration                  | `[implemented]` | Hardening in `deploy/hardening/` |

**Level target.** The project targets **ASVS Level 2** (standard for
applications handling sensitive data). Level 1 controls are largely
implemented; Level 2 controls are distributed across Phases 4 to 8.

---

## 4. ISO/IEC 27001:2022 — Annex A

The status of each Annex A control is recorded in the Statement of
Applicability, `docs/statement-of-applicability-v2.md`. That document is
the single source of truth for control status. This mapping does not
repeat it, so the two cannot diverge.

`backend/tests/test_soa_consistency.py` checks the Statement of
Applicability for identifiers, states and totals. It does not check
whether each justification is true.

An earlier version of this section listed 53 controls with their own
status. It was removed because it had diverged from the Statement of
Applicability. It remains in the git history.

---

## 5. NIS2 — Article 21(2)

The EU NIS2 Directive (2022/2555) requires essential and important
entities to implement ten categories of cybersecurity risk-management
measures (Article 21(2)). Although a personal lab is not in scope, the
categories provide a useful checklist.

| Ref  | Category                                                        | Status        |
|------|-----------------------------------------------------------------|---------------|
| (a)  | Risk analysis and information system security policies          | `[implemented]` — threat model, risk register, policies |
| (b)  | Incident handling                                               | `[implemented]` — incident response playbook |
| (c)  | Business continuity and crisis management                       | `[planned: phase 10]` — backup and restore |
| (d)  | Supply chain security                                           | `[partial]` — GitHub analysis in threat model; SCA planned |
| (e)  | Security in acquisition, development and maintenance            | `[partial]` — this project demonstrates the practice |
| (f)  | Policies to assess effectiveness of measures                    | `[partial]` — risk register tracked; audits not yet performed |
| (g)  | Basic cyber hygiene and cybersecurity training                  | `[implemented]` — operator certifications; documented practices |
| (h)  | Cryptography and encryption policies                            | `[implemented]` — TLS, PKI, password policy |
| (i)  | Human resources security, access control policies, asset management | `[implemented]` — password policy, threat model asset inventory |
| (j)  | MFA, secured communications                                     | `[partial]` — SSH keys, password manager MFA; application MFA pending |

**Portugal — CNPD and CNCS.** Portugal has designated the **CNCS**
(National Cybersecurity Centre) as the competent authority for NIS2. In
the event of a significant incident, the entity must notify CNCS within
24 hours (early warning) and 72 hours (formal notification). This is
referenced for awareness only — the lab is not in scope of NIS2.

---

## 6. Consolidated view

> **Historical snapshot (2026-10-05), not yet re-verified.** The OWASP and
> NIS2 states below have not been checked against the current code. The
> ISO column was removed: see the Statement of Applicability v2.

A single table combining the frameworks per area of the project.

| Area             | OWASP Top 10        | NIS2 |
|------------------|---------------------|-------------|
| Authentication   | A07 `[planned: 4]`  | (i) `[implemented]`, (j) `[partial]` |
| Authorization    | A01 `[planned: 4]`  | (i) |
| Transport        | A02 `[implemented]` | (h) |
| Injection        | A03 `[implemented]` | (e) `[partial]` |
| Design           | A04 `[implemented]` | (a) |
| Configuration    | A05 `[implemented]` | (g) |
| Components       | A06 `[planned: 6]`  | (d) `[partial]` |
| Integrity        | A08 `[planned: 12]` | (d) `[partial]` |
| Logging          | A09 `[planned: 8]`  | (b) `[implemented]` |
| SSRF             | A10 `[n/a]`         | — |
| Incident response | —                   | (b) |
| Backup           | —                   | (c) `[planned]` |

---

## 7. Gaps and next actions

> **Historical snapshot (2026-10-05), not yet re-verified.** Some of the
> gaps below may already be closed. Do not read this list as the current
> state.

The mapping surfaces gaps that are already planned in the roadmap. They
are listed here as the interface between this document and the phases
that follow.

| Gap                                     | Framework reference         | Phase |
|-----------------------------------------|-----------------------------|-------|
| No authentication or authorization      | OWASP A01, A07; ISO A.5.18, A.8.2 | 4 |
| No rate limiting on the API             | OWASP A07; risk R-05        | 4     |
| No SCA scans in a pipeline              | OWASP A06                   | 6     |
| No structured logging                   | OWASP A09; ISO A.8.15, A.8.16 | 8   |
| No auditd                               | OWASP A09; ISO A.8.16       | 8     |
| No backup or restore test               | ISO A.8.13; NIS2 (c)        | 10    |
| CA key stored unencrypted on the host   | ISO A.8.24; risk R-03       | 10    |
| No 2FA or signed commits on GitHub      | OWASP A08; risk R-04        | 12    |
| No account separation (admin vs daily)  | ISO A.8.2; risk R-02        | 9     |

**Every gap has a phase.** None is unplanned. This is the point of the
mapping — to make the roadmap traceable to a requirement.

---

## 8. References

- **OWASP Top 10 — 2021** — https://owasp.org/Top10/
- **OWASP ASVS 4.0.3** — https://owasp.org/www-project-application-security-verification-standard/
- **ISO/IEC 27001:2022** — Information security, cybersecurity and privacy protection — Information security management systems — Requirements
- **NIS2 Directive (EU) 2022/2555** — Article 21(2)
- **CIS Controls v8** — for cross-reference, not mapped in this version

---

## 9. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-05 | 1.0     | Initial mapping. All three frameworks covered. | Filipe Castanheira |
| 2026-10-22 | 1.1     | ISO Annex A section replaced by a pointer to the SoA v2; ISO column removed from the consolidated view; sections 6 and 7 marked as unverified snapshots. | Filipe Castanheira |
