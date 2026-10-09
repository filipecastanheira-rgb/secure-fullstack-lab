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

**Nothing.**

| Tool               | Result on the vulnerable commit         |
|--------------------|------------------------------------------|
| ruff               | `All checks passed!`                     |
| bandit             | No issues identified                     |
| pip-audit          | No known vulnerabilities                 |
| gitleaks           | No secrets found                         |
| eslint / oxlint    | Not applicable (backend change)          |
| OWASP ZAP baseline | Not applicable — baseline scan does not perform injection testing |

**This is the central finding of the exercise.** None of the automated
tools in the pipeline detected a SQL injection in the source code. The
tools are working as designed — they are not designed to detect this
class of vulnerability. This is a known limitation, documented in the
JOURNAL under "What the pipeline does NOT prove".

The detection mechanisms that would have caught it:

1. **Manual code review** — the reviewer sees `f"...{search}..."` and
   recognises the anti-pattern.
2. **A dedicated test** — a unit test that sends the payload and asserts
   that only the expected rows are returned. This test does not exist
   yet; it is on the action list for this exercise.
3. **DAST with injection testing enabled** — the OWASP ZAP baseline scan
   does not perform injection tests. A full scan (or an active scan)
   would, given enough time and coverage.
4. **A SAST tool with data-flow analysis** — Bandit is pattern-based and
   does not perform taint analysis. Tools such as Semgrep or CodeQL can
   track user input from source to sink and would have flagged this.

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
