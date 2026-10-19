# Statement of Applicability (SoA)

**Standard:** ISO/IEC 27001:2022, Annex A
**Version:** 2.0 (Canonical format)
**Date:** 2026-10-19
**Owner:** Filipe Castanheira

## 1. Purpose
This document records the applicability of all 93 controls from ISO/IEC 27001:2022 Annex A for the Secure Fullstack Lab. For each control, it states whether it is applicable, its current implementation status, and the justification.

## 2. Methodology
The lab simulates a production environment. Controls are deemed **applicable** unless the specific asset, role, or activity they protect does not exist in this architecture.
- **Status:** `Implemented` (I), `Partial` (P), `Planned` (Pl), `Not Applicable` (NA).

## 3. Control Assessment (A.5 to A.8)

| ID | Control Name | Status | Justification / Implementation Details |
|---|---|---|---|
| **A.5 Organizational controls** | | | |
| A.5.1 | Policies for information security | Pl | Documented via `docs/password-policy.md` and `docs/vulnerability-management-policy.md`. |
| A.5.2 | Information security roles and responsibilities | NA | Single-operator lab. No separation of duties. |
| A.5.3 | Segregation of duties | NA | Single-operator lab. |
| A.5.4 | Management responsibilities | NA | No personnel management. |
| A.5.5 | Contact with authorities | NA | Lab is not exposed to the Internet. |
| A.5.6 | Contact with special interest groups | NA | Not applicable to lab. |
| A.5.7 | Threat intelligence | NA | No formal threat intel feed. |
| A.5.8 | Information security in project management | I | Threat modeling applied (STRIDE) in `docs/threat-model.md`. |
| A.5.9 | Inventory of information and other associated assets | I | Asset inventory maintained in the DB and threat model. |
| A.5.10 | Acceptable use of information and other associated assets | Pl | Implicit in lab scope, not formally documented. |
| A.5.11 | Return of assets | NA | No employees. |
| A.5.12 | Classification of information | I | Data classification defined in threat model §3. |
| A.5.13 | Labelling of information | NA | No formal labelling system required. |
| A.5.14 | Information transfer | I | TLS enforced (Nginx/Internal CA). |
| A.5.15 | Access control | I | JWT auth + RBAC implemented. |
| A.5.16 | Identity management | I | User model + Argon2id hashing. |
| A.5.17 | Authentication information | I | Password policy (`docs/password-policy.md`) + JWT. |
| A.5.18 | Access rights | I | RBAC (user/admin) in `dependencies.py`. |
| A.5.19 | Information security in supplier relationships | NA | No external suppliers. |
| A.5.20 | Addressing information security within supplier agreements | NA | No external suppliers. |
| A.5.21 | Managing information security in the ICT supply chain | I | SBOM generated (Syft) and signed (cosign). |
| A.5.22 | Monitoring, review and change management of supplier services | NA | No external suppliers. |
| A.5.23 | Information security for use of cloud services | NA | Lab runs on-premises (VMware). |
| A.5.24 | Information security incident management planning and preparation | I | Incident response playbooks (`docs/incident-response.md`). |
| A.5.25 | Assessment and decision on information security events | P | Simulated exercise performed (`docs/simulated-incident-exercise.md`). |
| A.5.26 | Response to information security incidents | I | Playbooks IR-1 to IR-5. |
| A.5.27 | Learning from information security incidents | I | Post-mortem template included in IR playbook. |
| A.5.28 | Collection of evidence | P | Logs collected, but no formal chain of custody. |
| A.5.29 | Information security during disruption | P | Backups automated, RTO/RPO measured. |
| A.5.30 | ICT readiness for business continuity | P | Backup restore tested (`deploy/backup/README.md`). |
| A.5.31 | Legal, statutory, regulatory and contractual requirements | NA | Lab environment. |
| A.5.32 | Intellectual property rights | NA | Open source stack (MIT). |
| A.5.33 | Protection of records | P | Logs structured (JSON), but no WORM storage. |
| A.5.34 | Privacy and protection of PII | NA | No PII processed. |
| A.5.35 | Independent review of information security | NA | Single-operator lab. |
| A.5.36 | Compliance with policies, rules and standards | I | CI pipeline enforces rules (lint, tests, SAST). |
| A.5.37 | Documented operating procedures | I | Deployment docs in `deploy/`. |
| **A.6 People controls** | | | |
| A.6.1 | Screening | NA | No employees. |
| A.6.2 | Terms and conditions of employment | NA | No employees. |
| A.6.3 | Information security awareness, education and training | NA | Single-operator lab. |
| A.6.4 | Disciplinary process | NA | No employees. |
| A.6.5 | Responsibilities after termination or change of employment | NA | No employees. |
| A.6.6 | Confidentiality or non-disclosure agreements | NA | No employees. |
| A.6.7 | Remote working | NA | No employees. |
| A.6.8 | Information security event reporting | I | Logged via FastAPI middleware and auditd. |
| **A.7 Physical controls** | | | |
| A.7.1 | Physical security perimeters | NA | VMware virtual environment. |
| A.7.2 | Physical entry controls | NA | VMware virtual environment. |
| A.7.3 | Securing offices, rooms and facilities | NA | VMware virtual environment. |
| A.7.4 | Physical security monitoring | NA | VMware virtual environment. |
| A.7.5 | Protecting against physical and environmental threats | NA | VMware virtual environment. |
| A.7.6 | Working in secure areas | NA | VMware virtual environment. |
| A.7.7 | Clear desk and clear screen policy | NA | VMware virtual environment. |
| A.7.8 | Equipment siting and protection | NA | VMware virtual environment. |
| A.7.9 | Security of assets off-premises | NA | VMware virtual environment. |
| A.7.10 | Storage media | NA | VMware virtual environment. |
| A.7.11 | Supporting utilities | NA | VMware virtual environment. |
| A.7.12 | Cabling security | NA | VMware virtual environment. |
| A.7.13 | Equipment maintenance | NA | VMware virtual environment. |
| A.7.14 | Secure disposal or re-use of equipment | NA | VMware virtual environment. |
| A.7.15 | Clear desk and clear screen policy | NA | VMware virtual environment. |
| **A.8 Technological controls** | | | |
| A.8.1 | User endpoint devices | NA | No managed endpoint devices. |
| A.8.2 | Privileged access rights | I | `sudo` restricted; app runs as `secure-app` without shell/sudo. |
| A.8.3 | Information access restriction | I | RBAC + JWT authentication. |
| A.8.4 | Access to source code | I | GitHub repository (private). |
| A.8.5 | Secure authentication | I | Argon2id hashing; JWT with type separation. |
| A.8.6 | Capacity management | NA | Lab is not 24/7; resource usage is minimal. |
| A.8.7 | Protection against malware | P | Container isolation; no host AV (VM only). |
| A.8.8 | Management of technical vulnerabilities | I | Trivy, pip-audit, Dependabot (`docs/vulnerability-management-policy.md`). |
| A.8.9 | Configuration management | I | Ansible playbooks (`deploy/ansible/`). |
| A.8.10 | Information deletion | NA | Lab is destroyed at the end. |
| A.8.11 | Data masking | NA | No PII. |
| A.8.12 | Data leakage prevention | P | No DLP tool; relies on network isolation (UFW). |
| A.8.13 | Information backup | I | Automated backup + tested restore (`deploy/backup/`). |
| A.8.14 | Redundancy of information processing facilities | NA | Single VM lab. |
| A.8.15 | Logging | I | Structured JSON logs, auditd, GoAccess. |
| A.8.16 | Monitoring activities | I | Correlation script, rate limit alerts (`deploy/monitoring/`). |
| A.8.17 | Clock synchronisation | I | systemd-timesyncd (default Ubuntu). |
| A.8.18 | Use of privileged utility programs | P | No specific restrictions beyond UFW/sudo. |
| A.8.19 | Installation of software on operational systems | I | Only via Ansible/apt; container builds pinned. |
| A.8.20 | Networks security | I | UFW (deny incoming), internal CA TLS. |
| A.8.21 | Security of network services | I | Nginx reverse proxy, TLS 1.2/1.3. |
| A.8.22 | Segregation of networks | P | Isolated VMware segments, not physical. |
| A.8.23 | Web filtering | NA | Not applicable to backend lab. |
| A.8.24 | Use of cryptography | I | TLS (internal CA), Argon2id, GPG (commits), cosign (SBOM). |
| A.8.25 | Secure development life cycle | I | CI/CD pipeline, threat model, vuln exercises. |
| A.8.26 | Application security requirements | I | OWASP ASVS mapping (`docs/control-mapping.md`). |
| A.8.27 | Secure system architecture and engineering principles | I | Threat model (STRIDE), least privilege, defense in depth. |
| A.8.28 | Secure coding | I | Bandit SAST, ruff lint, pytest suite. |
| A.8.29 | Security testing in development and acceptance | I | ZAP DAST, IDOR/SQLi/CORS exercises. |
| A.8.30 | Outsourced development | NA | No outsourced development. |
| A.8.31 | Separation of development, test and production environments | P | Single lab VM; no formal separation. |
| A.8.32 | Change management | I | Git commit history + signed commits. |
| A.8.33 | Test information | NA | No production data used. |
| A.8.34 | Protection of information systems during audit testing | NA | No external audits. |

## 4. Summary of Applicability

- **Total controls:** 93
- **Applicable:** 53
- **Not Applicable:** 40
- **Implemented / Partial:** 53
- **Planned:** 4 (A.5.1, A.5.10, A.5.30, A.8.12)

The high number of Not Applicable controls (40) is a direct result of the lab being a single-operator environment without employees, physical premises, or external suppliers. All exclusions are justified in the table above, in line with ISO/IEC 27001:2013 clause 6.1.3(d) requirements.
