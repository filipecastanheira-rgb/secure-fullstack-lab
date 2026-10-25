# Password Policy — Secure Fullstack Lab

**Owner:** Filipe Castanheira
**Version:** 1.0
**Effective date:** 2026-10-05
**Review cycle:** Annually, or after any incident that involves credential compromise
**Classification:** Internal

---

## 1. Purpose

This policy defines how passwords and other authentication secrets are
created, stored, used, rotated, and revoked within the Secure Fullstack Lab.

The policy applies to:

- Human accounts (operator, administrators)
- Service accounts used by applications on the lab host
- Third-party service accounts (GitHub, cloud providers, etc.)
- Administrative access to network devices and virtualisation platforms

The objective is to ensure that credential-based access remains a
defensible control, not an assumed one.

---

## 2. Scope and applicability

The policy covers every credential that grants access to a system, service,
or piece of data within the lab, whether that credential is:

- Entered by a human (interactive login)
- Configured in a file (application configuration, script)
- Issued by a service (API tokens, deploy keys, SSH keys)

**Out of scope:**
- Public certificates (not secrets)
- Public keys (not secrets)
- Session cookies issued by a running application (covered by the
  application's own controls)

---

## 3. Technical requirements

### 3.1 Passwords for human accounts

| Requirement          | Value                                                       |
|----------------------|-------------------------------------------------------------|
| Minimum length       | 15 characters                                               |
| Maximum length       | No limit imposed; must support at least 64 characters       |
| Character classes    | Any combination of upper case, lower case, digits, symbols  |
| Uniqueness           | Must not be reused across any two systems                   |
| Predictability       | Must not contain the username, service name, or obvious sequences |
| Storage (server side)| Argon2id, bcrypt, or scrypt — never MD5, SHA-1, or plain SHA-256 |

**Note on length over complexity.** Research and standards (NIST SP 800-63B,
NCSC guidance) converge on length as the dominant factor in resistance to
offline attacks. Complexity requirements are retained as a general
expectation, not as the primary control.

**Update 2026-10-25.** The maximum-length row states the policy requirement and is
unchanged. In the lab, `backend/app/schemas.py` limits the password to 128 characters
when a user is created (line 61, `min_length=15`, `max_length=128`) and in the login
schema (`LoginRequest`, line 96, `max_length=128`), so "no limit imposed" does not describe the
implementation. The requirement to support at least 64 characters is met. Checked by
reading the code; no request was sent to test the limit.

### 3.2 Passphrases

Users are encouraged to use **passphrases** — several unrelated words
joined together — instead of short complex passwords. A 5-word passphrase
typically exceeds 20 characters with higher entropy than a 12-character
random string, and is easier to remember.

Example form (illustrative, not to be used): `quiet-forest-silver-rock-tower`

### 3.3 Storage on the client

Passwords for human accounts **must** be stored in a password manager.
Storing credentials in:

- Plain text files
- Browser-embedded password managers (as the only copy)
- Spreadsheets or notes
- Physical media (paper)

...is prohibited.

### 3.4 Password managers

The password manager must:

- Encrypt the vault with a master password (minimum 15 characters)
- Support MFA on the vault itself (TOTP or hardware key)
- Be backed up in encrypted form (see §6 on offboarding)
- Not be shared between users

**Current implementation:** the operator uses a password manager meeting
these requirements. The master password is unique, is not stored anywhere
electronically, and is different from every password it protects.

### 3.5 Multi-factor authentication (MFA)

MFA is **required** for every service that supports it. Preference order:

1. **Hardware security key** (FIDO2 / WebAuthn) — phishing-resistant
2. **TOTP app** (Aegis, Bitwarden Authenticator, etc.) — software, portable
3. **Push notification** with number matching — acceptable
4. **SMS** — last resort; susceptible to SIM-swap and interception

**SMS is not acceptable as the only second factor for administrative
accounts.**

### 3.6 Credential uniqueness

Every credential must be unique to its service. Reuse across services is
prohibited. This is why a password manager is mandatory — uniqueness at
scale is not achievable by memory alone.

---

## 4. Credential lifecycle

### 4.1 Rotation

Rotation is the **event-driven replacement** of a credential. Two models
exist in this policy:

- **Scheduled rotation** — periodic, calendar-based
- **Event-driven rotation** — triggered by a specific event

The policy uses **different rotation models for different account types**.
The reason is that the same rule cannot be optimal for a user account with
MFA and a service account with a shared secret.

### 4.2 Rotation schedule by account type

| Account type                        | Rotation model         | Interval        |
|-------------------------------------|------------------------|-----------------|
| Human account with MFA              | Event-driven only      | On event        |
| Human account without MFA           | Scheduled              | 180 days        |
| Privileged account (sudo, admin)    | Scheduled + event-driven | 90 days       |
| Service account (application, CI)   | Scheduled + event-driven | 90 days       |
| API token / PAT                     | Scheduled              | 90 days or expiry of the token, whichever is sooner |
| Deploy key                          | Event-driven           | On staff change or compromise |
| SSH key                             | Event-driven + periodic review | Annually   |
| Root / emergency account            | Scheduled              | 180 days; access logged |

### 4.3 Events that trigger rotation

Regardless of the schedule above, rotation is **immediate** on:

- Suspected or confirmed compromise of the credential
- Detection of the credential in a public leak (Have I Been Pwned,
  breach notifications)
- Change of role or privilege level
- Departure of a user with knowledge of a shared credential
- Incident response involvement of the account
- Loss or theft of the device where the credential is stored

### 4.4 Rotation of prohibited forms

The following forms of rotation are **not permitted**:

- Incremental changes (`Password1` → `Password2` → `Password3`)
- Seasonal or year-based patterns (`Summer2026!` → `Winter2026!`)
- Reversal or permutation of the previous credential
- Reuse of a previously used credential, at any point in history

A rotation that produces a predictable variant is worse than no rotation:
it satisfies the policy on paper and reduces real entropy.

### 4.5 Rationale for the two-speed model

The classic "rotate every 30 days for everything" rule was inherited from
an era before password managers and widespread MFA. It produced two
problems:

1. **Predictability** — users created variants of the same password to
   keep up with the rule, reducing effective entropy.
2. **Operational cost** — reset requests, helpdesk load, productivity loss,
   and mis-coordination with dependent systems.

**Modern guidance** (NIST SP 800-63B) recommends against scheduled rotation
in favour of event-driven rotation, combined with:

- Length (see §3.1)
- Screening against known-breached passwords
- MFA (see §3.5)

**Where scheduled rotation is retained** in this policy:

- Accounts **without** MFA — the credential is the only control, so time
  is the only limiting factor.
- **Privileged accounts** — the impact of compromise is disproportionate;
  a bounded exposure window is worth the operational cost.
- **Service accounts** — often shared among operators and rarely covered
  by MFA; periodic rotation ensures all holders are re-validated.

**Where scheduled rotation is removed** in this policy:

- Human accounts **with MFA** — the second factor already bounds the
  exposure window. Forcing rotation adds cost without proportional gain.

This is a deliberate compromise: not the classic "rotate everything", not
the modern "rotate nothing". The choice is documented so it can be
reviewed if the environment changes.

---

## 5. Privileged accounts

Accounts with administrative privileges (`sudo`, root-equivalent, admin
consoles) are subject to additional requirements:

- **Shorter rotation interval** — 90 days (see §4.2)
- **MFA required** where the platform supports it
- **Separate account from the daily-use account** — see §5.1
- **All authentication events logged** and reviewed
- **Access reviewed quarterly** — is this account still needed?
- **No credential sharing** — each administrator has their own privileged
  account

### 5.1 Separation of accounts

Where the platform permits it, the operator uses **at least two accounts**:

- **Daily-use account** — no administrative privileges; used for normal
  work
- **Administrative account** — elevated privileges; used only when
  elevation is required

The daily-use account is the one exposed to normal risk (browsing, email,
code editing). If it is compromised, the attacker inherits little. The
administrative account is used on demand and is not present in day-to-day
activity.

**Status in this lab:** `[partial]` — planned for Phase 9 (configuration as
code), when the final set of accounts is known. During the construction
phase, the operator account retains full `sudo` by design (documented in
the threat model §7.5).

**Update 2026-10-25.** The label was `[planned]`. `docs/JOURNAL.md` records Phase 9 as
closed (Session 22), and what it separated was the service: the application runs as
`secure-app` (no shell, no sudo), which closed R-02. On the VM, `/etc/passwd`
listed `filipe` as the only user with a UID of 1000 or more, so no separate
administrative and daily-use accounts were found. `id` showed `filipe` in the groups `adm`,
`sudo`, `lxd` and `docker`, and `/etc/group` listed `filipe` as the only member of
`sudo`, `lxd` and `docker`. Checked on 2026-10-25.

### 5.2 Break-glass accounts

A break-glass account is a credential that exists to regain access when
normal authentication has failed or is unavailable.

Requirements:

- Stored in the password manager, not in the operator's memory
- Rotated after every use
- Its use triggers a review

**Current lab:** the VMware console access to the Ubuntu VM acts as the
break-glass path for the host. The OS-level disk encryption passphrase of
the laptop is the ultimate break-glass for the physical device.

---

## 6. Offboarding and revocation

When an account, credential, or role ends — whether due to a person leaving,
a service being decommissioned, or a project being closed — the following
apply:

- **Revoke, do not just rotate.** Rotation leaves the old credential valid
  until the new one is fully propagated; revocation removes access
  immediately.
- **Revoke in dependency order:** first the credential itself, then the
  sessions, then the tokens derived from it.
- **Audit the revocation.** Confirm the account or credential cannot be
  used after revocation. In most platforms this is a login attempt that
  should fail.

### 6.1 Backups and offboarding

The password manager vault must be:

- Backed up in encrypted form, in a location separate from the primary
  device
- Tested for recovery before it is relied upon (a backup that cannot be
  restored is not a backup)
- Decommissioned according to the same data-handling policy as any other
  sensitive material

---

## 7. Exceptions

Any exception to this policy must be:

1. **Documented** — what is excepted, and for which account or service
2. **Justified** — why the exception is necessary
3. **Bounded in time** — an exception is not permanent
4. **Reviewed** — at the next policy review or earlier if circumstances
   change

Exceptions are not gaps. They are decisions, and they are recorded.

### 7.1 Current exceptions

| Ref | Exception | Justification | Review date |
|-----|-----------|---------------|-------------|
| E-01 | Administrative account not separated from daily-use account during construction phase | The lab is under active construction; account separation requires a stable set of accounts. Planned for Phase 9. | Phase 9 completion |
| E-02 | SSH key on the operator's Kali VM has no passphrase requirement in a specific case | The key has a passphrase applied as of Session 9 (2026-10-04). No active exception. | Closed |
| E-03 | Lab database (SQLite) is not encrypted at rest | The host VM disk is encrypted at rest (LUKS); the database file inherits this protection. Additional application-layer encryption is a Phase 10 consideration. | Phase 10 |

**Update 2026-10-25.** E-01: the review date, "Phase 9 completion", has passed and the
exception was not revised in this document. Phase 9 separated the service account
(`secure-app`) but not an administrative account from a daily-use account (see 5.1).
E-03: inside the VM, `lsblk -f` showed `sda2` as `ext4` mounted on `/`, with no
`crypto_LUKS` layer. This does not show how the disk is stored outside the VM, which
was not checked. Both rows are kept as written on 2026-10-05.

---

## 8. References

### 8.1 Standards and guidance

- **NIST SP 800-63B** — *Digital Identity Guidelines: Authentication and
  Lifecycle Management* — sections 5.1.1 (memorized secrets) and 5.1.4
  (rate limiting)
- **NCSC (UK)** — *Password policy: updating your approach*
- **CIS Controls v8** — Control 5 (*Account Management*) and Control 6
  (*Access Control Management*)
- **OWASP ASVS** — V2 (*Authentication*) and V3 (*Session Management*)

### 8.2 ISO/IEC 27001:2022 mapping

| Control  | Title                                              | Addressed by     |
|----------|----------------------------------------------------|------------------|
| A.5.15   | Access control                                     | §3, §5           |
| A.5.16   | Identity management                                | §3, §5.1         |
| A.5.17   | Authentication information                         | §3, §4, §5       |
| A.5.18   | Access rights                                      | §5, §6           |
| A.8.5    | Secure authentication                              | §3.5, §4.5       |

### 8.3 NIS2 mapping

Article 21(2)(i) — *human resources security, access control policies and
asset management*. This policy implements the access control and credential
lifecycle portion of that requirement.

---

## 9. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-05 | 1.0     | Initial policy. Two-speed rotation model documented. | Filipe Castanheira |
| 2026-10-25 | 1.1     | Status notes added: maximum length (3.1), account separation (5.1, label changed from `[planned]` to `[partial]`), exceptions E-01 and E-03 (7.1). Original text kept. | Filipe Castanheira |

---

## Appendix A — Passwords to avoid

The following are examples of patterns that fail the requirements in §3,
even if they technically meet length or complexity rules:

- `Company2026!` — contains the year and a predictable suffix
- `P@ssw0rd` with any trailing characters — appears on every breach list
- `qwerty` sequences with digits appended
- Keyboard walks (`asdfghjkl;`)
- Reused base with a site-specific prefix (`github_filipe_01`)
- Anything that appeared in a public breach (check Have I Been Pwned
  before accepting)
- The user's own name, email, or any element of it

The determining test is not "does it meet the rules" but "would an
attacker with the hash be able to crack it in reasonable time, and would
someone who knows the user be able to guess it".
