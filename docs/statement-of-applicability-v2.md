# Statement of Applicability (SoA)

**Standard:** ISO/IEC 27001:2022, Annex A
**Version:** 2.0 (Canonical format)
**Date:** 2026-10-19
**Owner:** Filipe Castanheira

## 1. Purpose
This document records the applicability of all 93 controls from ISO/IEC 27001:2022 Annex A for the Secure Fullstack Lab. For each control, it states whether it is applicable, its current implementation status, and the justification.

**Scope:** the application, its virtual machines and their configuration. The physical host and the surrounding network are outside the scope and intentionally not documented.

## 2. Methodology
The lab simulates a production environment. Controls are deemed **applicable** unless the specific asset, role, or activity they protect does not exist in this architecture.
- **Status:** `Implemented` (I), `Partial` (P), `Planned` (Pl), `Not Applicable` (NA).
- `Planned` means applicable but not yet implemented, either not started or lacking resources.
- Every `NA` justification starts with `Not applicable:`; every `Planned` justification starts with `Applicable, not implemented:` or `Applicable, no resources:`.

## 3. Control Assessment (A.5 to A.8)

| ID | Control Name | Status | Justification / Implementation Details |
|---|---|---|---|
| **A.5 Organizational controls** | | | |
| A.5.1 | Policies for information security | P | Specific policies exist (`docs/password-policy.md`, `docs/vulnerability-management-policy.md`, `docs/incident-response.md`); no overarching information security policy. |
| A.5.2 | Information security roles and responsibilities | P | Owner defined in this document; application roles (admin, user) enforced by RBAC. No formal RACI. |
| A.5.3 | Segregation of duties | NA | Not applicable: single operator. Absence of review approvals on `main` is a documented accepted risk (AR-06). |
| A.5.4 | Management responsibilities | NA | Not applicable: no personnel to manage. |
| A.5.5 | Contact with authorities | NA | Not applicable: not exposed to the Internet and no real data; CNPD is identified in the threat model for a real deployment. |
| A.5.6 | Contact with special interest groups | NA | Not applicable: no membership of special interest groups; vulnerability sources are tracked under A.5.7. |
| A.5.7 | Threat intelligence | P | Vulnerability intelligence via Dependabot, pip-audit in CI and GitHub Security Advisories (see `docs/vulnerability-management-policy.md`); no dedicated threat intelligence feed. |
| A.5.8 | Information security in project management | I | Threat modeling applied (STRIDE) in `docs/threat-model.md`. |
| A.5.9 | Inventory of information and other associated assets | I | Asset inventory maintained in the DB and threat model. |
| A.5.10 | Acceptable use of information and other associated assets | Pl | Applicable, not implemented: implicit in lab scope, not formally documented. |
| A.5.11 | Return of assets | NA | Not applicable: no employees or contractors. |
| A.5.12 | Classification of information | I | Data classification defined in threat model §3. |
| A.5.13 | Labelling of information | P | Assets are classified in the threat model (section 3.2); no labelling is applied to the data itself. |
| A.5.14 | Information transfer | I | TLS enforced (Nginx/Internal CA). |
| A.5.15 | Access control | I | JWT auth + RBAC implemented. |
| A.5.16 | Identity management | I | User model + Argon2id hashing. |
| A.5.17 | Authentication information | I | Password policy (`docs/password-policy.md`) + JWT. |
| A.5.18 | Access rights | I | RBAC (user/admin) in `dependencies.py`. |
| A.5.19 | Information security in supplier relationships | Pl | Applicable, not implemented: GitHub (code, CI, Dependabot), PyPI, npm and Ubuntu repositories are suppliers; there is no supplier register or review. |
| A.5.20 | Addressing information security within supplier agreements | NA | Not applicable: suppliers use standard terms that cannot be negotiated. |
| A.5.21 | Managing information security in the ICT supply chain | I | SBOM generated (Syft) and signed (cosign). |
| A.5.22 | Monitoring, review and change management of supplier services | Pl | Applicable, not implemented: no periodic review of supplier services; Dependabot alerts are the only monitoring. |
| A.5.23 | Information security for use of cloud services | P | Runtime is on local VMs; source hosting and CI run on GitHub (cloud). Use of GitHub is not formally assessed. |
| A.5.24 | Information security incident management planning and preparation | I | Incident response playbooks (`docs/incident-response.md`). |
| A.5.25 | Assessment and decision on information security events | P | Simulated exercise performed (`docs/simulated-incident-exercise.md`). |
| A.5.26 | Response to information security incidents | I | Playbooks IR-1 to IR-5. |
| A.5.27 | Learning from information security incidents | I | Post-mortem template included in IR playbook. |
| A.5.28 | Collection of evidence | P | Logs collected, but no formal chain of custody. |
| A.5.29 | Information security during disruption | P | Backups automated, RTO/RPO measured. |
| A.5.30 | ICT readiness for business continuity | P | Backup restore tested (`deploy/backup/README.md`). |
| A.5.31 | Legal, statutory, regulatory and contractual requirements | P | GDPR and CNPD identified in the threat model (section 3.4); MIT licence applied. No formal register of legal requirements. |
| A.5.32 | Intellectual property rights | P | Project released under MIT (`LICENSE`); open-source dependencies. No automated check of dependency licences. |
| A.5.33 | Protection of records | P | Logs structured (JSON), but no WORM storage. |
| A.5.34 | Privacy and protection of PII | P | Synthetic test accounts only (reserved example domain); client IPs appear in web server logs. Protected by argon2id hashing, access control and TLS. No documented privacy notice, retention policy or erasure procedure. |
| A.5.35 | Independent review of information security | Pl | Applicable, no resources: single operator, no independent reviewer. Informal reviews are not recorded as audit evidence. |
| A.5.36 | Compliance with policies, rules and standards | I | CI pipeline enforces rules (lint, tests, SAST). |
| A.5.37 | Documented operating procedures | I | Deployment docs in `deploy/`. |
| **A.6 People controls** | | | |
| A.6.1 | Screening | NA | Not applicable: no employees. |
| A.6.2 | Terms and conditions of employment | NA | Not applicable: no employees. |
| A.6.3 | Information security awareness, education and training | P | The operator's own certifications and training; no staff to train and no formal awareness programme. |
| A.6.4 | Disciplinary process | NA | Not applicable: no employees. |
| A.6.5 | Responsibilities after termination or change of employment | NA | Not applicable: no employees. |
| A.6.6 | Confidentiality or non-disclosure agreements | NA | Not applicable: no employees. |
| A.6.7 | Remote working | NA | Not applicable: no employees. |
| A.6.8 | Information security event reporting | I | Logged via FastAPI middleware and auditd. |
| **A.7 Physical controls** | | | |
| A.7.1 | Physical security perimeters | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.2 | Physical entry controls | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.3 | Securing offices, rooms and facilities | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.4 | Physical security monitoring | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.5 | Protecting against physical and environmental threats | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.6 | Working in secure areas | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.7 | Clear desk and clear screen policy | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.8 | Equipment siting and protection | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.9 | Security of assets off-premises | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.10 | Storage media | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.11 | Supporting utilities | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.12 | Cabling security | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.13 | Equipment maintenance | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| A.7.14 | Secure disposal or re-use of equipment | NA | Not applicable: physical host and premises are outside the declared scope (see section 1). |
| **A.8 Technological controls** | | | |
| A.8.1 | User endpoint devices | NA | Not applicable: no managed endpoint devices in scope. |
| A.8.2 | Privileged access rights | I | `sudo` restricted; app runs as `secure-app` without shell/sudo. |
| A.8.3 | Information access restriction | I | RBAC + JWT authentication. |
| A.8.4 | Access to source code | I | GitHub repository (private). |
| A.8.5 | Secure authentication | I | Argon2id hashing; JWT with type separation. |
| A.8.6 | Capacity management | Pl | Applicable, not implemented: no capacity monitoring or alerting. |
| A.8.7 | Protection against malware | P | Container isolation; no host AV (VM only). |
| A.8.8 | Management of technical vulnerabilities | I | Trivy, pip-audit, Dependabot (`docs/vulnerability-management-policy.md`). |
| A.8.9 | Configuration management | I | Ansible playbooks (`deploy/ansible/`). |
| A.8.10 | Information deletion | P | Backups older than 7 days are deleted by the backup script; no procedure for erasing an individual user's data on request. |
| A.8.11 | Data masking | NA | Not applicable: data is synthetic; there is no production data to mask. |
| A.8.12 | Data leakage prevention | P | No DLP tool; relies on network isolation (UFW). |
| A.8.13 | Information backup | I | Automated backup + tested restore (`deploy/backup/`). |
| A.8.14 | Redundancy of information processing facilities | Pl | Applicable, not implemented: single VM; recovery relies on backups (see A.5.30). |
| A.8.15 | Logging | I | Structured JSON logs, auditd, GoAccess. |
| A.8.16 | Monitoring activities | I | Correlation script, rate limit alerts (`deploy/monitoring/`). |
| A.8.17 | Clock synchronisation | I | systemd-timesyncd (default Ubuntu). |
| A.8.18 | Use of privileged utility programs | P | No specific restrictions beyond UFW/sudo. |
| A.8.19 | Installation of software on operational systems | I | Only via Ansible/apt; container builds pinned. |
| A.8.20 | Networks security | I | UFW (deny incoming), internal CA TLS. |
| A.8.21 | Security of network services | I | Nginx reverse proxy, TLS 1.2/1.3. |
| A.8.22 | Segregation of networks | P | Isolated VMware segments, not physical. |
| A.8.23 | Web filtering | NA | Not applicable: backend lab with no end-user web browsing. |
| A.8.24 | Use of cryptography | I | TLS (internal CA), Argon2id, GPG (commits), cosign (SBOM). |
| A.8.25 | Secure development life cycle | I | CI/CD pipeline, threat model, vuln exercises. |
| A.8.26 | Application security requirements | I | OWASP ASVS mapping (`docs/control-mapping.md`). |
| A.8.27 | Secure system architecture and engineering principles | I | Threat model (STRIDE), least privilege, defense in depth. |
| A.8.28 | Secure coding | I | Bandit SAST, ruff lint, pytest suite. |
| A.8.29 | Security testing in development and acceptance | I | ZAP DAST, IDOR/SQLi/CORS exercises. |
| A.8.30 | Outsourced development | NA | Not applicable: no outsourced development. |
| A.8.31 | Separation of development, test and production environments | P | Single lab VM; no formal separation. |
| A.8.32 | Change management | I | Git commit history + signed commits. |
| A.8.33 | Test information | NA | Not applicable: test data is synthetic; no production data is used. |
| A.8.34 | Protection of information systems during audit testing | NA | Not applicable: no formal audit testing is performed against the system. |

## 4. Summary of Applicability

- **Total controls:** 93
- **Applicable:** 61
- **Not Applicable:** 32
- **Implemented / Partial:** 55
- **Planned:** 6 (A.5.10, A.5.19, A.5.22, A.5.35, A.8.6, A.8.14)

The Not Applicable controls (32) result from the lab being a single-operator environment without employees, and from the physical host and network being outside the declared scope (section 1). Each exclusion is justified in the table above, as required by ISO/IEC 27001:2022 clause 6.1.3(d).
