# Simulated Incident Exercise — Brute-force on Login Endpoint

**Owner:** Filipe Castanheira
**Date performed:** 2026-10-08
**Playbook exercised:** IR-2 (host compromise) — with reference to IR-1
  for the account-compromise scenario it could have led to
**Outcome:** Contained automatically. No data exposed. Controls verified.

---

## 1. Purpose

ISO/IEC 27001:2022 A.5.27 requires that the organisation learns from
information security incidents. A playbook that has never been exercised
is a document, not a capability. This exercise was performed to:

- Validate that the controls documented in the playbooks actually work
  under real conditions.
- Measure how long the incident takes to detect and contain.
- Identify what the logs capture, and what they miss.
- Produce a genuine post-mortem with action items that feed back into the
  risk register.

The scenario was chosen because it is common, harmless, and directly
relevant to the assets in scope: a repeated, automated credential-guessing
attempt against the login endpoint.

---

## 2. Scenario

**Attacker profile:** A remote actor (in this lab: the Kali VM at
`<KALI_IP>`) sending a scripted sequence of login attempts with wrong
passwords, hoping to guess a valid credential.

**Target asset:** `POST /api/auth/login` on the application, reached via
Nginx on port 443.

**Objective of the exercise:** Verify that:

1. The rate limiting at the Nginx edge actually throttles repeated
   attempts.
2. The FastAPI backend does not authenticate a scripted brute force.
3. The logs record enough to reconstruct the attempt after the fact.
4. The response codes distinguish "rejected by backend" from "rejected
   by edge", so a future analyst can tell what happened.

---

## 3. Execution

**Command (from Kali):**

    for i in $(seq 1 20); do
      curl -sk -o /dev/null -w "%{http_code} " \
        -X POST https://<UBUNTU_IP>/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"admin@example.com","password":"tentativa-numero-'$i'"}'
    done

**Observed response codes, in order:**

    401 401 401 401
    429 429 429 429 429 429 429 429 429 429
    429 429 429 429 429 429

- **4 × 401** — reached FastAPI, rejected by the application
- **16 × 429** — rejected at the Nginx edge, before reaching the backend

**Wall-clock duration:** approximately 3 seconds (from log timestamps).

---

## 4. Evidence collected

The Nginx access log for the affected endpoint was extracted after the
simulation:

    sudo grep "auth/login" /var/log/nginx/secure-fullstack.access.log | tail -25

**Excerpt (timestamps and body of the response shown as observed):**

    <KALI_IP> - - [08/Oct/2026:19:41:20 +0100] "POST /api/auth/login HTTP/2.0" 401  39 "-" "curl/8.20.0"
    <KALI_IP> - - [08/Oct/2026:19:41:20 +0100] "POST /api/auth/login HTTP/2.0" 401  39 "-" "curl/8.20.0"
    <KALI_IP> - - [08/Oct/2026:19:41:20 +0100] "POST /api/auth/login HTTP/2.0" 401  39 "-" "curl/8.20.0"
    <KALI_IP> - - [08/Oct/2026:19:41:21 +0100] "POST /api/auth/login HTTP/2.0" 401  39 "-" "curl/8.20.0"
    <KALI_IP> - - [08/Oct/2026:19:41:21 +0100] "POST /api/auth/login HTTP/2.0" 429 178 "-" "curl/8.20.0"
    <KALI_IP> - - [08/Oct/2026:19:41:21 +0100] "POST /api/auth/login HTTP/2.0" 429 178 "-" "curl/8.20.0"
    ... (14 more lines of 429)
    <KALI_IP> - - [08/Oct/2026:19:41:23 +0100] "POST /api/auth/login HTTP/2.0" 429 178 "-" "curl/8.20.0"

**Fields present:**

| Field        | Value                              | What it establishes                    |
|--------------|------------------------------------|----------------------------------------|
| Source IP    | `<KALI_IP>`                    | Originating host on the lab network    |
| Timestamp    | `08/Oct/2026:19:41:20` → `19:41:23`| Three-second window, 20 requests       |
| Method+path  | `POST /api/auth/login HTTP/2.0`    | The endpoint targeted                  |
| Status       | `401` then `429`                   | Transition from backend rejection to edge rejection |
| Body size    | `39` bytes then `178` bytes        | JSON (39) vs HTML (178)                |
| Referrer     | `"-"`                              | No referrer — consistent with a script |
| User-Agent   | `curl/8.20.0`                      | Automated client, not a browser        |

**What the log establishes beyond doubt:**

1. **Origin:** the traffic came from one IP.
2. **Timing:** the request cadence was ~6–7 per second. This is not human
   behaviour. A human attempting a login types at most one attempt every
   few seconds.
3. **Tool:** the user-agent identifies the client as `curl`, not a browser.
   A legitimate login from a browser would show a browser UA string.
4. **Layer of rejection:** the change in body size from 39 to 178 bytes
   is the digital fingerprint of the transition from FastAPI (JSON, 39
   bytes) to Nginx (HTML error page, 178 bytes). Without that distinction,
   an analyst could not tell where the request was rejected.

## 5. What the exercise proved

### 5.1 The rate limit worked as designed

Only 4 out of 20 requests reached the backend. The other 16 were
discarded at the Nginx edge. This is the intended behaviour: absorb the
attack as early as possible, before it consumes application resources.

### 5.2 The cost of the attack was bounded

Every login attempt that reaches FastAPI triggers a password verification
with argon2id, using 64 MB of RAM and 3 iterations. Twenty attempts would
have consumed ~1.28 GB and several hundred milliseconds of CPU. Because
only 4 attempts reached the backend, actual consumption was ~256 MB. This
is the difference between "the attacker can drain the server" and "the
attacker is capped at a fixed cost per minute".

### 5.3 The user enumeration prevention held

All four requests that reached FastAPI received 401 with the same
generic message (`Invalid email or password.`). Even though the simulated
attacker was targeting `admin@example.com` — an account that does not
exist in this lab — the response is indistinguishable from a wrong
password on an existing account. No information was leaked.

### 5.4 The logs are usable for retrospective analysis

The complete attack can be reconstructed from the Nginx access log alone:

- Origin IP
- Start and end time
- Number of attempts
- Client tool
- Outcome at each stage

This satisfies the A.5.28 requirement (Collection of evidence) for this
class of incident.

### 5.5 Detection was not automatic

**This is the finding.** The attack was detected **after the fact**, by a
manual log grep. There is currently no mechanism that raises an alert
when the rate limiter starts rejecting requests. In a production
environment with 24/7 operations, this would be unacceptable: the attack
would have to be noticed by someone reading logs.

**This is the primary action item of this exercise** (see §7).

---

## 6. Post-mortem

Filled using the template from `docs/incident-response.md` §7.

### 6.1 Summary

A simulated brute-force attack against the login endpoint was executed
from the Kali VM over a three-second window. Of twenty requests, four
reached the FastAPI backend and were rejected; sixteen were refused at
the Nginx edge by the rate limiter. No credential was guessed, no data
was exposed, and the application remained available throughout. The
incident was contained automatically, but was only detected by manual
log inspection after the fact.

### 6.2 Timeline

| Time      | Event                                                        |
|-----------|--------------------------------------------------------------|
| 19:41:20  | First four login attempts reach FastAPI and are rejected (401)|
| 19:41:21  | Rate limiter engages; subsequent requests refused at edge (429)|
| 19:41:23  | Last request in the simulated batch                          |
| 19:42     | Operator inspects Nginx access log to reconstruct the attack |

**Time from first attempt to containment:** immediate (automatic).
**Time from attack end to detection:** approximately 40 seconds (manual).
**Time from detection to full understanding:** under 1 minute.

### 6.3 Impact

- **Confidentiality:** none. No data was read or disclosed.
- **Integrity:** none. No data was modified.
- **Availability:** none. The application remained responsive throughout,
  as demonstrated by legitimate access continuing to work after the
  simulated attack.
- **Reputation:** none in this exercise (internal simulation).

### 6.4 Detection

The attack was **not** detected automatically. Detection occurred when
the operator ran a manual `grep` against the Nginx access log looking for
the affected endpoint. Had the operator not been looking, the attack
would have completed and left no alert.

This is the single most important finding of the exercise. It confirms
what the risk register already recorded as R-06 (no audit trail) and
partially as A.8.15/A.8.16 gaps: the system has controls, but does not
currently tell anyone when they are being used.

### 6.5 Response

The response was **automatic**. The rate limiter engaged without
intervention. No manual containment was required. This is the design
intent of edge controls: contain without depending on human reaction time.

### 6.6 Root cause

- **Immediate cause:** a scripted sequence of login attempts.
- **Contributing causes:** none. The attack did not exploit a weakness;
  it exercised a control that worked as designed.
- **Root cause:** not applicable to the attack itself, because the attack
  did not succeed. However, the *exercise* revealed a **detection gap**:
  controls that act silently produce no signal for monitoring.

### 6.7 What went well

- **Rate limiting worked exactly as designed.** Four requests reached
  the backend, sixteen were refused at the edge. This is the correct
  balance: some legitimate attempts succeed, some are throttled.
- **The backend remained available.** No degradation in service.
- **The generic 401 message held.** No information was leaked even
  though the attacker specifically probed for an `admin` account.
- **The logs told the whole story.** A single grep was enough to
  reconstruct origin, timing, tool, and outcome.
- **The transition from 401 to 429 was visible in the log.** The change
  in response body size (39 → 178 bytes) makes it possible for an analyst
  to know which layer responded.

### 6.8 What went badly

- **No automated alert.** The incident was invisible until someone
  looked. In a real deployment, this would be a serious detection gap.
- **No timestamped incident record by the system itself.** The logs are
  raw Nginx output; there is no application-level record of "rate limit
  hit for IP X at time Y", only the log lines that an analyst must
  aggregate manually.
- **No automated counter.** Determining how many attempts occurred
  required `grep | wc -l` by hand. A structured log would provide this
  without post-processing.

### 6.9 Corrective action items

| # | Action                                                                 | Owner  | Deadline   | Related to          |
|---|------------------------------------------------------------------------|--------|------------|---------------------|
| 1 | Add an alert when the rate limiter begins rejecting requests (e.g., Nginx `error_log` parsing, or a cron that detects a spike in 429s) | Filipe | Phase 8    | R-06, A.8.16        |
| 2 | Configure structured logging on the FastAPI side (JSON) to record failed login attempts with timestamp, source IP, and user identifier (or "unknown") | Filipe | Phase 8    | R-06, A.8.15        |
| 3 | Add a threshold-based alert: if more than N failed logins from one IP in T minutes, raise an alert (in addition to the rate limiting already in place) | Filipe | Phase 8    | Threat model §7.2 D1 |
| 4 | Consider moving to a full SIEM in a future project (out of scope for this lab, documented in the risk register §4.2 as DP-05) | Filipe | Future     | DP-05               |

**Action item #1 is the priority.** Without it, the rate limiting is a
prevention control that never generates a signal. Prevention + detection
is the goal; prevention alone leaves the operator blind to the attacks
that are being blocked.

### 6.10 Risk register update

- **Entries closed:** none. The exercise did not close a risk.
- **Entries added:** none. The detection gap is already captured by R-06
  (no audit trail) and by the A.8.15 and A.8.16 gaps discussed above.
- **Entries modified:** none at this time. The exercise confirms the
  current status of R-06 and the planned Phase 8 work. If a future
  exercise reveals the detection gap is still unaddressed after Phase 8,
  this entry will be revisited.

---

## 7. Conclusion

The exercise achieved its purpose: it validated the controls that
existed, and it revealed a gap that the documents alone had not made
obvious. Specifically:

- **Prevention works.** The rate limiter at the Nginx edge effectively
  bounded the attack.
- **Logging works.** The evidence needed to reconstruct the attack is
  present in the access log.
- **Detection does not yet work.** Nothing raises an alert when the
  controls act. This is the finding that Phase 8 will address.

The value of the exercise is exactly this: a control that works silently
is half a control. The system now knows what to build next, and has the
evidence to justify it.

---

## 8. References

- `docs/incident-response.md` — the playbooks that were exercised
- `docs/incident-response.md` §7 — the post-mortem template used here
- `docs/risk-register.md` — R-06 (no audit trail), DP-05 (SIEM)
- `docs/statement-of-applicability-v2.md` — A.8.15, A.8.16 (logging and monitoring; current status)
- `docs/threat-model.md` §7.2 — D1 (rate limiting threat)
- NIST SP 800-61 Rev. 2 — the framework used for the post-mortem
- ISO/IEC 27001:2022 — A.5.27 (Learning from incidents), A.5.28 (Evidence)

---

## 9. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-08 | 1.0     | Initial exercise. Brute-force on login endpoint. Primary finding: no automated detection. | Filipe Castanheira |
