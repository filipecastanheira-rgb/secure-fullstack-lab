# Vulnerability Exercise — IDOR (Insecure Direct Object Reference)

**Date:** 2026-10-10
**Phase:** 7
**Branch where introduced:** `vuln/idor`
**Branch where fixed:** `fix/idor`
**Status:** Fixed

---

## 1. Vulnerability

A new endpoint `GET /api/assets/{asset_id}` was added to return a single
asset by id. The endpoint requires authentication (via
`Depends(get_current_user)`) but does **not** verify that the requesting
user owns the asset:

    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()

There is no check on `asset.owner_id`. Any authenticated user can read
any asset by guessing or enumerating its id.

The fix adds the missing ownership filter:

    asset = (
        db.query(models.Asset)
        .filter(
            models.Asset.id == asset_id,
            models.Asset.owner_id == current_user.id,
        )
        .first()
    )

The difference is one clause: `models.Asset.owner_id == current_user.id`.
The consequence is the difference between an endpoint that returns "your
asset" and one that returns "any asset you ask for".

**This is different in nature from the SQL injection exercise.** SQL
injection is a code pattern — a string is interpolated into a query, and
the shape of the vulnerability is visible in the source. IDOR is a
**logic flaw**: the code is syntactically correct, uses the ORM safely,
and does nothing that any pattern-based scanner would flag. What is
missing is a condition that the developer should have known to add.

## 2. Why this class of vulnerability is important

**IDOR is in the OWASP Top 10.** It is part of A01:2021 (Broken Access
Control), which has been the top-ranked category in the OWASP Top 10
since the 2017 revision. It is not an edge case — it is the most
commonly reported application security issue in bug bounty programmes.

**It maps to the three-level authorization model in the threat model
(§7.3).** The model distinguishes:

| Level | Question                                  | Where enforced         | Status here |
|-------|-------------------------------------------|------------------------|-------------|
| L1    | Can this subject call this endpoint?      | Auth dependency, RBAC  | ✅ Implemented |
| **L2**| **Can this subject see this row?**        | **Query filter (IDOR)**| ❌ **The vulnerability** |
| L3    | Can this subject see this field of this row? | Response schema     | ✅ Implemented |

The three levels are independent. A system that implements L1 and L3 but
not L2 is vulnerable to IDOR while passing every automated check. This
is the exact situation of the vulnerable commit.

**It appears in the threat model as threat E2** ("IDOR — Insecure Direct
Object Reference"), classified as `[partial: phase 7]` since the
authentication work in Phase 4. The classification was a placeholder for
the demonstration that happens here.

## 3. Evidence — before

**Setup.** Two users with separate asset inventories:

- Filipe (id 1, role admin) owns assets with ids 1, 2, 3
- Joana (id 2, role user) owns asset with id 4

**Control tests — each user reads their own asset:**

    # Filipe reads asset 1 (his)
    $ curl -H "Authorization: Bearer $TOKEN_ADMIN" \
        http://127.0.0.1:8000/api/assets/1
    {
      "hostname": "ubuntu-lab",
      "ip_address": "<UBUNTU_IP>",
      "os": "Ubuntu 24.04",
      "id": 1,
      "owner_id": 1,
      ...
    }

    # Joana reads asset 4 (hers)
    $ curl -H "Authorization: Bearer $TOKEN_USER" \
        http://127.0.0.1:8000/api/assets/4
    {
      "hostname": "joana-laptop",
      "ip_address": "10.0.0.50",
      "os": "Windows 11",
      "id": 4,
      "owner_id": 2,
      ...
    }

Both succeed. The endpoints work as intended for the "correct" cases.

**Attack test — Joana reads Filipe's asset:**

    # Joana reads asset 1 (Filipe's)
    $ curl -H "Authorization: Bearer $TOKEN_USER" \
        http://127.0.0.1:8000/api/assets/1
    {
      "hostname": "ubuntu-lab",
      "ip_address": "<UBUNTU_IP>",
      "os": "Ubuntu 24.04",
      "id": 1,
      "owner_id": 1,
      ...
    }

**The request succeeded.** Joana, whose token identifies her as user 2,
received asset 1 — which belongs to user 1. The `owner_id` field in the
response confirms that the asset does not belong to her; the server
returned it anyway.

This is IDOR. The same URL returned different content to the two users —
but only because the id was different. Given a valid id of another
user's asset, both users receive the same content.

## 4. Impact

If this vulnerability existed in production:

- **Any authenticated user** can read any asset in the system, by
  enumerating ids. The ids are sequential integers — no guesswork is
  required.
- **The confidentiality of the entire assets table is lost** — not by
  exploit, but by simply iterating over `GET /api/assets/1`,
  `GET /api/assets/2`, and so on.
- **The impact scales with future data.** The current assets table
  contains only hostname, IP, and OS. As the application grows —
  user records, credentials, scan results, incident reports — every one
  of them inherits the same flaw if the endpoint is not corrected. The
  pattern, not the current data, is the risk.

The severity is lower than the SQL injection exercise in immediate
terms (no data modification is possible here, only reading). The
severity is higher in strategic terms: this class of bug is the most
common finding in real-world application security assessments, and the
mistake is easy to make again with any new endpoint.

---

## 5. The fix

The fix adds an ownership filter to the query:

    asset = (
        db.query(models.Asset)
        .filter(
            models.Asset.id == asset_id,
            models.Asset.owner_id == current_user.id,
        )
        .first()
    )

Two conditions instead of one. The endpoint now returns an asset only
if it both exists AND belongs to the requesting user.

### 5.1 Why 404 and not 403

For an asset that exists but belongs to another user, the endpoint
returns **404 Not Found**, not 403 Forbidden. This is deliberate.

**403 Forbidden** would say: "this asset exists, but you are not allowed
to see it". A caller who enumerates ids would learn which ids exist.

**404 Not Found** says: "there is no asset with this id" — which is
false, but indistinguishable from a genuinely non-existent id. An
attacker iterating over `/api/assets/1`, `/api/assets/2`, and so on
learns only which ids belong to the caller. They learn nothing about
the existence of other users' assets.

This is the same principle as the generic login error message
(`"Invalid email or password."`) — multiple internal cases, one external
response. At the object level rather than the authentication level.

## 6. Evidence — after

**Control tests — each user reads their own asset:**

    $ curl -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $TOKEN_ADMIN" \
        http://127.0.0.1:8000/api/assets/1
    200

    $ curl -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $TOKEN_USER" \
        http://127.0.0.1:8000/api/assets/4
    200

Both succeed. Functionality is preserved.

**Attack test — Joana reads Filipe's asset:**

    $ curl -H "Authorization: Bearer $TOKEN_USER" \
        http://127.0.0.1:8000/api/assets/1
    {"detail":"Asset not found."}

    Status: 404

The vulnerability is closed. Joana, with a valid token identifying her
as user 2, cannot retrieve asset 1 (owned by user 1). The endpoint
behaves as if the asset did not exist.

### 6.1 The behavioural comparison

| Request                                | Before  | After   |
|----------------------------------------|---------|---------|
| Filipe → `/api/assets/1` (his)          | 200     | 200     |
| Joana  → `/api/assets/4` (hers)         | 200     | 200     |
| **Joana → `/api/assets/1` (Filipe's)**  | **200** | **404** |

One row changed. That row is the fix. The two rows above it confirm
that the fix did not break the legitimate cases.

---

## 7. What the CI pipeline did

**Nothing detected the vulnerability.** The complete pipeline ran green
on the vulnerable commit, with the IDOR endpoint present and exploitable.

| Job                    | Result on the vulnerable commit | Why it did not detect |
|------------------------|---------------------------------|------------------------|
| Lint (ruff)            | ✅ Passed                       | Valid Python            |
| Tests (pytest)         | ✅ Passed                       | No existing test covered the cross-user case |
| Security (bandit)      | ✅ **Passed**                   | **No unsafe pattern to flag** |
| Secrets (gitleaks)     | ✅ Passed                       | No secret was involved  |
| Frontend lint          | ✅ Passed                       | Backend-only change     |
| DAST (ZAP baseline)    | ✅ Passed                       | Baseline scan does not test authorisation |
| Route policy test      | ✅ Passed                       | The endpoint *does* require authentication |

The pipeline was green. The vulnerability was present.

**The bandit result is the point.** This is the same scanner that
detected the SQL injection exercise's vulnerable code (B608). It does
not — and cannot — detect IDOR, because IDOR is not a pattern in the
code. The vulnerable code contains no string interpolation, no `eval`,
no `subprocess`, no weak hash, no hard-coded secret. It contains a query
that is missing a condition. Bandit has no rule for "missing
authorisation check" because that is not a syntactic property — it is a
property of the *policy* the code is supposed to implement.

**The route policy test is a subtler case.** This test exists
specifically to catch endpoints added without authentication. It fired
on the SQL injection exercise — no, it did not; it verified that the
endpoint required auth, which it did. Here it also verified the
endpoint required auth, which it also did. The test is correct. It
simply tests the wrong layer for this class of bug: it checks L1
(endpoint authentication), not L2 (row-level authorisation).

**The vulnerability was detected by:**

1. **A manual `curl` test** comparing what two users see. This is what
   the exercise used to demonstrate the vulnerability.
2. **A regression test that will be added** as part of the fix. The test
   exists to prevent the same pattern from being reintroduced.

Neither of the automated tools in the pipeline detected it. This is the
central lesson of the exercise.

## 8. Detection gap and action items

The pipeline cannot detect IDOR. It can detect the *introduction* of
IDOR patterns only if a specific test is written for them. The
regression test added with the fix is the mechanism that closes this
particular gap.

| # | Action                                                                 | Owner  | Deadline       |
|---|------------------------------------------------------------------------|--------|----------------|
| 1 | Add a pytest test that verifies a user cannot read another user's asset via `GET /api/assets/{id}` | Filipe | Same PR as the fix |
| 2 | Extend the review checklist: every endpoint that accepts a resource id must verify ownership — added to the threat model as a "code review note" | Filipe | Before closing Phase 7 |
| 3 | Evaluate tools with taint analysis (Semgrep, CodeQL) for L2 authorisation flows | Filipe | Phase 12 (final polish) |

**Action item 1 is done in the fix commit itself.** The regression test
is part of the deliverable, not a follow-up. Without it, the fix would
only be a behavioural correction; with it, the fix becomes a defence
against regression.

**Action item 3 has a limitation worth noting.** Taint analysis tools
can track user input to sensitive sinks (SQL, filesystem, exec). They
are much weaker at detecting *missing* authorisation logic, because
"missing a check" is not a data flow — it is the absence of one. Even
the best SAST tools cannot reliably catch IDOR. This is a known
limitation of static analysis, not a gap specific to this project.

## 9. Conclusion

The exercise demonstrates, side by side with the SQL injection
exercise, two different classes of vulnerability and two different
detection stories:

| Exercise      | Nature              | SAST (bandit)  | Manual test | Regression test |
|---------------|---------------------|----------------|-------------|-----------------|
| SQL injection | Code pattern        | **Detected** (B608) | Detected | Would need to be written |
| IDOR          | Logic flaw          | **Missed**     | Detected    | **Written as part of the fix** |

Both exercises produced a fix and a documented trail. The IDOR exercise
adds one thing the SQL injection exercise did not: an automated test
that encodes the policy. Without it, the fix would be defensible only
by the memory of the person who wrote it. With it, the policy is
enforceable by the pipeline.

**This is the shape of the answer to "how do you prevent IDOR?"** Not
"run bandit", not "review the code". The answer is: know what the policy
is, write a test that checks it, and let the pipeline fail when the
policy is violated. Automated detection of logic flaws is possible —
but only when the policy is stated in a form the tool can execute.

---

## 10. References

- `docs/threat-model.md` §7.2 — E2 (IDOR), the threat this exercise
  demonstrates. §7.3 — the three-level authorisation model that
  situates the vulnerability at L2.
- `docs/control-mapping.md` — OWASP A01:2021 (Broken Access Control).
- `docs/statement-of-applicability-v2.md` — ISO 27001 A.5.18 (Access rights),
  A.8.3 (Information access restriction).
- `docs/vuln-exercise-sqli.md` — the companion exercise, for contrast.
- OWASP Top 10 — A01:2021 Broken Access Control (top-ranked since 2017).

---

## 11. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-10 | 1.0     | Initial exercise. IDOR on GET /api/assets/{id}. Detection: manual and regression test only — no scanner found it. | Filipe Castanheira |
