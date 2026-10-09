# Vulnerability Exercise — SQL Injection

**Date:** 2026-10-09
**Phase:** 7
**Branch where introduced:** `vuln/sql-injection`
**Branch where fixed:** `fix/sql-injection`
**Status:** Fixed

---

## 1. Vulnerability

The endpoint `GET /api/assets` accepts a `search` query parameter used to
filter assets by hostname. In the vulnerable version, this parameter was
concatenated directly into the SQL query text:

    query = text(
        f"SELECT id, hostname, ip_address, os, created_at "
        f"FROM assets WHERE hostname LIKE '%{search}%' ORDER BY id"
    )

The correct pattern — parameterised SQL — is:

    query = text(
        "SELECT id, hostname, ip_address, os, created_at "
        "FROM assets WHERE hostname LIKE :search ORDER BY id"
    )
    result = db.execute(query, {"search": f"%{search}%"}).fetchall()

The difference is one character: `{search}` (interpolation) vs `:search`
(binding). The first writes the value into the query language; the second
binds it as a value. The consequence is the difference between an
application where the caller controls the *data* and an application where
the caller controls the *query*.

## 2. Evidence — before

**Control test (normal behaviour):**

    $ curl -s -H "Authorization: Bearer $TOKEN" \
        "http://127.0.0.1:8000/api/assets?search=ubuntu"
    [
        {
            "hostname": "ubuntu-lab",
            "ip_address": "192.168.1.173",
            "os": "Ubuntu 24.04",
            "id": 1,
            "created_at": "2026-09-26T17:23:46.979889"
        }
    ]

Only one asset returned. The filter works as intended.

**Attack test (SQL injection):**

    $ curl -s -H "Authorization: Bearer $TOKEN" \
        "http://127.0.0.1:8000/api/assets?search=%27%20OR%201%3D1--"
    [
        { "hostname": "ubuntu-lab", ... },
        { "hostname": "kali-attacker", ... },
        { "hostname": "test-via-nginx", ... }
    ]

All three assets returned. The payload is `' OR 1=1--` (URL-encoded). The
filter would be expected to return zero rows, because no hostname
contains the literal string `' OR 1=1--`. Instead, the SQL that reaches
the database is:

    SELECT id, hostname, ip_address, os, created_at
    FROM assets WHERE hostname LIKE '%' OR 1=1--%' ORDER BY id

The `OR 1=1` condition is always true, and the `--` comments out the
remainder of the original query. The filter is bypassed.

## 3. What the CI pipeline detected

**The bandit job failed.** The SQL injection was detected by the SAST
scanner in the CI pipeline.

**Bandit output (from the pull request check):**

    >> Issue: [B608:hardcoded_sql_expressions] Possible SQL injection
       vector through string-based query construction.
       Severity: Medium   Confidence: Low
       CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
       Location: app/main.py:104:10
       103      query = text(
       104          f"SELECT id, hostname, ip_address, os, created_at "
       105          f"FROM assets WHERE hostname LIKE '%{search}%' ORDER BY id"
       106      )

**What the other tools did:**

| Tool               | Result on the vulnerable commit         |
|--------------------|------------------------------------------|
| **bandit**         | **Failed — B608 detected**               |
| ruff               | Initially failed (UP017, unrelated); after fix, passed |
| pip-audit          | No known vulnerabilities                 |
| gitleaks           | Failed — see §7 for the cause (not a real detection) |
| eslint / oxlint    | Not applicable (backend change)          |
| OWASP ZAP baseline | Passed — baseline scan does not perform injection testing |
| pytest             | Passed — no test covers the injection case |

**Correction to an earlier note.** An earlier draft of this document
stated that bandit did not detect the vulnerability. That was incorrect:
it was written before the pipeline ran on the vulnerable commit. The
scanner works as designed. The correction is recorded here rather than
silently rewritten — a false statement about what a tool does not detect
is more dangerous than a false statement about what it does detect.

**What this demonstrates:**

1. **SAST works.** Bandit has a rule (B608) specifically for
   string-interpolated SQL. It fired.
2. **The pipeline blocks the merge.** A pull request that introduces a
   detected vulnerability cannot be merged without explicitly overriding
   the check.
3. **The detection would not have happened without the pipeline.** The
   developer (single-operator lab) wrote the vulnerable code; a reviewer
   would have needed to notice it manually. The pipeline made the
   detection automatic and consistent.

**What bandit did NOT detect and why it matters:**

Bandit is a pattern-based scanner. Its strength is that it is fast and
has almost no false negatives on its defined rule set. Its weakness is
that it only finds patterns it has rules for. The classes of
vulnerability that bandit does not detect — and which the exercise
demonstrates separately — are:

- **IDOR** — a logic flaw, not a pattern. No source code line is "wrong".
- **Broken access control** — the code is correct in isolation; the
  policy is wrong.
- **Business logic flaws** — the code does what it says; the says is
  wrong.

This is why the exercise continues past SQL injection. The categories
that pattern-based SAST cannot find are exactly the categories where
human design and test cases matter most.

## 4. Impact

If this vulnerability existed in production:

- **Any authenticated user** can read every row in the `assets` table,
  regardless of intended filters.
- With crafted payloads (not executed in this lab), the same injection
  point could:
  - Read from **other tables** in the same database, including `users`
    and any future table.
  - Modify or delete data (`UPDATE`, `DELETE`, `DROP`).
  - Extract the schema and infer application structure.
- **Confidentiality, integrity, and availability** are all at risk from
  a single injection point.

## 5. The fix

The fix replaces string interpolation with parameter binding:

    query = text(
        "SELECT id, hostname, ip_address, os, created_at "
        "FROM assets WHERE hostname LIKE :search ORDER BY id"
    )
    result = db.execute(query, {"search": f"%{search}%"}).fetchall()

The wildcards (`%`) are part of the **bound value**, not the query. Even
a payload designed to close the string and append SQL is treated as
literal text.

## 6. Evidence — after

**Same attack payload, against the fixed version:**

    $ curl -s -H "Authorization: Bearer $TOKEN" \
        "http://127.0.0.1:8000/api/assets?search=%27%20OR%201%3D1--"
    []

An empty list. The payload is treated as a literal search string that no
hostname contains. The injection is neutralised.

## 7. Detection gap and action items

| # | Action                                                                 | Owner  | Deadline |
|---|------------------------------------------------------------------------|--------|----------|
| 1 | Add a test to `tests/test_auth.py` (or a new `tests/test_injection.py`) that sends the SQLi payload and asserts that only expected rows are returned | Filipe | Before closing Phase 7 |
| 2 | Evaluate Semgrep or CodeQL for data-flow aware SAST, replacing or complementing Bandit | Filipe | Phase 12 |
| 3 | Consider a full OWASP ZAP active scan (rather than baseline) on a schedule | Filipe | Future |

**Action item 1 is the priority.** The vulnerability was detected by a
human running `curl` manually. A regression test would detect it
automatically, in the pipeline, the next time someone reintroduces the
same pattern.

## 8. References

- `docs/threat-model.md` §7.2 — T3 (SQL injection), the threat this
  exercise demonstrates.
- `docs/control-mapping.md` — OWASP A03:2021 (Injection), ISO 27001
  A.8.28 (Secure coding).
- `docs/vulnerability-management-policy.md` — the process that governs
  a finding like this in the normal course of operations.
- Commits: `vuln/sql-injection` (introduction), `fix/sql-injection` (fix).


## 9. Pull request history

The exercise was executed via two pull requests, so that the Git history
records the full cycle:

**PR #1 — Introduction of the vulnerability** (merged as `aae7677`)

- Branch: `vuln/sql-injection`
- Commits: `4814a19` (introduction), `7853059` (documentation),
  `7dabb63` (ruff UP017 fix — unrelated to the exercise, discovered
  during the PR), `9340d90` (tool version pinning — also discovered
  during the PR), `f18bc6d` (correction of the CI detection record),
  `907de53` (gitleaks permissions)
- CI result on merge: **5 checks green, 1 check red** (bandit — the
  detection that this exercise was designed to produce)

**PR #2 — Fix** (merged as `25525e5`)

- Branch: `fix/sql-injection`
- Commit: `1edcd4b` (parameter binding)
- CI result on merge: **6 checks green, 0 red**

The two CI results, taken together, are the evidence that the SAST
scanner works: it failed on the vulnerable code and passed on the fixed
code, with no other change between the two runs on `main.py`.

## 10. What this exercise demonstrated

| Aspect                                    | Outcome                          |
|-------------------------------------------|----------------------------------|
| The vulnerability was real                | Confirmed — filter bypassed      |
| It was exploitable with a trivial payload | Confirmed — `' OR 1=1--`         |
| The SAST scanner detected it              | Confirmed — bandit B608          |
| The pipeline blocked the merge            | Confirmed — Security job failed  |
| The fix removed the vulnerability         | Confirmed — payload returns `[]` |
| The fix preserved functionality           | Confirmed — normal search works  |
| The fix closed the SAST finding           | Confirmed — bandit passed        |
| The history recorded the cycle            | Confirmed — PR #1 and PR #2      |

The exercise is closed.

