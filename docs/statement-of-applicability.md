# Statement of Applicability — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.0
**Effective date:** 2026-10-08
**Framework:** ISO/IEC 27001:2022, Annex A
**Related documents:**
- `docs/control-mapping.md` — detailed status of all 93 controls
- `docs/threat-model.md` — risk context for applicability decisions
- `docs/risk-register.md` — treatment decisions

---

## 1. Purpose

The Statement of Applicability (SoA) documents, for every control in
ISO/IEC 27001:2022 Annex A:

- Whether the control is **applicable** to this environment
- Whether it is **implemented**, partial, or planned
- The **justification** for the applicability decision

The SoA is a mandatory artefact under ISO/IEC 27001:2022 clause 6.1.3(d).
It is the bridge between the risk assessment and the controls the
organisation has chosen to apply.

## 2. Scope of this SoA

This SoA covers the Secure Fullstack Lab:

- A single-operator environment
- Running on isolated virtual networks
- Consisting of one Ubuntu host running an application (Vue + FastAPI +
  SQLite), served through Nginx with an internal CA
- Not exposed to the Internet, not a production service

The scope is intentionally narrow. Controls that are meaningful only in a
multi-person, multi-site, or regulated-data environment are marked as not
applicable, with the rationale recorded.

## 3. Method

For each control, applicability was determined by asking:

1. **Is the asset or activity the control addresses present in this
   environment?** — if not, the control is not applicable.
2. **If the asset is present, does the risk assessment require the
   control?** — if the risk does not justify it, the control is accepted
   as a residual risk (recorded in `docs/risk-register.md` §4).
3. **If applicable, is the control implemented, partial, or planned?**

Each decision is recorded in `docs/control-mapping.md` §4 (for the
technological controls) and in the tables below (for the summary).

**Decision criteria for "not applicable":**

- **Role not present.** Example: A.6.1 (screening) — there is no
  employment relationship to screen.
- **Scale not present.** Example: A.8.31 (separation of development,
  test, and production environments) — there is a single environment.
- **Activity not performed.** Example: A.5.19 (supplier relationships) —
  no suppliers beyond GitHub, which is covered separately by A.5.23.

A "not applicable" decision is not a gap. It is a justified exclusion,
and it must be recorded.

## 4. Summary by theme

The 2022 revision of Annex A organises 93 controls into four themes:

| Theme                     | Code range | Total | Applicable | Not applicable |
|---------------------------|------------|-------|------------|----------------|
| Organizational controls   | A.5.x      | 37    | 20         | 17             |
| People controls           | A.6.x      | 8     | 3          | 5              |
| Physical controls         | A.7.x      | 14    | 3          | 11             |
| Technological controls    | A.8.x      | 34    | 30         | 4              |
| **Total**                 |            | **93**| **56**     | **37**         |

**Approximately 60% of Annex A is applicable** to this environment. The
remainder are excluded because the asset, role, or activity they address
does not exist in a single-operator lab — not because they were judged
inconvenient.

## 5. Applicable controls — status

The detailed status of every applicable control is in
`docs/control-mapping.md` §4. The summary below shows the aggregate
position at the effective date.

### 5.1 Organizational controls (A.5.x — applicable subset)

| Control | Title                                              | Status        |
|---------|----------------------------------------------------|---------------|
| A.5.1   | Policies for information security                  | Implemented   |
| A.5.7   | Threat intelligence                                | Implemented   |
| A.5.9   | Inventory of information and other associated assets | Implemented |
| A.5.14  | Information transfer                               | Implemented   |
| A.5.15  | Access control                                     | Implemented   |
| A.5.16  | Identity management                                | Partial       |
| A.5.17  | Authentication information                         | Implemented   |
| A.5.18  | Access rights                                      | Partial       |
| A.5.23  | Information security for use of cloud services     | Partial       |
| A.5.24  | Information security incident management planning and preparation | Implemented |
| A.5.25  | Assessment and decision on information security events | Implemented |
| A.5.26  | Response to information security incidents         | Implemented   |
| A.5.27  | Learning from information security incidents       | Implemented   |
| A.5.28  | Collection of evidence                             | Implemented   |
| A.5.29  | Information security during disruption             | Planned       |
| A.5.30  | ICT readiness for business continuity              | Planned       |
| A.5.34  | Privacy and protection of PII                      | Partial       |
| A.5.35  | Independent review of information security         | Not implemented |
| A.5.36  | Compliance with policies, rules and standards      | Partial       |
| A.5.37  | Documented operating procedures                    | Implemented   |

### 5.2 People controls (A.6.x — applicable subset)

| Control | Title                                              | Status        |
|---------|----------------------------------------------------|---------------|
| A.6.3   | Information security awareness, education and training | Implemented |
| A.6.4   | Disciplinary process                               | Not applicable |
| A.6.6   | Confidentiality or non-disclosure agreements       | Not applicable |
| A.6.8   | Information security event reporting               | Implemented   |

### 5.3 Physical controls (A.7.x — applicable subset)

| Control | Title                                              | Status        |
|---------|----------------------------------------------------|---------------|
| A.7.1   | Physical security perimeters                       | Accepted      |
| A.7.4   | Physical security monitoring                       | Accepted      |
| A.7.7   | Clear desk and clear screen                        | Implemented   |
| A.7.10  | Storage media                                      | Planned       |

### 5.4 Technological controls (A.8.x — applicable subset)

| Control | Title                                              | Status        |
|---------|----------------------------------------------------|---------------|
| A.8.1   | User endpoint devices                              | Partial       |
| A.8.2   | Privileged access rights                           | Partial       |
| A.8.3   | Information access restriction                     | Partial       |
| A.8.5   | Secure authentication                              | Implemented   |
| A.8.8   | Management of technical vulnerabilities            | Implemented   |
| A.8.9   | Configuration management                           | Implemented   |
| A.8.12  | Data leakage prevention                            | Partial       |
| A.8.13  | Information backup                                 | Planned       |
| A.8.15  | Logging                                            | Planned       |
| A.8.16  | Monitoring activities                              | Planned       |
| A.8.20  | Network security                                   | Implemented   |
| A.8.21  | Security of network services                       | Implemented   |
| A.8.22  | Segregation of networks                            | Implemented   |
| A.8.24  | Use of cryptography                                | Implemented   |
| A.8.25  | Secure development life cycle                      | Partial       |
| A.8.26  | Application security requirements                  | Implemented   |
| A.8.28  | Secure coding                                      | Implemented   |
| A.8.32  | Change management                                  | Implemented   |

*(The full list is in `docs/control-mapping.md` §4.4.)*

## 6. Not-applicable controls — rationale

Rather than list each of the 37 non-applicable controls, the criteria by
which they were excluded are recorded. This is the "simplified" aspect of
this SoA — appropriate for a lab with a small, well-understood scope.

| Category                  | Controls excluded | Rationale                                                                 |
|---------------------------|-------------------|---------------------------------------------------------------------------|
| Employment-related        | A.6.1, A.6.2, A.6.5 | No employment relationship; single operator working on a personal project |
| Supplier relationships    | A.5.19–A.5.22      | No suppliers beyond GitHub (covered separately under A.5.23)              |
| Physical/geographic       | A.7.2, A.7.3, A.7.5, A.7.6, A.7.8–A.7.14 | Host laptop remains at home; no office, no perimeters, no on-site staff |
| Multi-environment         | A.8.31             | Single environment; no separate dev/test/prod split                       |
| Specialised hardware      | A.7.9, A.7.12, A.7.13, A.8.10, A.8.11 | No on-premises servers, no removable assets in scope                |
| Specialised applications  | A.8.17, A.8.18, A.8.19, A.8.30, A.8.33, A.8.34 | No time-synchronisation risk, no privileged utilities, no source code access from outside, no external audit testing |

## 7. Related risk register entries

The following risk-register items correspond to controls marked as
accepted or deferred in this SoA. Each is justified in its own entry.

| SoA control | Related risk-register item                                      |
|-------------|------------------------------------------------------------------|
| A.7.1, A.7.4| `docs/risk-register.md` §4.2 (DP-01, DP-02 — physical context)   |
| A.8.2       | R-02 (no privilege separation) — planned for Phase 9             |
| A.8.13      | R-05 recurrence risk for backup (planned for Phase 10)           |
| A.8.15, A.8.16 | R-06 (no audit trail) — planned for Phase 8                   |

## 8. Review

This SoA is reviewed:

- **Annually**, alongside the password policy and the incident response
  playbook.
- **When the environment changes** in a way that affects a control's
  applicability (e.g. introducing a multi-user deployment, exposing the
  lab to the Internet, adding a supplier).
- **After every security incident** that reveals a missing control.

## 9. References

- **ISO/IEC 27001:2022** — clause 6.1.3(d) (Statement of Applicability)
- **ISO/IEC 27001:2022 Annex A** — the 93 controls
- `docs/control-mapping.md` — detailed status per control
- `docs/risk-register.md` — accepted risks and deferred best practices
- `docs/threat-model.md` — risk assessment context

---

## 10. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-08 | 1.0     | Initial SoA. Simplified format referencing control-mapping.md for detail. | Filipe Castanheira |
