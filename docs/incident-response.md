# Incident Response Playbook — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.1
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

| Control                          | Where                                  |
|----------------------------------|----------------------------------------|
| SSH key-only, no password        | deploy/hardening/sshd-hardening.conf   |
| UFW with three rules             | deploy/hardening/ufw-rules.txt         |
| Fail2Ban with custom filter      | deploy/hardening/fail2ban-*.conf       |
| TLS with internal CA             | /etc/nginx/ssl/secure-fullstack/       |
| FastAPI bound to loopback        | deploy/systemd/secure-fullstack-api.service |
| GitHub push email notifications  | GitHub repository settings             |
| Password manager with MFA        | operator's device                      |
| Disk encryption on host laptop   | OS-level (BitLocker/LUKS)              |
| Risk register with classification| docs/risk-register.md                  |
| Threat model with findings       | docs/threat-model.md                   |

Any gap in this list is documented in the risk register.

---

## 3. Severity classification

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

**Escalation rule:** if uncertain, classify one level higher than the
initial assessment and downgrade after analysis. The cost of
over-responding to a SEV-3 is low. The cost of under-responding to a
SEV-1 is high.

---

## 4. Roles

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

- The **post-mortem template** (section 7) is filled out after the
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

---

## 6. Playbooks

### 6.1 IR-1 — GitHub account compromise

**Trigger.** A push notification email is received that does not
correspond to an expected action. Or: any other signal (login alert,
unexpected password change confirmation) indicating that the GitHub
account has been accessed without authorization.

**Severity.** SEV-1 if the repository is public. SEV-2 if it is still
private. Escalate to SEV-1 if evidence of malicious commits is found.

**Detection.**

- Email notifications on push (primary).
- GitHub security log review (secondary).
- Unexpected password reset emails from GitHub (secondary).

**Containment (act immediately, in this order).**

1. Do not click links in the notification. Open GitHub directly in a
   browser that is already authenticated, and verify the commit exists.
   The notification itself could be spoofed.
2. Change repository visibility to private. If already private, skip.
3. Revoke all credentials associated with the account:
   - All deploy keys.
   - All personal access tokens.
   - The SSH key used for pushes from the Ubuntu host.
   - Any other SSH keys or tokens listed in the account settings.
   - Active sessions.
4. Rotate the account password and confirm 2FA is enabled.

**Eradication.**

5. Identify what was changed. Against a trusted local clone:

        cd ~/secure-fullstack-lab
        git fetch origin
        git log --all --oneline --graph
        git diff HEAD origin/main

6. Restore from a known-good state. The local clone may still have the
   previous state in its reflog. The external disk backup is the
   authoritative pre-incident reference.
7. Re-establish trusted access. Regenerate SSH keys, re-add the correct
   public key to GitHub, re-create tokens with minimum scope.

**Recovery.**

8. Confirm legitimate pushes work again with the new credentials.
9. Confirm no unauthorized commit remains in the history.

**Evidence to preserve.**

- A copy of the notification email (headers included).
- The GitHub security log excerpt.
- The suspect commit SHA(s) and diff, saved outside the repository.

**Post-mortem.** Required for SEV-1 and SEV-2. Focus: how access was
achieved, which detection control fired, what should have prevented it.

---

### 6.2 IR-2 — Ubuntu host compromise

**Trigger.** Any of the following:

- Unexpected processes running (identified via `ps`, `top`, or `systemd`).
- Unexpected network connections (`ss -tnp`, `netstat`).
- Changes to system files (`/etc/passwd`, `/etc/ssh/`, `sshd_config`, UFW
  rules) that the operator did not make.
- Fail2Ban has banned an unexpected IP, or the ban count is rising
  without an obvious cause.
- A notification from an external system (e.g., GitHub reports a push
  originating from the host that the operator does not recognize).
- Suspicious journal entries: repeated sudo failures, unexpected
  authentication events, kernel messages.

**Severity.** SEV-1 if root access is confirmed or suspected. SEV-2 if an
unprivileged compromise is confirmed. SEV-3 if the signal is ambiguous.

**Detection.**

- **auditd** with watches on `/etc/`, `~/secure-fullstack-lab/backend/`,
  and `~/pki/` (planned for Phase 8).
- **journalctl** for `sshd`, `sudo`, `systemd`, and `kernel`.
- **UFW log** (`/var/log/ufw.log`) for unexpected traffic.
- **Filesystem check** with `debsums`, `rpm -Va`, or manual inspection of
  modified files.
- **Process inspection** with `ps auxf`, `systemctl list-units`.
- **Network inspection** with `ss -tnp`, `lsof -i`.

**Containment (act immediately, in this order).**

1. **Do not reboot.** Rebooting destroys volatile evidence: running
   processes, network connections, memory contents.
2. **Disconnect from the network.** In VMware: uncheck the network
   adapter, or use the "Disconnect" option. In the guest, you can also:

        sudo ip link set ens33 down

   This stops any further exfiltration or command-and-control.
3. **Take a snapshot of the VM** before touching anything. In VMware:
   VM → Snapshot → Take Snapshot, named `IR-2-suspect-<date>`. This
   preserves the state for later analysis.
4. **Copy critical logs off the host**, if you have a second channel
   (e.g., the VMware console plus an external USB). At minimum, capture:

        sudo journalctl --since "24 hours ago" > /tmp/ir2-journal.log
        sudo cp /var/log/auth.log /tmp/ 2>/dev/null
        sudo cp /var/log/ufw.log /tmp/ 2>/dev/null
        sudo ss -tnp > /tmp/ir2-connections.log
        sudo ps auxf > /tmp/ir2-processes.log

   Save these to an external location (host laptop via VMware shared
   folder, or a USB if attached).

**Eradication.**

5. **Identify the entry vector.** Options to consider, in order of
   likelihood for this lab:
   - SSH key theft (the key from Kali or from the operator).
   - An unpatched service exposed to the lab network.
   - A malicious package or script that the operator accidentally ran.
   - A compromised container or VM on the same segment.
6. **Identify the persistence mechanism.** Check:
   - `crontab -l` and `/etc/cron.*`
   - `systemctl list-unit-files` for unexpected units
   - `~/.bashrc`, `~/.profile`, `/etc/profile.d/`
   - `~/.ssh/authorized_keys` for unexpected keys
   - `sudo -l` for unexpected privilege grants
7. **Remove the malicious artifact.** Only after confirming what it is
   and how it entered.
8. **Patch the entry vector.** If a vulnerable package: update it. If a
   key: revoke it. If a misconfiguration: fix it.

**Recovery.**

9. **Restore from a known-good snapshot.** For a lab, the fastest and
   safest recovery is usually a VMware snapshot taken **before** the
   compromise. This is why snapshots are taken before major changes.
10. **Rebuild if necessary.** If no clean snapshot exists, rebuild the
    VM from scratch using the `deploy/` scripts and the external backup
    of the repository and `lab.db`.
11. **Re-enable services.** Start nginx, secure-fullstack-api, fail2ban,
    ssh one at a time. Confirm each is behaving before the next.
12. **Change all credentials** that were accessible on the host: SSH
    keys, password manager (if unlocked during the compromise window),
    GitHub deploy keys, and the CA passphrase.

**Evidence to preserve.**

- The VMware snapshot taken at containment (step 3).
- The log copies captured at step 4, stored outside the host.
- The process and connection listings at the time of detection.
- A written timeline of events: what was noticed, when, and what was
  done.

**Post-mortem.** Always required. Focus:

- What was the actual entry vector, as distinct from the suspected one?
- Which detection control fired, and how long after the event?
- Which control should have fired first, and why did it not?
- Does the risk register have an entry for this class of attack? If not,
  it is added.

---

### 6.3 IR-3 — CA private key compromise

**Trigger.** Any of the following:

- The `ca.key` file has been read by an unexpected process, or copied
  from `~/pki/` (requires auditd or file monitoring).
- A certificate appears that is signed by the lab CA but was not issued
  by the operator.
- The host compromise playbook (IR-2) confirms root access — the
  `ca.key` must then be assumed compromised.

**Severity.** Always SEV-1. The CA key is the root of trust for the lab.
Its compromise invalidates every certificate the CA has signed and will
sign.

**Detection.**

- **File access monitoring** on `~/pki/` (auditd watch, planned for
  Phase 8).
- **Unexpected certificate** found in the wild (not applicable in an
  isolated lab, but relevant if the CA is ever used publicly).
- **Inherited from IR-2.** If root access is confirmed, assume the CA
  key is compromised. Do not wait for direct evidence.

**Containment.**

1. **Take the CA offline.** If the `ca.key` has any passphrase, ensure it
   is not cached in an ssh-agent or keychain during the incident window.
   If the key is on a host that is compromised, treat the file as
   already exfiltrated.
2. **Stop issuing certificates** from the compromised CA. No new
   certificates until the new CA is ready.
3. **Preserve the compromised material** for forensics (do not delete the
   `ca.key` file — its existence and content are part of the evidence).

**Eradication.**

4. **Generate a new CA.** A new pair of `ca.key` and `ca.crt`, with:

        openssl genrsa -out ca-new.key 4096
        openssl req -x509 -new -nodes -key ca-new.key -sha256 -days 3650 \
          -out ca-new.crt \
          -subj "/C=PT/O=Secure Fullstack Lab/CN=Secure Fullstack Lab Root CA v2"

   Include a version suffix ("v2") so the old and new are
   distinguishable in any trust store that might still hold both.

5. **Issue a new server certificate** for Nginx, signed by the new CA.
6. **Install the new CA on all clients** (Ubuntu, Kali):
   - Remove the old CA from `/usr/local/share/ca-certificates/`.
   - Install the new one.
   - Run `sudo update-ca-certificates`.
7. **Remove the old CA from the trust stores.** Everywhere it was
   installed. This includes the Firefox trust store if it was installed
   separately.

**Recovery.**

8. Confirm HTTPS works with the new certificate on both Ubuntu and Kali.
9. Confirm the old CA is no longer trusted anywhere (an attempt to
   connect to a service presenting a certificate signed by the old CA
   should fail).

**Evidence to preserve.**

- The old `ca.key` and `ca.crt` (kept separately, marked as compromised,
  not deleted).
- The public key fingerprints of both CAs (old and new), recorded in the
  incident log.
- A list of every certificate issued by the old CA and where it was
  deployed (in this lab, likely just the Nginx server certificate).

**Post-mortem.** Always required. Focus:

- How was the key exposed? Was it the passphrase being absent, the file
  being on a running host, or an inherited compromise from IR-2?
- Was there a control that would have prevented this and was not in
  place?
- Does this change the priority of the DP-02 (HSM) or the planned
  offline-storage of the CA key?

---

### 6.4 IR-4 — Physical loss or theft of the host laptop

**Trigger.** The laptop that hosts the lab (VMware plus the Ubuntu VM) is
lost, stolen, or accessed physically by someone other than the operator.

**Severity.** Always SEV-1. Physical access to the host is equivalent to
access to every credential, every key, and every session the operator
holds — unless disk encryption holds.

**Detection.**

- Direct observation (the laptop is missing).
- Operating-system login alerts from the host (if configured).
- Unexpected activity on any service that the laptop is registered with
  (GitHub push notifications, cloud provider login alerts).

**Containment (act as soon as you can get to another device).**

1. **From another device, immediately:**
   - Change the GitHub account password.
   - Revoke the SSH key used for pushes from the Ubuntu host.
   - Revoke any personal access tokens.
   - Sign out all sessions on GitHub.
2. **Change the master password of the password manager.** If the laptop
   had an unlocked session, assume all credentials in the vault are
   compromised.
3. **Change the CA passphrase** if the CA key is stored anywhere
   accessible from the laptop (it is, at `~/pki/`).
4. **Rotate every credential that was accessible** from the laptop:
   - SSH keys.
   - Cloud provider sessions.
   - Email account password (which gates device verification for GitHub).

**Eradication.**

Not applicable. There is no software to clean on a device that is no
longer in the operator's possession. The work here is **credential
invalidation**, not cleaning.

**Recovery.**

1. **Restore the lab on a replacement device** from the external disk
   backup (planned for Phase 10).
2. **Regenerate all keys** from scratch. Do not restore the old SSH keys
   or the old CA key — regenerate them. The old ones are permanently
   considered compromised.
3. **Reinstall the new CA certificate** on clients (Kali, and any other
   device that trusts it).

**Evidence to preserve.**

- Police report, if the device was stolen.
- Timeline of last known use and where the device was last seen.
- A list of credentials that were on the device, so that rotation can
  be verified as complete.

**Post-mortem.** Always required. Focus:

- Was the disk encryption actually enabled and verified? If not, this is
  the first action item.
- Was the external-disk backup actually up to date? If not, this is the
  second action item.
- Does the risk register have an entry for "physical access to host"?
  (It does — R-02 references it as a compensating control dependency.)

**Note on scope.** Software controls are irrelevant at this point. The
only effective control is the OS-level disk encryption, which is why it
is listed in the preparation controls of section 2.1. This playbook
exists to ensure that after the physical event, the digital cleanup is
executed systematically.

---

### 6.5 IR-5 — Suspected data exfiltration of lab.db

**Trigger.** Any of the following:

- Unexpected access to `lab.db` recorded by auditd or file monitoring.
- Unusual outbound traffic from the FastAPI process (network monitoring).
- A large or unexpected query appearing in the application logs.
- An external party demonstrating knowledge of data that only exists in
  `lab.db`.

**Severity.** SEV-2 if suspected, SEV-1 if confirmed. The current data
in `lab.db` is Internal classification (asset inventory, no personal
data). Severity rises once user accounts exist.

**Detection.**

- **auditd watch** on `lab.db` and its sidecar files (`-wal`, `-shm`).
- **Application logs** — unexpected `SELECT * FROM assets` or repeated
  queries outside normal patterns.
- **Network monitoring** — outbound connections from the FastAPI process
  to destinations other than `127.0.0.1` and the SQLite file.
- **File size anomaly** — a sudden decrease in size could indicate
  truncation; a sudden increase could indicate injected data.

**Containment.**

1. **Stop the FastAPI service.**

        sudo systemctl stop secure-fullstack-api.service

   This stops any ongoing exfiltration through the application.
2. **Isolate the host from the network** (as in IR-2, step 2).
3. **Copy `lab.db` and its sidecars to a separate location** before any
   further action:

        cp ~/secure-fullstack-lab/backend/lab.db /tmp/ir5-lab-db-copy
        cp ~/secure-fullstack-lab/backend/lab.db-wal /tmp/ 2>/dev/null
        cp ~/secure-fullstack-lab/backend/lab.db-shm /tmp/ 2>/dev/null

   Store these off the host.

**Eradication.**

4. **Identify the exfiltration path.** Options:
   - Direct file access by a non-application process.
   - Query via the API (an endpoint returning data to an unauthorised
     party).
   - Extraction by a process running as `filipe` that read the file
     directly.
5. **Close the path.** If via the API: the endpoint is locked down. If
   via file access: file permissions are corrected and auditd rules
   updated.
6. **Rotate credentials** that could have been used to reach the
   database.

**Recovery.**

7. **Assess data integrity.** Run:

        sqlite3 ~/secure-fullstack-lab/backend/lab.db "PRAGMA integrity_check;"

   Any failure indicates the file is corrupt or has been tampered with.
8. **Restore from the external backup** if the file cannot be trusted.
9. **Re-enable the FastAPI service.** Confirm the API works and the
   assets table is intact.

**Evidence to preserve.**

- The copied `lab.db` (frozen state).
- The auditd log entries for the access.
- Network captures (if available).
- The application log excerpt.

**Post-mortem.** Required if SEV-1, recommended if SEV-2. Focus:

- What was actually read, if determinable? All rows? Specific rows?
- Could the exfiltration have been detected earlier? Which control was
  closest to firing?
- Does the data classification of `lab.db` need to be revised (currently
  Internal)?

---

## 7. Post-mortem template

Fill this in after the incident is closed. It is not a status report.
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

## 3. Impact

What was affected, what was not. Be explicit about what is unknown.

## 4. Detection

How the incident was detected. How long between the event and detection.

## 5. Response

What was done, in what order. Include decisions and their rationale.

## 6. Root cause

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
- **When the architecture changes.**

---

## 9. References

### 9.1 Standards

- **NIST SP 800-61 Rev. 2** — Computer Security Incident Handling Guide
- **ISO/IEC 27001:2022** — controls A.5.24 to A.5.28
- **NIS2** — Article 21(2)(b)

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
| 2026-10-05 | 1.0     | Initial playbook. IR-1 complete.        | Filipe Castanheira |
| 2026-10-05 | 1.1     | IR-2 to IR-5 completed. Full playbook.  | Filipe Castanheira |
