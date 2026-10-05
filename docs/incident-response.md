# Incident Response Playbook — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.0
**Effective date:** 2026-10-05
**Classification:** Internal
**Framework reference:** NIST SP 800-61 Rev. 2

---

## 1. Purpose and scope

This document defines how the operator of the Secure Fullstack Lab
detects, responds to, and learns from security incidents.

It exists because:

- **Before an incident** is the wrong time to decide what to do.
- A response that is improvised under pressure produces inconsistent
  results and destroys evidence.
- After an incident, the value of the response is largely determined by
  what was prepared beforehand.

### 1.1 What this document covers

- Incidents affecting the lab infrastructure (Ubuntu host, VMs, network
  segments).
- Incidents affecting the code, its source of truth, or its supply chain.
- Incidents affecting credentials, keys, or trust material (TLS CA, SSH
  keys, tokens).
- Incidents involving data confidentiality, integrity, or availability.

### 1.2 What this document does not cover

- Business continuity for a production service (this is a lab).
- Legal or regulatory notification procedures (mapped in section 9 but not
  executed here; the lab holds no personal data of third parties).
- Physical security procedures (covered indirectly in section 3.1 as a
  compensating control).

---

## 2. Framework

The response process follows **NIST SP 800-61 Rev. 2**, with four phases:

    ┌───────────────────────┐
    │  1. Preparation       │  Controls in place BEFORE anything happens
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  2. Detection and     │  Perceive the event and understand it
    │     Analysis          │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  3. Containment,      │  Stop the bleeding, clean up, restore
    │     Eradication, and  │
    │     Recovery          │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │  4. Post-Incident     │  Learn, update, improve
    │     Activity          │
    └───────────────────────┘

### 2.1 Preparation already in place

The preparation phase is not a document. It is the state of the system.
As of the effective date of this playbook, the following preparation
controls exist:

| Control                          | Where                                  |
|----------------------------------|----------------------------------------|
| SSH key-only, no password        | `deploy/hardening/sshd-hardening.conf` |
| UFW with three rules             | `deploy/hardening/ufw-rules.txt`       |
| Fail2Ban with custom filter      | `deploy/hardening/fail2ban-*.conf`     |
| TLS with internal CA             | `/etc/nginx/ssl/secure-fullstack/`     |
| FastAPI bound to loopback        | `deploy/systemd/secure-fullstack-api.service` |
| GitHub push email notifications  | GitHub repository settings             |
| Password manager with MFA        | operator's device                      |
| Disk encryption on host laptop   | OS-level (BitLocker/LUKS)              |
| Risk register with classification| `docs/risk-register.md`                |
| Threat model with findings       | `docs/threat-model.md`                 |

Any gap in this list is documented in the risk register.

---

## 3. Severity classification

Not every incident is the same. Classifying severity **first** determines
how much response is warranted and how quickly.

### 3.1 Severity levels

| Level    | Description                                                       | Response target  |
|----------|-------------------------------------------------------------------|------------------|
| **SEV-1**| Confirmed compromise of trust material (CA key, root access), or confirmed data exfiltration | Immediate |
| **SEV-2**| Confirmed compromise of an account or service, without evidence of exfiltration | Within 1 hour |
| **SEV-3**| Suspicious event requiring investigation but no confirmation of compromise | Within 24 hours |
| **SEV-4**| Minor event or anomaly with no immediate impact | Within 1 week |

### 3.2 How to classify

Classification is based on two questions:

1. **What was compromised?** Account, service, data, trust material?
2. **Is the impact ongoing or already done?**

An incident is not upgraded because the operator is worried. It is
upgraded because the answers to those two questions justify it.

**Escalation rule:** if uncertain, classify one level higher than the
initial assessment and downgrade after analysis. The cost of
over-responding to a SEV-3 is low. The cost of under-responding to a
SEV-1 is high.

---

## 4. Roles

This lab has a single operator. In production environments, the roles
below would be distributed. Here, they are all filled by the same person.
This is itself a limitation, documented in section 4.1.

| Role                    | Responsibility                                                |
|-------------------------|---------------------------------------------------------------|
| **Incident Lead**       | Owns the response end-to-end. Makes the call on severity.     |
| **Investigator**        | Analyzes logs, reproduces events, identifies scope.           |
| **Communicator**        | Notifies affected parties (in this lab, only the operator).   |
| **Documenter**          | Records the timeline, decisions, and evidence.                |

### 4.1 The single-operator limitation

Separation of duties does not exist in this lab. The same person
investigates, decides, acts, and documents. This produces three risks:

- **Confirmation bias.** The operator may anchor on an initial theory
  and miss contradicting evidence.
- **No second opinion.** A mistake is not caught by another human.
- **Documentation is often skipped.** The operator is busy responding.

**Compensating measures:**

- The **post-mortem template** (section 7) is filled out **after** the
  incident, when the pressure has eased.
- Findings from the post-mortem are recorded in the risk register, so
  that the "second opinion" eventually comes from the record itself.

---

## 5. Playbook format

Each scenario in section 6 follows the same structure:

    Trigger      What event starts the playbook
    Severity     Expected classification
    Detection    How the event would be noticed
    Containment  Stop the bleeding (act fast)
    Eradication  Remove the cause
    Recovery     Restore normal operation
    Evidence     What to preserve for analysis
    Post-mortem  Whether required and what to focus on

This structure matches NIST SP 800-61's phases but uses vocabulary that
stays consistent across scenarios.

---

## 6. Playbooks

### 6.1 IR-1 — GitHub account compromise

**Trigger.** A push notification email is received that does not
correspond to an expected action. Or: any other signal (login alert,
unexpected password change confirmation) indicating that the GitHub
account has been accessed without authorization.

**Severity.** SEV-1 if the repository is public. SEV-2 if it is still
private, because the exposure is limited to pre-publication knowledge.
Escalate to SEV-1 if evidence of malicious commits is found.

**Detection.**

- Email notifications on push (primary).
- GitHub security log review (secondary).
- Unexpected password reset emails from GitHub (secondary).

**Containment (act immediately, in this order).**

1. **Do not click links in the notification.** Open GitHub directly in a
   browser that is already authenticated, and verify the commit exists.
   The notification itself could be spoofed.

2. **Change repository visibility to private.** If it is already private,
   skip. If it is public, this is the first action. It stops the exposure
   from spreading further.

3. **Revoke all credentials associated with the account:**
   - All deploy keys.
   - All personal access tokens.
   - The SSH key used for pushes from the Ubuntu host.
   - Any other SSH keys or tokens listed in the account settings.
   - Active sessions (GitHub settings, Sessions).

4. **Rotate the account password** and confirm 2FA is enabled.

**Eradication.**

5. **Identify what was changed.** Against a trusted local clone:

        cd ~/secure-fullstack-lab
        git fetch origin
        git log --all --oneline --graph
        git diff HEAD origin/main

   Any commit that is not recognized as the operator's is suspect.

6. **Restore from a known-good state.** If the history has been
   rewritten (git push --force):

   - The local clone on the Ubuntu host may still have the previous state
     in its reflog.
   - The external disk backup (when implemented) is the authoritative
     pre-incident reference.

7. **Re-establish trusted access.** Regenerate SSH keys, re-add the
   correct public key to GitHub, re-create any necessary tokens with
   minimum scope.

**Recovery.**

8. Confirm that legitimate pushes work again, with the new credentials.
9. Confirm that no unauthorized commit remains in the history.

**Evidence to preserve.**

- A copy of the notification email (headers included, not just the body).
- The GitHub security log excerpt (or screenshot, if export is not
  available).
- The suspect commit SHA(s) and diff, saved to a file outside the
  repository.

**Post-mortem.** Required for SEV-1 and SEV-2. Focus:

- How was the initial access achieved?
- Which detection control fired first, and how long after the event?
- What should have prevented this, and why did it not?
- Does the risk register need updating?

### 6.2 IR-2 — Ubuntu host compromise

*Placeholder. To be written in a future session. Will cover: detection
of unauthorized processes, unexpected network connections, changes to
system files, and a full host integrity check procedure.*

### 6.3 IR-3 — CA private key compromise

*Placeholder. To be written in a future session. Will cover: how a
compromise would be detected, why it requires rebuilding the entire PKI,
and how to safely regenerate and redistribute the CA.*

### 6.4 IR-4 — Physical loss or theft of the host laptop

*Placeholder. To be written in a future session. Will cover: the
assumption that physical access is game over for software controls, the
role of disk encryption, and the steps to invalidate every credential
held on the device.*

### 6.5 IR-5 — Suspected data exfiltration of lab.db

*Placeholder. To be written in a future session. Will cover: detection
via unexpected file access, evidence collection, and the assessment of
whether exfiltration actually occurred.*

---

## 7. Post-mortem template

Fill this in **after** the incident is closed. It is not a status report.
It is the learning artefact.

<!-- BEGIN POST-MORTEM TEMPLATE -->
# Post-Mortem — [Incident ID]

**Date of incident:**
**Date of detection:**
**Date of closure:**
**Severity:**
**Classification:**
**Playbook used:**

## 1. Summary

One paragraph. What happened, in plain language.

## 2. Timeline

| Time  | Event |
|-------|-------|
|       |       |

Precise times where possible, otherwise sequence order.

## 3. Impact

What was affected, what was not. Be explicit about what is unknown.

## 4. Detection

How the incident was detected. How long between the event and detection.

## 5. Response

What was done, in what order. Include decisions and their rationale, not
just actions.

## 6. Root cause

Why did this happen? Distinguish between:

- Immediate cause: the specific event.
- Contributing causes: what made it possible.
- Root cause: the underlying weakness.

## 7. What went well

Be specific. Nothing is not an acceptable answer.

## 8. What went badly

Be specific. Everything is not an acceptable answer.

## 9. Action items

| Action | Owner | Deadline | Risk register entry |
|--------|-------|----------|---------------------|
|        |       |          |                     |

Every action item either closes a risk or creates a new one.

## 10. Risk register update

- Entries closed:
- Entries added:
- Entries modified:
<!-- END POST-MORTEM TEMPLATE -->

---

## 8. Maintenance

This document is reviewed:

- **Annually**, alongside the password policy.
- **After every incident**, before the post-mortem is closed.
- **When the architecture changes** (a new component, a new trust
  boundary, a new data flow).

If a scenario occurs that is not covered by an existing playbook, a new
one is written as part of the post-mortem action items.

---

## 9. References

### 9.1 Standards

- **NIST SP 800-61 Rev. 2** — Computer Security Incident Handling Guide
- **ISO/IEC 27001:2022** — controls A.5.24 to A.5.28 (incident management)
- **NIS2** — Article 21(2)(b) (incident handling)

### 9.2 ISO 27001 mapping

| Control  | Title                                              | Addressed by     |
|----------|----------------------------------------------------|------------------|
| A.5.24   | Information security incident management planning and preparation | Section 1, 2 |
| A.5.25   | Assessment and decision on information security events | Section 3, 4 |
| A.5.26   | Response to information security incidents         | Section 5, 6     |
| A.5.27   | Learning from information security incidents       | Section 7        |
| A.5.28   | Collection of evidence                             | Section 6 (each playbook) |

---

## 10. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-05 | 1.0     | Initial playbook. IR-1 complete; IR-2 to IR-5 placeholders. | Filipe Castanheira |
