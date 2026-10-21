# Vulnerability Exercise — Permissive CORS with Credentials

**Date:** 2026-10-12
**Phase:** 7
**Branch where introduced:** `vuln/cors`
**Branch where fixed:** `fix/cors`
**Status:** Fixed

---

## 1. Vulnerability

A `CORSMiddleware` was added to the FastAPI application with a
permissive configuration:

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

The combination of `allow_origins=["*"]` with `allow_credentials=True` is
the vulnerable pattern. A developer writing `["*"]` typically believes
the resulting policy is "any origin, but without credentials" — which is
the correct interpretation for CORS alone. With `allow_credentials=True`
enabled, the practical effect is different, and it is more permissive
than the developer intended.

The correct pattern, when CORS is needed at all, is an explicit allowlist
of known origins — for example
`allow_origins=["https://<UBUNTU_IP>"]` — with no wildcards.

### 1.1 The subtlety that makes this vulnerability deceptive

The wildcard in `allow_origins=["*"]` does not survive the combination
with `allow_credentials=True`. The CORS specification forbids the
combination of `Access-Control-Allow-Origin: *` with
`Access-Control-Allow-Credentials: true` — the browser rejects it.

Starlette, the framework underlying FastAPI, resolves this by **echoing
the specific origin of each request** instead of sending the literal
`*`:

    access-control-allow-origin: https://evil.example.com
    access-control-allow-credentials: true

To a developer inspecting the header, this looks like a specific origin
was allowed — as though a narrow allowlist had been configured. In
reality, the middleware echoes **whatever origin the caller supplies**.
The wildcard is not gone; it has been reformatted into something less
obvious.

**This is the core lesson of the exercise.** A configuration that looks
restrictive in the response headers can be functionally identical to a
wildcard.

## 2. Why this class of vulnerability matters

**CORS misconfiguration is not a small problem.** It is one of the most
commonly reported findings in web application security assessments, and
it appears in several OWASP categories:

- **A01:2021 Broken Access Control** — a permissive CORS policy is an
  access control failure, because it grants cross-origin access that the
  application did not intend to grant.
- **A05:2021 Security Misconfiguration** — the root cause is a
  misconfigured security control.
- **A07:2021 Identification and Authentication Failures** — when
  credentials are involved, the misconfiguration intersects with
  authentication.

**The CORS mechanism is easy to misunderstand because it is a
browser-enforced policy.** Servers emit headers. Browsers enforce them.
A request that the browser refuses to read on behalf of a JavaScript
caller is still processed by the server. CORS protects the *user's
browser session* from being used by another origin — it does not protect
the server from direct requests. This distinction is not obvious to
developers who have not encountered it directly.

## 3. Evidence — before

**Control test — request from a neutral origin:**

    $ curl -s -i -H "Origin: https://example.com" \
        http://127.0.0.1:8000/api/hello
    HTTP/1.1 200 OK
    ...
    access-control-allow-origin: https://example.com
    access-control-allow-credentials: true
    vary: Origin
    ...

**Attack test — request from an attacker-controlled origin:**

    $ curl -s -i -H "Origin: https://evil.example.com" \
        http://127.0.0.1:8000/api/hello
    HTTP/1.1 200 OK
    ...
    access-control-allow-origin: https://evil.example.com
    access-control-allow-credentials: true
    vary: Origin
    ...

**The two responses are structurally identical.** The middleware does
not distinguish between the legitimate origin and the attacker origin.
It echoes the caller's origin in both cases and asserts that credentials
are allowed.

A browser running a page at `https://evil.example.com` that issued
`fetch('https://<UBUNTU_IP>/api/hello', { credentials: 'include' })`
would receive the response, read the `Access-Control-Allow-Origin`
header, find its own origin echoed back, and **allow the JavaScript
caller to read the response body**.

## 4. Impact

**In theory, the impact is severe.** A permissive CORS policy with
credentials enabled allows any website to make authenticated requests on
behalf of a user who is currently logged into the application. Every
action the user can perform, the attacker can perform — read their data,
create or modify records, delete them — from a page the user happens to
visit while logged in.

**In practice, for this specific application, the impact is currently
limited.** The application uses **JWT in the `Authorization` header**,
not cookies. A browser does not automatically attach an `Authorization`
header to cross-origin requests:

- The JWT is stored by the SPA in `localStorage` (or `sessionStorage`).
- `localStorage` is scoped to the origin. JavaScript running on
  `evil.example.com` cannot read the JWT stored for
  `https://<UBUNTU_IP>`.
- Without the JWT, the attacker cannot send an authenticated request —
  they can only send unauthenticated requests, which the API rejects.

The attack requires an attacker who has both (a) a victim user actively
logged in, and (b) the ability to make the browser attach the victim's
credentials to a cross-origin request. The current architecture does not
provide (b).

**Why the finding still matters.** Three reasons:

1. **The configuration is wrong.** It violates the principle of least
   privilege regardless of whether it is currently exploitable. A
   control that is configured incorrectly is a liability waiting for
   the surrounding conditions to change.
2. **The migration to cookies is planned.** The password policy
   (`docs/password-policy.md`) and the threat model discuss the
   transition to `HttpOnly` cookies for refresh tokens — the safer
   pattern for token storage. The moment that migration happens, the
   CORS misconfiguration becomes immediately exploitable. The
   configuration error must be corrected before the architecture
   changes, not after.
3. **The subtlety is what makes the finding valuable.** The response
   headers look like an allowlist. A reviewer looking only at the
   response would see a specific origin and conclude that the policy is
   narrow. Recognising that the origin is echoed, not filtered, requires
   knowledge of how the framework implements the wildcard.


---

## 5. The fix

The `CORSMiddleware` was **removed entirely** rather than being replaced
with a restrictive allowlist.

    # CORS is intentionally not configured here.
    #
    # The application is served by Nginx on a single origin
    # (https://<UBUNTU_IP>), with the frontend and the API under the same
    # hostname. There are no cross-origin requests, so no CORS policy is
    # required.
    #
    # If the architecture changes and the frontend is served from a different
    # origin in the future, CORS must be reintroduced with an explicit
    # allowlist of known origins. Wildcards combined with
    # `allow_credentials=True` are not acceptable — see
    # `docs/vuln-exercise-cors.md` for the demonstration of why.

**Why removal, not replacement.** The application's architecture makes
CORS unnecessary. Nginx serves the frontend and proxies the API under
the same origin (`https://<UBUNTU_IP>`). The browser sees no
cross-origin requests because there are none. Configuring an allowlist
would be configuring for a scenario that does not exist — a form of
security theatre that adds complexity without adding protection.

**When CORS would be required.** If the architecture changes and the
frontend is served from a different origin — for example, a CDN on a
separate domain, or a mobile app talking to the API — CORS must be
reintroduced. The pattern then is:

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://app.example.com"],  # explicit, no wildcard
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],  # explicit
        allow_headers=["Authorization", "Content-Type"],  # explicit
    )

Every element of the policy is explicit. No wildcards. The comment in
the fixed source makes this clear so that a future developer who needs
to add CORS finds the pattern that is correct, not the pattern that is
convenient.

## 6. Evidence — after

**Same attack test, against the fixed version:**

    $ curl -s -i -H "Origin: https://evil.example.com" \
        http://127.0.0.1:8000/api/hello
    HTTP/1.1 200 OK
    date: Mon, 12 Oct 2026 16:08:30 GMT
    server: uvicorn
    content-length: 37
    content-type: application/json

    {"message": "Hello from FastAPI 👋"}

**The CORS headers are gone.** No `Access-Control-Allow-Origin`, no
`Access-Control-Allow-Credentials`, no `Vary: Origin`.

A browser running a page at `https://evil.example.com` that issues a
cross-origin request to this API receives the response at the HTTP
layer, but the browser refuses to expose the response body to the
JavaScript caller — the same-origin policy blocks it because the server
did not authorize the cross-origin read.

### 6.1 The behavioural comparison

| Request                                    | Before  | After   |
|--------------------------------------------|---------|---------|
| `Origin: https://example.com` (neutral)    | `Access-Control-Allow-Origin: https://example.com` | (no CORS headers) |
| `Origin: https://evil.example.com` (attacker) | `Access-Control-Allow-Origin: https://evil.example.com` | (no CORS headers) |

**The two rows collapse into one.** Before the fix, the server replied
with a different allowed-origin header for every caller. After the fix,
the server replies with no CORS headers at all, regardless of who is
asking. The policy is no longer conditional on the caller's origin.

## 7. What the CI pipeline did

**Nothing detected the vulnerability.** The complete pipeline ran green
on the vulnerable commit.

| Job                    | Result on the vulnerable commit | Why it did not detect |
|------------------------|---------------------------------|------------------------|
| Lint (ruff)            | ✅ Passed                       | Valid Python |
| Tests (pytest)         | ✅ Passed                       | No test sent an `Origin` header, so the CORS middleware did not engage |
| Security (bandit)      | ✅ Passed                       | No unsafe pattern — CORS is a configuration, not a code smell |
| Secrets (gitleaks)     | ✅ Passed                       | No secret involved |
| Frontend lint          | ✅ Passed                       | Backend-only change |
| DAST (ZAP baseline)    | ✅ Passed                       | The ZAP baseline sends no `Origin` header, so the CORS middleware never activates |

**The DAST result deserves a closer note.** The ZAP baseline scan sends
plain HTTP requests without an `Origin` header. The CORS middleware only
emits headers when the request carries an `Origin`. From the ZAP scan's
perspective, the server looks identical with or without the permissive
configuration — the middleware never engages. A more thorough DAST
configuration (an active scan, or a scanner configured to send an
`Origin` header) would have a chance of detecting the misconfiguration,
but the baseline configuration in this pipeline does not.

**This completes the pattern demonstrated across the three exercises.**
See §8 for the consolidated comparison.


---

## 8. The three Phase 7 exercises, side by side

Phase 7 is now complete. The three exercises were not chosen at random:
they cover three distinct classes of vulnerability, and three distinct
détection stories. The comparison is the value of the phase.

| Aspect                          | SQL Injection              | IDOR                       | CORS (this exercise)      |
|---------------------------------|----------------------------|----------------------------|---------------------------|
| **Nature**                      | Code pattern               | Logic flaw                 | Configuration             |
| **Where the flaw lives**        | In the code                | In what the code omits     | In a header policy        |
| **Detected by ruff**            | ❌ No                      | ❌ No                      | ❌ No                     |
| **Detected by bandit**          | ✅ Yes (B608)              | ❌ No                      | ❌ No                     |
| **Detected by pytest (before)** | ❌ No test existed         | ❌ No test existed         | ❌ No test existed        |
| **Detected by ZAP baseline**    | ❌ No                      | ❌ No                      | ❌ No                     |
| **CI turned red?**              | ✅ Yes                     | ❌ No                      | ❌ No                     |
| **How it was detected**         | Pipeline (bandit)          | Manual + written test      | Manual (header inspection)|
| **Regression test added**       | ❌ Not yet (see §9)        | ✅ Yes (6 tests)           | ✅ Yes (2 tests)          |

**The distribution is the point.** One in three vulnerabilities was
detected automatically. Two in three were not, and neither of the two
could have been.

**Why this matters for the portfolio.** A junior candidate's repository
often claims "the code is secure" or "we run security scans". Neither
claim is falsifiable. This repository demonstrates the boundary: here is
what the scanners catch, here is what they do not, and here is how the
gaps are covered — with tests, with review practices, and with the
documented decision to accept certain residual risks.

An auditor or hiring manager reading the three `vuln-exercise-*.md`
files sees something specific: **the ability to distinguish between what
a tool provides and what it does not**, and the discipline to compensate
for the difference.

## 9. Detection gap and action items

| # | Action                                                                 | Owner  | Deadline                    |
|---|------------------------------------------------------------------------|--------|-----------------------------|
| 1 | Add a regression test for the SQL injection fix (parameter binding) — currently missing | Filipe | Before closing Phase 7      |
| 2 | Consider an active ZAP scan (not just baseline) that sends `Origin` headers and exercises injection endpoints | Filipe | Phase 12 (final polish)     |
| 3 | Document the CORS decision in the deployment notes for the Nginx config: "no CORS configuration is required because the frontend and API share an origin" | Filipe | Phase 12                    |

**Action item 1 is the notable one.** The SQL injection exercise was
closed with a fix but without a regression test. The IDOR and CORS
exercises both included tests. This is an inconsistency that should be
corrected — the SQL injection fix is currently protected only by the
behaviour of the code, not by a test that would catch its regression.

The test itself is trivial: send a `search` value containing the
injection payload and assert that only the expected rows come back. It
belongs in `tests/test_asset_authorization.py` or in a new
`tests/test_asset_search.py`.

## 10. References

- `docs/threat-model.md` §7.2 — the FastAPI STRIDE analysis. CORS was
  documented as removed in Session 6 (Nginx unifies the origin) and
  reintroduced here for the exercise.
- `docs/control-mapping.md` — OWASP A01:2021 (Broken Access Control),
  A05:2021 (Security Misconfiguration); ISO 27001 A.5.14 (Information
  transfer), A.8.20 (Network security).
- `docs/vuln-exercise-sqli.md` — the first exercise, for contrast.
- `docs/vuln-exercise-idor.md` — the second exercise, for contrast.
- MDN Web Docs — *Cross-Origin Resource Sharing (CORS)* — the reference
  for the browser-side enforcement model.
- OWASP — *CORS OriginHeaderScManual* — the canonical explanation of the
  wildcard-with-credentials trap.

## 11. Review history

| Date       | Version | Change                                  | Author |
|------------|---------|-----------------------------------------|--------|
| 2026-10-12 | 1.0     | Initial exercise. CORS with wildcard and credentials. Detection: manual header inspection only — no scanner found it. | Filipe Castanheira |
