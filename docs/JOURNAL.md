# Secure Fullstack Lab — Development Journal

Chronological log of decisions, commands and issues found throughout the project.
Purpose: (1) document for portfolio, (2) restore context, (3) learn from mistakes.

---

## Current architecture

    Frontend (Vue + Vite)   →   Backend (FastAPI)   →   [soon: SQLite]
    http://192.168.1.173:5173     http://192.168.1.173:8000

Machines:
- Ubuntu (VMware) — 192.168.1.173 — hosts the project
- Kali (VMware) — 192.168.1.125 — client / browser / testing

---

## Session 1 — Bootstrapping frontend and backend

**Goal:** have Vue and FastAPI running and reachable from Kali.

- FastAPI backend responding at `/` with `{"message": "Secure Fullstack Lab API is running"}`.
- Vue frontend running with `npm run dev -- --host 0.0.0.0`.
- Initial `App.vue` only displayed "You did it!" (Vite template).

**Issue 1:** Firefox on Kali could not open `http://192.168.1.173:5173`.
**Diagnosis (layer by layer):**
1. `ss -ltnp | grep 5173` on Ubuntu → Vite listening on `0.0.0.0:5173` (OK).
2. `curl` on Ubuntu → `HTTP/1.1 200 OK` (OK).
3. `ping` from Kali → replies (network OK).
4. `curl` from Kali → `HTTP/1.1 200 OK` (network + firewall + Vite OK).
**Conclusion:** the issue was browser-side (cache/refresh). Fixed with `Ctrl+Shift+R`.

**Lesson:** always diagnose layer by layer — network → firewall → service → browser.

---

## Session 2 — Connecting Vue to FastAPI

**Goal:** Vue performs a `fetch` to FastAPI and displays the response on screen.

**Backend (`backend/main.py`):**
- Added `CORSMiddleware` with allowed origins:
  - `http://localhost:5173`
  - `http://192.168.1.173:5173`
- New endpoint: `GET /api/hello` → `{"message": "Hello from FastAPI 👋"}`.

**Frontend (`frontend/src/App.vue`):**
- `ref` for reactive state (`message`).
- `onMounted` to trigger `fetch` when the component mounts.
- `await fetch('http://192.168.1.173:8000/api/hello')` + `await res.json()`.
- `{{ message }}` in the template to display the response.

**Issue 2:** `NetworkError when attempting to fetch resource` in the browser.
**Cause:** FastAPI had died in the meantime (killed with the terminal).
**Diagnosis:** `curl -H "Origin: http://192.168.1.173:5173" -i ...` showed `access-control-allow-origin` while the server was alive → CORS was fine.
**Solution:** start FastAPI and Vite with `nohup ... &` so they survive the terminal closing.

**Result:** Firefox on Kali shows `Hello from FastAPI 👋` — Vue ↔ FastAPI working. ✅

---

## Useful commands

Start FastAPI in background:

    cd ~/secure-fullstack-lab/backend
    source .venv/bin/activate
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ~/fastapi.log 2>&1 &

Start Vite in background:

    cd ~/secure-fullstack-lab/frontend
    nohup npm run dev -- --host 0.0.0.0 > ~/vite.log 2>&1 &

View logs:

    tail -f ~/fastapi.log
    tail -f ~/vite.log

Check what is using a port:

    sudo ss -ltnp | grep <port>

Kill a process:

    kill <PID>

---

## Architecture decisions

- **Explicit CORS** (no `"*"`), because we will use credentials later.
- **`/api` prefixes** on endpoints, to separate API from pages.
- **SQLite first, PostgreSQL later** — code will be written with SQLAlchemy so migration is just swapping the connection string.
- **`nohup` in development** — temporary solution; in production we will use systemd/supervisor.

---

## Next step

- Data persistence with SQLite + SQLAlchemy.



---

## Session 3 — Persistent data with SQLite + SQLAlchemy

**Goal:** replace in-memory data with a real database, keeping the door open
to swap SQLite for PostgreSQL later without rewriting business code.

**Backend restructure:**

    backend/
    ├── app/
    │   ├── __init__.py      # marks "app" as a Python package
    │   ├── main.py          # FastAPI entry point + endpoints
    │   ├── database.py      # SQLAlchemy engine, session, Base, get_db()
    │   ├── models.py        # ORM models (Asset)
    │   └── schemas.py       # Pydantic schemas (AssetCreate, AssetRead)
    ├── lab.db               # SQLite file (gitignored)
    └── .venv/

**Design decisions:**

- **SQLAlchemy 2.0 syntax** (`Mapped[...]` + `mapped_column(...)`) instead of
  the legacy `Column(...)` style — this is what modern tutorials and docs use.
- **Separate `models.py` and `schemas.py`.** Models describe the *database*;
  schemas describe the *API contract*. Mixing them causes information
  disclosure (sensitive DB fields leaking through JSON responses).
- **`lifespan` context manager** instead of the deprecated `@app.on_event`.
  On startup it calls `Base.metadata.create_all(bind=engine)`.
- **`Depends(get_db)`** for session injection — each request opens a session
  and closes it in a `finally` block, even on exceptions.
- **`created_at` uses `lambda: datetime.now(timezone.utc)`** and not the
  bare function reference, otherwise all rows would share the same timestamp
  (Python evaluates the default only once).
- **Uvicorn command changed** from `main:app` to `app.main:app` because
  `main.py` moved into the `app/` package.
- **`db.refresh(asset)` after `commit()`** to fetch the DB-generated values
  (`id`, `created_at`) before returning the object — otherwise they would be
  missing from the response.

**Endpoints added:**

- `GET /api/assets` → returns the full list of assets, ordered by id.
- `POST /api/assets` → creates a new asset; returns `201 Created` with the
  row as it was stored.

**Automatic validation (Pydantic):**

- `hostname` shorter than 1 character → `422 Unprocessable Entity`
- The request never reaches the endpoint function. Validation happens before.

This is a defense-in-depth pattern: constraints live in one place (the schema)
and the API rejects invalid input automatically.

**Verification commands:**

    # empty list
    curl -s http://192.168.1.173:8000/api/assets

    # create
    curl -s -X POST http://192.168.1.173:8000/api/assets \
      -H "Content-Type: application/json" \
      -d '{"hostname":"ubuntu-lab","ip_address":"192.168.1.173","os":"Ubuntu 24.04"}'

    # list again — the new row must be present
    curl -s http://192.168.1.173:8000/api/assets

    # invalid payload — expect 422
    curl -s -X POST http://192.168.1.173:8000/api/assets \
      -H "Content-Type: application/json" \
      -d '{"hostname":"","ip_address":"10.0.0.1","os":"Kali"}'

**Next step:**

- Connect the Vue frontend to the assets endpoints (list + create form).
- Then: deployment on Ubuntu with systemd/supervisor.


---

## Session 4 — Frontend ↔ Assets API + network safety decision

**Goal:** give the user a real interface to interact with the assets API —
list existing assets and create new ones — without refreshing the page.

**Frontend structure (new components):**

    frontend/src/
    ├── App.vue                    # orchestrator: state + data fetching
    ├── config.js                  # central API endpoints (new)
    └── components/
        ├── AssetList.vue          # table of assets (presentational)
        └── AssetForm.vue          # form to create assets

**Component communication:**

    App.vue  ──── props (assets) ─────▶  AssetList.vue
       ▲
       │
       └──── event (created) ─────────  AssetForm.vue

- **props** flow parent → child (data).
- **emits** flow child → parent (events).
- `<script setup>` makes imported components available in the template
  without explicit registration.

**Vue concepts used:**

- `ref()` for reactive state (arrays, strings, booleans).
- `onMounted()` to run a function when the component appears — used to load
  the initial asset list.
- `v-model` for two-way binding on form inputs.
- `v-for` + `:key` to render the table rows.
- `v-if` / `v-else-if` / `v-else` to handle three UI states: loading, error,
  success.
- `defineProps` / `defineEmits` macros for component contracts.
- `@submit.prevent` to stop the browser's default form submit (which would
  reload the whole page and break the SPA).
- `:disabled="loading"` to prevent double-submits while a request is in flight.
- `:assets="assets"` — the colon means the value is a JavaScript expression,
  not a literal string.

**Centralized configuration (`frontend/src/config.js`):**

Before this session, the backend URL `http://192.168.1.173:8000` was hardcoded
in two places. Now it lives in one file:

    export const API_BASE_URL = 'http://192.168.1.173:8000'
    export const API_ENDPOINTS = {
      assets: `${API_BASE_URL}/api/assets`,
      hello:  `${API_BASE_URL}/api/hello`,
    }

Same idea on the backend: `ALLOWED_ORIGINS` is now a single constant at the
top of `app/main.py`, referenced by the CORS middleware.

**Why this matters:** the lab will eventually be re-provisioned on a
Host-only network with different IPs. Centralizing the base URL means only
one line changes when the network changes.

**Network safety decision (IMPORTANT):**

Both VMs currently run in VMware **Bridged** mode, meaning they can reach
each other AND the home network / Internet through the same router that the
host uses. This is convenient during development (apt, pip, npm, git push)
but is **not safe** for offensive-security testing.

**Commitment, until the lab is properly isolated:**

- Only non-offensive commands are run from the Kali VM:
  `curl`, `ping`, `apt`, `npm`, `git`, `nmap` **only against `127.0.0.1`
  or against our own IPs** (`192.168.1.173`, `192.168.1.125`).
- No subnet scans, brute-force, exploits, or sniffing.
- The home network must never see traffic that looks like an attack.

**Planned fix (Session 5 or later):** migrate the lab to a VMware
**Host-only** network with two network adapters per VM:

    eth0  — Host-only (VMnet1) — lab traffic (isolated)
    eth1  — NAT                — Internet, only when needed

This will be a milestone for the portfolio, and will be documented in the
hardening section.

**Verification commands:**

    # List assets from the terminal (should match what the browser shows)
    curl -s http://192.168.1.173:8000/api/assets

    # Create an asset via curl
    curl -s -X POST http://192.168.1.173:8000/api/assets \
      -H "Content-Type: application/json" \
      -d '{"hostname":"kali-attacker","ip_address":"192.168.1.125","os":"Kali Linux"}'

**Result:** Vue shows the asset table updated live after each form submit —
no manual refresh needed. Full-stack round-trip confirmed. ✅

**Next step:**

- Migrate the lab to an isolated Host-only network (security).
- Then: deployment on Ubuntu with systemd/supervisor.


---

## Scope note — what this repository does and does not cover

This repository documents **the Secure Fullstack Lab application** — its code,
its deployment, its security hardening. It does **not** document the home
network it runs on.

Reasons:

- The project runs on **isolated virtual networks** inside VMware. The home
  network is never touched by this application.
- The lab is **not a 24/7 service** — it is started when working on it, and
  stopped afterwards.
- Documenting personal infrastructure here would mix concerns and expose
  details that do not belong in a project repository.

Anything network-specific to the lab (VM names, internal segments, firewall
rules) is deliberately **out of scope** for this repository. The code only
knows what it needs to know: the URLs and origins declared in
`frontend/src/config.js` and `ALLOWED_ORIGINS` in `backend/app/main.py`.

**Operational policy during offensive-security testing** (future sessions):

- The lab's outbound route to the Internet will be disabled while running
  scans or exploits.
- Only the isolated lab networks are reachable during those tests.
- No traffic that resembles an attack leaves the lab under any circumstance.


---

## Session 5 — systemd services + repository scope

**Goal:** stop losing the FastAPI and Vite processes whenever a terminal is
closed. Replace manual `nohup ... &` with proper service management.

**Why systemd, not nohup:**

`nohup` keeps a process alive across terminal sessions, but it does not:
- restart the process if it crashes,
- start it at boot,
- give a single command to start/stop/restart,
- centralize logs.

systemd does all of the above and is the standard service manager on modern
Linux. Learning it is a prerequisite for any real deployment.

**Two services created** in `/etc/systemd/system/`:

| Service                          | Runs                          | Port |
|----------------------------------|-------------------------------|------|
| `secure-fullstack-api.service`   | FastAPI (uvicorn)             | 8000 |
| `secure-fullstack-web.service`   | Vue (Vite dev server)         | 5173 |

**Copies kept in the repository** at `deploy/systemd/` so the configuration
is versioned. The real files still live in `/etc/systemd/system/` — the ones
in the repo are backups/installers for other machines (see
`deploy/README.md`).

**Key design decisions in the service files:**

- **`User=filipe` / `Group=filipe`** — the services run as a normal user,
  never as root. The API only needs a high port and read access to project
  files; no privilege escalation required.
- **`WorkingDirectory=`** — set to the backend/frontend folder. Critically,
  this makes the relative `sqlite:///./lab.db` resolve to the right file.
- **`ExecStart=` uses absolute paths** — systemd does not expand `~` or
  environment variables from the user's shell. For the frontend we call
  `node_modules/.bin/vite` directly instead of `npm run dev`, so systemd
  tracks a single process instead of two (npm → node → vite).
- **`Restart=on-failure` + `RestartSec=3`** — the service restarts
  automatically if it crashes, but stays stopped if we stop it deliberately.
- **No `--reload` in production** — the service does not auto-reload on code
  changes. To apply changes: `sudo systemctl restart secure-fullstack-api`.
  This matches production behaviour and avoids the multi-process reloader.

**Verification — resilience test:**

Killed the API process with `kill -9`. systemd detected the failure and
restarted the service automatically within ~3 seconds, with a new PID. The
logs recorded the entire sequence:

    Failed with result 'signal'
    Scheduled restart job, restart counter is at 1
    Started secure-fullstack-api.service

**Result:** frontend and backend run as managed services, start on boot, and
recover automatically. No more "why did it stop again?".

**Scope decision — what this repository contains:**

The repository documents **the application** — code, deployment, hardening.
It does **not** document the home network. Reasons:

- The lab runs on isolated virtual networks (VMware LAN Segments behind an
  OPNsense VM router). The home network is never touched by this project.
- It is not a 24/7 service — it is started when working on it.
- Personal infrastructure details do not belong in a project repository.

Network-specific details of the lab (VM names, segments, firewall rules) are
deliberately out of scope. The code only knows what it needs: `config.js` on
the frontend, `ALLOWED_ORIGINS` in `backend/app/main.py`.

**Operational policy during offensive-security testing (future sessions):**
the lab's outbound route to the Internet will be disabled while running scans
or exploits. Nothing that resembles an attack leaves the lab.

**Next step:**

- Nginx as reverse proxy (replace the Vite dev server with a build + static
  serving; unify the app under a single port).
- Then: HTTPS in the lab, then hardening (SSH, UFW, Fail2Ban).


---

## Session 6 — Nginx as reverse proxy

**Goal:** unify the app behind a single port, remove the Vite dev server from
production, and eliminate CORS as a concern.

**Before:**

    Browser ──▶ :5173  (Vite dev server)
    Browser ──▶ :8000  (FastAPI)      ← cross-origin → CORS required

**After:**

    Browser ──▶ :80  (Nginx)
                        │
                        ├── /          → frontend/dist/  (static)
                        └── /api/*     → proxy → FastAPI :8000
                                                    │
                                                    ▼
                                                  SQLite

**Steps taken:**

1. Installed Nginx with `apt`. Ubuntu's default package enables it at boot
   via systemd automatically (`Created symlink .../nginx.service`).
2. Built the frontend for production with `npm run build`. Output:
   - `dist/index.html`
   - `dist/assets/index-<hash>.css`
   - `dist/assets/index-<hash>.js`
   The hash in filenames means the browser can cache them forever.
3. Created the site configuration in
   `/etc/nginx/sites-available/secure-fullstack`. It:
   - serves static files from `frontend/dist/`
   - proxies `/api/*` to `http://127.0.0.1:8000`
   - falls back to `index.html` for SPA routes (`try_files $uri $uri/ /index.html`)
   - uses dedicated logs (`secure-fullstack.access.log` and `.error.log`)
   - sets `X-Real-IP` and `X-Forwarded-For` so the API sees the real client IP
4. Enabled the site and disabled the default one:
   - `ln -s /etc/nginx/sites-available/secure-fullstack /etc/nginx/sites-enabled/`
   - `rm /etc/nginx/sites-enabled/default`
5. Validated with `nginx -t`, then reloaded (`systemctl reload nginx` — no
   downtime, unlike `restart`).
6. Changed `frontend/src/config.js` to use **relative paths**
   (`API_BASE_URL = ''`) so the frontend always talks to the same origin.
7. Added a `server.proxy` block to `vite.config.js` for local development
   (`/api` → `http://127.0.0.1:8000`), so `npm run dev` keeps working.
8. Removed `CORSMiddleware` from `backend/app/main.py`. Same origin now —
   CORS is no longer needed. Left a comment explaining the decision and when
   it would have to come back.
9. Stopped, disabled, and deleted `secure-fullstack-web.service`. The Vite
   dev server is no longer run as a service.
10. Versioned the Nginx config at `deploy/nginx/secure-fullstack`.

**Issue encountered:** Nginx returned `500 Internal Server Error` on first
try. Error log showed:

    stat() ".../dist/index.html" failed (13: Permission denied)

**Cause:** Ubuntu home directories are mode `drwxr-x---`. Nginx runs as
`www-data`, which is neither the owner nor in the owner's group — so it
cannot traverse `/home/filipe/`.

**Fix (temporary):**

    sudo chmod o+x /home/filipe

This grants traverse-only permission (not listing). It works, but is not the
production-correct approach. In a later hardening session, `dist/` will be
moved to `/var/www/secure-fullstack/` and this permission will be revoked.

**Issue encountered (second):** after configuring Nginx, the browser showed
`NetworkError`. The frontend build still contained the old hardcoded URL
(`http://192.168.1.173:8000`), because it had been built *before* editing
`config.js`.

**Lesson:** the `dist/` folder is a **build artefact**. Any change to the
frontend source requires `npm run build` before the browser will see it.
This is exactly why `dist/` is git-ignored — it is generated, not source.

**Key concepts learned:**

- **Reverse proxy** — Nginx is a single entry point that routes to different
  backends by path. Same-origin from the browser's perspective.
- **`proxy_set_header X-Real-IP` / `X-Forwarded-For`** — without these, the
  API sees every request as coming from `127.0.0.1`. With them, real client
  IPs are preserved for logs and auditing.
- **SPA fallback** — `try_files $uri $uri/ /index.html` is required for Vue
  Router to handle client-side URLs.
- **`nginx -t` before reload** — always validate config syntax before
  applying. A bad config with `restart` can take the site down.
- **Content-hashed assets** — Vite's `index-<hash>.js` filenames enable
  `expires 1y; immutable`, so repeat visits are instant.
- **`chmod o+x` on a directory** — grants traverse, not list. Different
  permission bit meaning than on files.

**Result:** one URL, one port, no CORS, faster frontend, everything managed
by systemd.

**Next step:**

- HTTPS in the lab environment (self-signed or internal CA, since there is
  no public domain).
- Then: hardening (SSH, UFW, Fail2Ban).


---

## Session 7 — HTTPS with an internal CA

**Goal:** serve the application over HTTPS with a certificate the lab trusts,
without depending on any public domain or paid CA.

**Why not Let's Encrypt:** Let's Encrypt requires proof of control over a
public domain (DNS-01 or HTTP-01 challenge). The lab runs on a private IP
(`192.168.1.173`) inside isolated virtual networks — no public domain, no
exposure to the internet. Let's Encrypt is not applicable here.

**Solution:** build our own internal Certificate Authority (CA), the same
approach used inside companies for internal services.

### PKI material created

All material lives **outside the repository**, at `~/pki/secure-fullstack-lab/`:

| File          | Purpose                                 | Secret? |
|---------------|-----------------------------------------|---------|
| `ca.key`      | CA private key (RSA 4096)               | YES     |
| `ca.crt`      | CA public certificate (self-signed, 10y)| no      |
| `server.key`  | Server private key (RSA 2048)           | YES     |
| `server.csr`  | Certificate signing request             | no      |
| `server.crt`  | Server certificate signed by the CA     | no      |
| `ca.srl`      | Serial counter maintained by OpenSSL    | no      |

The `.gitignore` was updated **before** creating these files, to ensure they
can never be committed by accident:

    *.key
    *.pem
    *.crt
    *.csr
    *.srl
    certs/
    pki/
    secrets/

**Rule:** if a file is a secret or a credential, the `.gitignore` must be
excluding it *before* the file is created.

### Commands used

1. CA private key:

        openssl genrsa -out ca.key 4096

2. CA self-signed certificate (10 years, no passphrase — lab environment):

        openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
          -out ca.crt \
          -subj "/C=PT/O=Secure Fullstack Lab/CN=Secure Fullstack Lab Root CA"

3. Server private key:

        openssl genrsa -out server.key 2048

4. Certificate signing request, with SAN (the important part):

        openssl req -new -key server.key -out server.csr \
          -subj "/C=PT/O=Secure Fullstack Lab/CN=192.168.1.173" \
          -addext "subjectAltName=IP:192.168.1.173,DNS:localhost,IP:127.0.0.1"

5. Sign the CSR with the CA:

        openssl x509 -req -in server.csr \
          -CA ca.crt -CAkey ca.key -CAcreateserial \
          -out server.crt -days 825 -sha256 \
          -copy_extensions copy

### Key concepts

- **CA = notary.** The CA signs certificates for others. Anyone who trusts
  the CA automatically trusts anything it signs.
- **A certificate is a public document.** It can be shared freely. Only the
  matching *private key* is secret.
- **Self-signed CA.** The CA's certificate is signed by itself — the trust
  is an act of faith. That is why the user must install the CA manually on
  each client (as we did on Ubuntu and Kali).
- **One key per purpose.** The CA has its own key (4096 bit); the server has
  a different one (2048 bit). If the server key leaks, only that certificate
  needs to be revoked — the CA stays intact.
- **SAN, not CN.** Modern browsers ignore the Common Name entirely for host
  verification. All identities must be listed in `subjectAltName`.
  Without SAN, the certificate is rejected with `ERR_CERT_COMMON_NAME_INVALID`.
- **`-copy_extensions copy`** is required in step 5. Without it, the SAN from
  the CSR is dropped when the certificate is signed, and the browser rejects.
- **TLS 1.2/1.3 only.** TLS 1.0 and 1.1 have known weaknesses and are
  deprecated. The config restricts to 1.2 and 1.3.

### Nginx configuration

- **HTTP (port 80)** is now a pure redirect:

        return 301 https://$host$request_uri;

  This preserves the path and query string. Nothing is served over plain
  HTTP anymore.

- **HTTPS (port 443)** serves the real site. It configures:
  - certificate + key paths (under `/etc/nginx/ssl/secure-fullstack/`)
  - `ssl_protocols TLSv1.2 TLSv1.3`
  - modern session cache settings

### Security headers added

All set with `always` so they also apply to error responses:

| Header                       | Purpose                                          |
|------------------------------|--------------------------------------------------|
| `Strict-Transport-Security`  | Force HTTPS for 1 year (browser-level)           |
| `X-Frame-Options: DENY`      | Prevent clickjacking (no embedding in iframes)   |
| `X-Content-Type-Options`     | Stop MIME-type sniffing (classic XSS vector)     |
| `Referrer-Policy`            | Limit Referer header sent to other sites         |
| `Permissions-Policy`         | Disable unused browser APIs (geo, mic, camera)   |
| `Content-Security-Policy`    | Restrict what the browser can load — last line   |
|                              | of defense against XSS                           |

The CSP is `default-src 'self'` across the board, with `object-src 'none'`
and `frame-ancestors 'none'`. This means: no external scripts, no inline
scripts, no external fonts, no embedding. It works because Vite outputs
external `.js` and `.css` files — no inline code.

### Installing the CA on clients

Ubuntu:

    sudo cp ca.crt /usr/local/share/ca-certificates/secure-fullstack-lab-ca.crt
    sudo update-ca-certificates

Kali: same commands. The file must end in `.crt` — otherwise
`update-ca-certificates` ignores it.

Firefox uses the system trust store via `p11-kit` on modern Linux
distributions, so installing the CA at the OS level was enough — no
separate NSS import required.

### Verification

- `curl -s https://192.168.1.173/` — works without `-k` (system trusts CA)
- Firefox on Kali: padlock shown, "Verified by: Secure Fullstack Lab",
  TLS 1.3, no warnings
- All 6 security headers present in responses
- HTTP requests get `301 Moved Permanently` with `Location: https://...`
- Full app works: list assets, create asset, table updates

### Future cleanup (hardening session)

The Nginx certificate files were copied to `/etc/nginx/ssl/secure-fullstack/`
with `root:root` ownership and `600` on the key. This is correct.

However, Nginx still serves static content from
`/home/filipe/secure-fullstack-lab/frontend/dist/`. That required granting
`o+x` on `/home/filipe/` earlier. In the hardening session, the built assets
will be moved to `/var/www/secure-fullstack/`, and the `o+x` permission will
be revoked.

**Next step:**

- SSH hardening (key-only authentication, disable password login, no root).
- UFW firewall.
- Fail2Ban.


---

## Session 8 — Server hardening (SSH, UFW, Fail2Ban)

**Goal:** apply the standard server-hardening measures that make a fresh
Ubuntu VM safe to leave running. Four independent layers, all tested.

### Layer 1 — SSH key-only authentication

Generated an SSH key on the Kali VM (client side):

    ssh-keygen -t ed25519 -C "kali-lab@192.168.1.125"

Copied the public key to the Ubuntu user:

    ssh-copy-id filipe@192.168.1.173

**Order matters here.** Key auth was tested *before* disabling passwords.
If we had disabled passwords first and the key was wrong, we would have been
locked out.

SSH hardening lives in a drop-in file:

    /etc/ssh/sshd_config.d/99-hardening.conf

Applied after the main config because of the `99-` prefix. Key settings:

- `PasswordAuthentication no` — passwords disabled
- `PermitRootLogin no` — root can never log in
- `AllowUsers filipe` — allowlist; everyone else is rejected before auth
- `KbdInteractiveAuthentication no` + `ChallengeResponseAuthentication no`
  — disables alternate interactive auth paths. This is a common gotcha:
  turning off `PasswordAuthentication` alone is not enough.
- `MaxAuthTries 3`, `LoginGraceTime 30` — reduce the attack window
- `AllowTcpForwarding no`, `AllowAgentForwarding no`, `X11Forwarding no`
  — disable features we do not use

**Validated before applying:**

    sudo sshd -t
    sudo systemctl restart ssh

**Verified:**

- `ssh filipe@192.168.1.173 hostname` → works, no password prompt
- `ssh -o PubkeyAuthentication=no filipe@192.168.1.173` →
  `Permission denied (publickey)` — passwords truly disabled

**Break-glass:** the VMware console always works, regardless of SSH config.
This was the safety net throughout.

### Layer 2 — UFW firewall

Defaults: `deny incoming`, `allow outgoing`.

Only three rules, and only the first restricts by source:

    sudo ufw allow from 192.168.1.125 to any port 22 proto tcp comment 'SSH from Kali'
    sudo ufw allow 80/tcp  comment 'HTTP (redirects to HTTPS)'
    sudo ufw allow 443/tcp comment 'HTTPS'

**Order matters:** the SSH rule was defined *before* `ufw enable`. Without
that rule in place, enabling the firewall would cut remote access instantly.

**Result:** FastAPI on `:8000` is no longer reachable from the network.
Verified from Kali:

    nc -zv -w 3 192.168.1.173 8000
    → Connection timed out

The timeout (rather than "Connection refused") confirms UFW is **dropping**
packets — the client gets no response at all. That is the intended
behaviour: an attacker learns nothing.

### Layer 3 — Fail2Ban

Bans IPs that fail SSH authentication repeatedly. Two important details:

**1. UFW as the ban backend.** The default Fail2Ban action uses raw
`iptables -I INPUT`, but UFW manages its own chains
(`ufw-user-input`). A raw iptables rule would be inserted *outside* the
chain UFW actually consults, so it would have no effect. Fix:

    banaction = ufw
    banaction_allports = ufw

This makes Fail2Ban call `ufw insert 1 deny from <IP>` — visible in
`ufw status`.

**2. Custom filter needed on OpenSSH 9.x+ (Ubuntu 24.04+).**
Discovered through debugging that:

- The authentication worker process is now `sshd-session`, **not** `sshd`.
  The packaged filter restricts to `_COMM=sshd` and misses every entry.
- Our test attempts produced `Connection closed by authenticating user ...`
  rather than `Failed password`. The packaged filter does not count that
  as a failure.

Created a custom filter at `/etc/fail2ban/filter.d/secure-sshd.conf`,
covering five patterns:

    Failed publickey for ...
    Failed password for ...
    Invalid user ...
    Connection closed by authenticating user ... [preauth]
    Connection closed by <HOST> port ... [preauth]

Also overrode `journalmatch` to match on `_SYSTEMD_UNIT=ssh.service` only
(dropping the `+ _COMM=sshd` restriction), so it captures both `sshd` and
`sshd-session` entries.

**Verified end-to-end:**

1. Generated 6 failed SSH attempts from Kali.
2. `fail2ban-client status sshd` showed:
   - `Total failed: 5`
   - `Currently banned: 1`
   - `Banned IP list: 192.168.1.125`
3. Confirmed the UFW rule list contained a temporary DENY for that IP.
4. Unbanned with `fail2ban-client set sshd unbanip 192.168.1.125`.
5. Confirmed the temporary rule was removed and the original allow rules
   remained intact.

### Lessons

- **Order of operations matters.** For both SSH and UFW, testing the new
  method *before* disabling the old one prevented lockout.
- **A ban blocks the whole IP, not just the port.** When Fail2Ban banned
  the Kali IP, all traffic from Kali (including HTTPS) was blocked. Worth
  knowing before it surprises you in a real environment.
- **Fail2Ban + UFW need explicit integration.** They do not cooperate by
  default. `banaction = ufw` is required.
- **OpenSSH 9.x+ renamed things.** `sshd-session` breaks the packaged
  Fail2Ban filter silently. `fail2ban-regex systemd-journal <filter>`
  against real logs is the fastest way to detect this.
- **`DROP` vs `REJECT`.** UFW's default is to drop packets silently.
  The client sees a timeout, not a refusal. Slower for legitimate users,
  but reveals nothing to a scanner.

### Files versioned in the repository

All hardening configs are copied into `deploy/hardening/` with a README
that explains how to reinstall them on a fresh machine.

**Next step:**

- CI/CD pipeline with GitHub Actions: lint, tests, security scanning
  (Bandit for SAST, dependency check for SCA).
- Then: DAST with OWASP ZAP against the running lab.
- Then: logging and monitoring (GoAccess for Nginx logs, Btop for system).
- Then: backups.
- Finally: documentation polish and the "What I Learned" section.


---

## Session 9 — Threat model (STRIDE)

**Goal:** produce a threat model of the system as if it were going into
production, before introducing authentication. The model informs the
design of every subsequent phase — auth, pipeline, vulnerability exercise,
GRC documents.

### Method

Chose **STRIDE** (Microsoft) because it maps cleanly to recognised
frameworks and because each category corresponds to a security property:

| Letter | Threat                | Violates         |
|--------|-----------------------|------------------|
| S      | Spoofing              | Authentication   |
| T      | Tampering             | Integrity        |
| R      | Repudiation           | Non-repudiation  |
| I      | Information disclosure| Confidentiality  |
| D      | Denial of service     | Availability     |
| E      | Elevation of privilege| Authorisation    |

### Scope principle

Established an explicit principle in §1.2 of the threat model: **the lab
simulates production**. Isolation, absence of public exposure, and
temporary lifetime are *not* accepted as reasons to lower the bar. Every
deferral must have a technical rationale, not an environmental excuse.
A table of accepted deferrals was added in §1.2.1, each with its specific
justification.

### Document structure

Created `docs/threat-model.md` with:

1. Scope and assumptions
2. System description (target state, with status markers)
3. Data classification (Public / Internal / Confidential / Restricted)
4. Assets (data, services, access, integrity-critical)
5. Trust boundaries (six boundaries, B1–B6, with controls per boundary)
6. Threat actors (T-01 to T-06)
7. STRIDE analysis
8. Regulatory obligations (planned)
9. Risk register (planned)
10. Open findings and gaps
11. Revision history

Every control in the document is tagged `[implemented]`, `[planned]`, or
`[gap]`. The gap list feeds the risk register.

### STRIDE analysis produced

Four components analysed in depth:

**7.1 Nginx** — 12 threats identified. Main gaps:
- `server_tokens off` not set (version disclosure)
- No rate limiting at the edge
- No slowloris mitigations

**7.2 FastAPI** — ~17 threats. Main gaps:
- No authentication (the biggest)
- No rate limiting on API endpoints
- No pagination on collection endpoints
- Verbose validation errors

Two threats confirmed as already mitigated:
- Mass assignment — Pydantic ignores undeclared fields
- SQL injection — SQLAlchemy parameterises by default

**7.4 SQLite** — smaller section by design. SQLite is not a network
service: it has no identity concept, no privilege model, and its security
depends entirely on file permissions and the process that opens it. Most
entries are `[gap]` or `[known limitation]`. This is expected.

**7.6 SSH** — the strongest boundary. Most controls `[implemented]`:
- Key-only authentication
- Root login disabled
- User allowlist
- LoginGraceTime, MaxAuthTries
- AllowTcpForwarding no, AllowAgentForwarding no
- Fail2Ban integrated with UFW

### Findings recorded

Four findings, tagged for the risk register:

| ID  | Finding                                              | Component |
|-----|------------------------------------------------------|-----------|
| #1  | FastAPI listens on `0.0.0.0:8000`                    | FastAPI   |
| #2  | Application runs as the human operator (`filipe`)    | Host      |
| #3  | No privilege separation (same root cause as #2)      | Host      |
| #4  | SSH sessions are not recorded                        | SSH       |

Findings #2 and #3 are the same problem described from two angles — will
be consolidated in the risk register.

### Cross-cutting insight: three levels of authorisation

While discussing IDOR, we identified that "authorisation" is not a single
control. There are three independent levels, and a system that implements
only the first is vulnerable to IDOR, and a system that implements only
the first two leaks sensitive fields:

| Level | Question                                          | Where enforced         |
|-------|---------------------------------------------------|------------------------|
| L1    | Can this subject call this endpoint?              | Auth dependency, RBAC  |
| L2    | Can this subject see this row?                    | Query filter (IDOR)    |
| L3    | Can this subject see this field of this row?      | Response schema        |

This is why SQLAlchemy models (`models.py`) and Pydantic schemas
(`schemas.py`) are separate: the schema is the mechanism for L3.

Recorded as §7.3 of the threat model.

### SSH key passphrase applied

As a partial mitigation for threat S4 (key theft), a passphrase was applied
to the Kali operator's private key:

    ssh-keygen -p -f ~/.ssh/id_ed25519

Verified: SSH now prompts for the passphrase on every new connection, and
authentication continues to work.

This closes the "key file exfiltrated" scenario but not the "session
already open" or "passphrase intercepted" scenarios.

### SSH certificates — deferred with rationale

Discussed implementing short-lived SSH certificates (8h–24h) issued by a
dedicated SSH CA. This is the correct long-term mitigation for S4 and is
used in large organisations. **Deferred**, for two reasons:

1. It would add a critical key (the SSH CA) to the same account that
   already holds the TLS CA key and `lab.db` ownership — making the
   privilege-collapse problem (Finding #3) worse, not better.
2. It pairs naturally with Ansible (Phase 9), where certificate issuance
   and rotation can be automated.

Recorded in §1.2.1 as an accepted deferral with a technical rationale.

### Concepts learned

- **Authentication vs authorisation** — different questions, different
  layers, different failures.
- **JWT** — a signed token; the signature is the only thing preventing
  payload tampering. `alg: none` and weak keys are the two most common
  failure modes.
- **IDOR** — a valid, well-formed request that returns another user's
  data. The most common authorisation bug in web applications.
- **Mass assignment** — a server that trusts the client to send only
  expected fields. Prevented by strict schemas.
- **RBAC** — roles, not individual permissions, assigned to users.
- **Rate limiting** — the difference between "server can handle load" and
  "server survives abuse".
- **Defense in depth in concrete terms** — UFW filters by origin;
  Fail2Ban filters by behaviour. Independent controls, covering different
  failure modes.
- **DROP vs REJECT** — UFW drops silently. The client sees a timeout, not
  a refusal. Fewer signals for a scanner, more time for the operator.

### Lessons

- **A threat model is a working document, not a checkbox.** Most entries
  produced an actionable follow-up item. The document drove the next phase
  rather than describing what was already done.
- **"Not applicable" is a valid result.** SQLite has no spoofing risk
  because it has no identity concept. Recording why something does *not*
  apply is as valuable as recording what does.
- **Deferrals must have a technical rationale.** "It's just a lab" is not
  one. "It depends on Finding #3 being fixed first" is.
- **Tools integrate badly by default.** The Fail2Ban/UFW interaction was
  the first example; the SSH CA and privilege separation is the second.
  Integration is a design task.
- **Passphrase on a key is not a session control.** It protects the file
  at rest, not the session. Understanding *what* a control protects is
  more important than knowing it exists.

### Files changed

- `docs/threat-model.md` — created (1088 lines)
- Kali SSH key — passphrase applied

**Next step:**

- Complete STRIDE analysis for remaining components: **PKI**, **GitHub**.
- Then produce the **risk register** (`docs/risk-register.md`) with
  likelihood, impact, severity, treatment, and residual risk for every
  finding.
- Then **Statement of Applicability** and **control mapping**.
- Then proceed to Phase 4 (authentication).


---

## Session 10 — Risk register

**Goal:** turn the findings from the threat model into a structured risk
register with classification, treatment decisions, and residual risk.

### Method

Chose the qualitative approach: **Risk = Likelihood × Impact**, both on a
1–5 scale.

| Product | Severity |
|---------|----------|
| 1–4     | Low      |
| 5–9     | Medium   |
| 10–16   | High     |
| 17–25   | Critical |

Treatment options recorded per risk: **mitigate / accept / transfer /
avoid**. Every mitigated risk gets a residual value — the risk that
remains after the control is applied. Residual is never zero; the point of
recording it is to show the treatment reduces the risk to an acceptable
level, not that it eliminates it.

### Structure of the register

The document has seven sections:

1. Purpose
2. Scoring method (this section, for reference by anyone reading later)
3. Active risks (R-01 to R-07)
4. Accepted risks and deferred best practices
5. Risk distribution (snapshot, updated as risks close)
6. Closed risks
7. Revision history

The **§4 structure is deliberate** — see below.

### Active risks

Seven risks were classified. Each references its origin in the threat
model:

| ID   | Risk                                              | Severity  |
|------|---------------------------------------------------|-----------|
| R-01 | FastAPI listens on all network interfaces         | High (12) |
| R-02 | No privilege separation (app runs as `filipe`)    | High (15) |
| R-03 | CA private key unencrypted on the running server  | High (15) |
| R-04 | GitHub account exposure                           | Low (4)   |
| R-05 | No rate limiting at any layer                     | Medium (9)|
| R-06 | SSH sessions are not recorded                     | Medium (6)|
| R-07 | No pagination on collection endpoints             | Medium (6)|

### Finding consolidation

Threat model findings #2 and #3 were consolidated into R-02. Both describe
the same underlying problem from two angles: the application runs with the
same privilege as the human operator. Keeping them separate would have
inflated the count without adding information. A single entry with a
combined treatment plan is more accurate.

### Two risks added beyond formal findings

The threat model listed rate limiting (Nginx §7.1 D1, FastAPI §7.2 D1) and
pagination (FastAPI §7.2 D2, SQLite §7.4 D2) as gaps, but they did not
become formal findings because they do not correspond to a single
component. They were promoted into the register as R-05 and R-07 because
they affect the system as a whole and have concrete treatment plans.

This is intentional: the register is not a mirror of the findings list. It
is a **working document** where items earn their place by having a real
impact and an actionable treatment.

### R-04 — the iterative classification

The R-04 classification changed three times during the session as the
controls and context were examined:

| Round | Likelihood | Impact | Severity  | Change                            |
|-------|------------|--------|-----------|-----------------------------------|
| 1     | 4          | 4      | High (16) | Initial: no 2FA, single password  |
| 2     | 3          | 4      | High (12) | Device verification via email counted as an implicit second factor |
| 3     | 2          | 2      | Low (4)   | Repository private during development; strong unique password; push notifications enabled |

**The number was produced by the discussion, not assumed at the start.**
Each iteration added a real control or a real context and the score
adjusted. This is how a risk register is supposed to evolve.

### §4 — Accepted risks and deferred best practices

The section was deliberately structured in two parts:

**§4.1 — Accepted risks.** Five risks identified in the threat model and
**explicitly accepted** without a planned control, each with a written
rationale. Examples: Nginx version disclosure, no `Host` header validation,
no certificate revocation infrastructure.

**§4.2 — Deferred best practices.** Ten recognised industry practices
**not applied** in this context, with the reason. Examples: external-disk
offline backup, HSM for the CA key, automatic credential rotation, WAF,
centralised SIEM, external penetration test, separation of duties.

**Why this second section matters.** A register that only lists what is
implemented fails the audit question *"why did you not implement X?"*.
Documenting what is deliberately **not done** — with rationale — is part
of the work. This is the same logic as the Statement of Applicability in
ISO 27001, where every control must be justified whether applied or not.

### Documents produced

- `docs/risk-register.md` — created (initial version, ~600 lines)

### Concepts learned

- **Risk is a product, not a feeling.** Likelihood × Impact forces
  discipline: you cannot call something "high" without answering both
  questions separately.
- **Residual is never zero.** Recording it makes the treatment measurable,
  and prevents the illusion of complete elimination.
- **Identification and classification are separate steps.** Doing them
  together produces bias — you tend to classify highly what was hard to
  find. The threat model identifies; the register classifies.
- **Consolidation is not simplification.** Two findings about the same
  root cause are one risk with two symptoms, not two risks.
- **Justifying non-implementation is a control.** Accepted risks and
  deferred best practices are not gaps — they are decisions, and they
  belong in the register with their reasoning.

### Next steps

- Write the password policy (`docs/password-policy.md`) — the two-speed
  rotation model decided in Session 11.
- Close R-01 by binding FastAPI to loopback.
- Continue the GRC layer with incident-response and control-mapping.


---

## Session 11 — Method discussions that shaped the password policy

This session was not a coding session. It was a series of debates about
security decisions, several of which changed the initial position. The
conclusions became `docs/password-policy.md`. This entry records the
reasoning, not just the outcome, because the reasoning is the part worth
preserving.

### Discussion 1 — Rotation of passwords

**Initial position:** classic rule — rotate every 30 days, never reuse.

**Counter-argument raised:** rotation on a fixed schedule was designed for
an era before password managers and MFA. Two problems emerged in practice:

- Users created predictable variants (`Filipe2025!` → `Filipe2026!`),
  reducing real entropy while satisfying the policy on paper.
- Operational cost: resets, helpdesk load, and coordination with dependent
  systems.

NIST SP 800-63B recommends against scheduled rotation in favour of
event-driven rotation, combined with length and MFA.

**Counter-counter-argument (from the operator):** with a password manager,
the first problem disappears — the manager generates a random replacement
with no correlation to the previous one. The user simply accepts it. The
second problem also shrinks, because rotation becomes a button press
rather than a support ticket.

This was a good argument. It moved the discussion from "rotation is bad"
to "rotation is context-dependent".

**Conclusion — the two-speed model.** Rotation is retained where the
credential is the only control, and removed where a second control (MFA)
already bounds the exposure window:

| Account type            | Rotation model     | Interval   |
|-------------------------|--------------------|------------|
| Human account with MFA  | Event-driven       | On event   |
| Human account without MFA | Scheduled        | 180 days   |
| Privileged account      | Scheduled + event  | 90 days    |
| Service account         | Scheduled + event  | 90 days    |

**Why this is better than either extreme.** "Rotate everything every 30
days" is expensive and produces predictable variants. "Rotate nothing"
leaves accounts without MFA exposed indefinitely. The two-speed model
matches the rotation to the actual risk: if there is no second factor,
time is the only limit; if there is a second factor, the limit is already
there.

### Discussion 2 — Separate administrative account

**Initial position:** the operator uses one account (`filipe`) with `sudo`
for everything.

**Alternative proposed:** split into three accounts:

- `filipe-admin` — privileged, used only when elevation is required
- `filipe-work` — daily use, no `sudo`
- `secure-app` — runs the application, no shell, no `sudo`

This is standard practice in production environments: the account used
for everyday work is not the account that can change the system.

**Decision — deferred, not rejected.** Implementing this now would mean:

- Re-mapping `lab.db` ownership
- Changing the systemd unit
- Adjusting Nginx static file permissions
- Re-testing everything

And the operator is still in the construction phase, where `sudo` is
needed constantly. The separation becomes meaningful when there is a
stable set of accounts and permissions to separate. Planned for **Phase 9
(configuration as code)**, where Ansible makes the migration scriptable
and testable.

This is recorded in the threat model (§1.2.1) as a deferral with a
technical rationale — not an environmental excuse.

### Discussion 3 — Repository visibility

**Position:** the repository is private during development and made public
only when complete.

**What this gives:**

- Time to complete pre-publication hygiene without pressure
- Reduced exposure while the code is still changing
- A single, explicit moment when the repository becomes visible

**What it does not give:**

- It does not make the account invisible. An attacker with account access
  can clone the private repository exactly as if it were public.
- It does not eliminate the impact of pre-publication exposure — the
  attacker still gains advance knowledge of the architecture.

**Consequence for the risk register.** R-04 was classified as **Low (4)**
during development. The reasoning: while the repository is private, the
worst case is that the attacker obtains a copy of code that will become
public anyway. The impact rises to 4 if the repository is published
without the planned controls (2FA, signed commits, branch protection).

### Discussion 4 — Notification as a detection control

**Position:** email notifications on push are configured, and the
notification address is delivered to the operator's mobile device.

**Why this matters.** A notification delivered only to the workstation is
limited: it works when the operator is at the workstation, and fails
otherwise. A notification delivered out-of-band — to a device the
operator carries — reduces the detection window from hours to minutes,
regardless of where the operator is.

**What it does not solve.** A notification is a detection control, not a
prevention control. Between the event and the operator's response, the
attacker acts. Any data already cloned cannot be un-cloned. The
notification reduces the *duration* of exposure, not the *fact* of it.

**Recorded in the risk register** as R-04.1, with the containment
procedure (R-04.2) alongside.

### Discussion 5 — Backup strategy

**Position:** the 3-2-1 rule — 3 copies, 2 media types, 1 off-site.

Applied to this project:

| Copy | Location                          | Medium               |
|------|-----------------------------------|----------------------|
| 1    | Ubuntu VM (working copy)          | Internal disk        |
| 2    | GitHub (canonical remote)         | Cloud (Microsoft)    |
| 3    | External disk (planned)           | Removable, offline   |

**Why the external copy must be kept disconnected.** A drive that is
permanently connected is reachable by ransomware and by any process
running with the operator's privileges. A drive that is disconnected is
not reachable. The cost is that backups are manual; the benefit is that
the copy is genuinely independent.

**What backup protects against, and what it does not.**

| Threat                          | Backup helps? |
|---------------------------------|---------------|
| Accidental deletion             | Yes           |
| Disk corruption                 | Yes           |
| Ransomware (if disconnected)    | Yes           |
| **Attacker has cloned the repo**| **No**        |
| **History rewritten remotely**  | Yes (local copy preserves prior state) |

**Recorded as DP-01** in the risk register (§4.2), planned for **Phase
10 (backup and restore)**.

### Concepts learned

- **A control is not a checkbox.** "Rotate every 30 days" is a rule. "Rotate
  when the credential is the only control, otherwise rely on MFA" is a
  decision. The second is defensible; the first is not.
- **The right answer depends on the context.** Rotation is not bad or good
  in itself. Its value depends on what other controls exist. A policy that
  ignores this produces either false security or unnecessary friction.
- **Detection and prevention are different.** A notification is not a
  firewall. A firewall is not a notification. Both are needed; neither
  substitutes the other.
- **Backup is a copy, not a defence.** Backup protects against loss.
  It does not protect against exposure. Confusing the two produces a false
  sense of safety.
- **Documenting what is not done is part of the work.** Accepted risks and
  deferred best practices belong in the register. An auditor does not ask
  "did you do everything?" — they ask "did you decide about everything?".
- **Deferral needs a technical reason.** "It's a lab" is not a reason.
  "It depends on X being in place first" is.

### Documents produced

- `docs/password-policy.md` — created (~360 lines). Two-speed rotation
  model, technical requirements, lifecycle, exceptions, ISO 27001 mapping.

### Next steps

- Write `docs/incident-response.md` — the R-04.2 containment procedure is
  already a draft of one scenario.
- Write `docs/control-mapping.md` — OWASP Top 10 / ASVS, ISO 27001 Annex A,
  NIS2.
- Then move to code: Phase 4 (authentication) or Phase 6 (pipeline).

---

## Session 12 — IR-2 to IR-5, control mapping, and R-01 closure

**Goal:** complete the incident response playbook and the control mapping,
and close the first risk in the register.

### R-01 closed — first risk to complete the full cycle

R-01 (FastAPI listening on all interfaces) was identified in the threat
model (Finding #1) and classified in the risk register (High, 12). This
session it was treated, verified, and closed.

**Control implemented.** The systemd unit was changed:

    ExecStart=... uvicorn app.main:app --host 0.0.0.0 --port 8000

to:

    ExecStart=... uvicorn app.main:app --host 127.0.0.1 --port 8000

**Rationale.** Nginx runs on the same host and reaches the API through
loopback. Binding to `0.0.0.0` was never required. Binding to loopback
ensures that even if UFW is disabled, the API remains unreachable.

**Verification.**

1. `ss -ltnp | grep 8000` now shows `127.0.0.1:8000`, not `0.0.0.0:8000`.
2. The full application (`https://192.168.1.173`) continues to work from
   Kali — the Nginx → FastAPI path is unaffected.
3. From Kali: `nc -zv -w 3 192.168.1.173 8000` returns `Connection timed
   out`. It was already blocked by UFW; now it is also not listening.

**Commit:** `f0bd5ee` — "fix(api): bind FastAPI to loopback; close R-01
in risk register".

**Significance.** This is the first risk to go through the full cycle:
identified → classified → treated → verified → closed. Subsequent
closures follow the same format. The register's §6 (Closed risks) now has
its first entry.

### Incident response playbook — all five playbooks written

`docs/incident-response.md` was extended from IR-1 only (initial commit)
to all five scenarios:

| ID   | Scenario                                |
|------|-----------------------------------------|
| IR-1 | GitHub account compromise               |
| IR-2 | Ubuntu host compromise                  |
| IR-3 | CA private key compromise               |
| IR-4 | Physical loss or theft of the host laptop |
| IR-5 | Suspected data exfiltration of `lab.db` |

**Framework.** The playbook follows **NIST SP 800-61 Rev. 2**, with the
four standard phases: Preparation, Detection and Analysis, Containment /
Eradication / Recovery, and Post-Incident Activity.

**Structure of each playbook.** Trigger, Severity, Detection, Containment,
Eradication, Recovery, Evidence to preserve, Post-mortem requirements.
This ensures consistency between scenarios and makes the document easy to
navigate under pressure.

**Decisions worth noting.**

- **IR-2 (host compromise) does not recommend rebooting.** Rebooting
  destroys volatile evidence (running processes, network connections,
  memory). Containment is to isolate the network, not to reboot.
- **IR-2 and IR-5 both instruct to take a VMware snapshot** before any
  cleanup. This is the forensic evidence that cannot be recreated later.
- **IR-3 (CA key) always escalates to SEV-1**, because the CA is the root
  of trust and its compromise invalidates every certificate it signed.
- **IR-4 (physical loss) is honest about scope.** It states explicitly
  that software controls are irrelevant once the device is out of the
  operator's possession. The only effective control is OS-level disk
  encryption. The playbook exists to systematise the **digital** cleanup
  after the physical event.
- **IR-5 recognises** that the current data classification of `lab.db` is
  Internal (no personal data), and that severity rises once user accounts
  exist.

**Post-mortem template.** Included as a separate block in section 7.
Filled out after an incident, not during. Requires distinguishing
immediate cause, contributing causes, and root cause — a distinction that
prevents superficial learning.

**Single-operator limitation.** Section 4.1 documents that separation of
duties does not exist in this lab: the same person investigates, decides,
acts, and documents. Three risks are acknowledged (confirmation bias, no
second opinion, documentation skipped under pressure) with two
compensating measures (post-mortem written after the event; findings
recorded in the risk register so the "second opinion" comes from the
record).

**File size.** 667 lines. Committed in two steps: initial IR-1 (`3805b03`)
and the completion (`08b27bd`).

### Control mapping — connecting the project to frameworks

`docs/control-mapping.md` was created (428 lines, 181 table rows). It maps
the controls implemented in this project to four frameworks:

- **OWASP Top 10 — 2021** (all 10 categories)
- **OWASP ASVS 4.0.3** (14 chapters, target Level 2)
- **ISO/IEC 27001:2022 Annex A** (93 controls, assessed by section)
- **NIS2 Article 21(2)** (10 categories)

**Structure.** For each framework, a table lists the control or category,
its status (`[implemented]` / `[planned: N]` / `[partial]` / `[accepted]`
/ `[n/a]`), and where it is addressed. A final consolidated view aligns
all three frameworks per area of the project.

**Purpose of the mapping.** Three reasons:

1. **For the operator.** A control is only meaningful if it can be traced
   to a requirement. This prevents implementing for the sake of
   implementing.
2. **For an auditor.** Reviewing whether a framework is satisfied means
   reading what the system actually does. The mapping saves the effort of
   reverse-engineering.
3. **For a portfolio reviewer.** It shows the work is grounded in
   standards, not improvised.

**Every gap has a phase.** Section 7 lists the gaps surfaced by the
mapping and assigns each to a phase of the roadmap. None is unplanned.
This is what makes the mapping useful — it is not a status report, it is
the interface between the requirements and the roadmap.

**ASVS level.** The project targets **ASVS Level 2**, the standard for
applications handling sensitive data. Level 1 controls are largely
implemented. Level 2 controls are distributed across Phases 4 to 8.

**File size.** 428 lines. Commit `e41f58a`.

### Phase 5 (GRC) — completed

With the control mapping written, the entire GRC layer of the project is
complete:

| Document                 | Lines | Focus                                    |
|--------------------------|-------|------------------------------------------|
| `docs/threat-model.md`   | ~1200 | STRIDE analysis of six components        |
| `docs/risk-register.md`  | ~700  | Active, accepted, and deferred risks     |
| `docs/password-policy.md`| ~360  | Two-speed rotation model, ISO mapping    |
| `docs/incident-response.md` | ~667 | Five playbooks, NIST SP 800-61          |
| `docs/control-mapping.md`| ~428  | OWASP, ASVS, ISO 27001, NIS2             |

**Total: roughly 3,400 lines of GRC documentation**, all traceable to
recognised standards.

### Concepts learned

- **A risk closure is a moment, not a checkbox.** R-01 required
  identification, classification, treatment, verification, and
  documentation. The register recorded all five. This is the difference
  between "we fixed it" and "we can prove it was fixed".
- **A playbook is a sequence, not a checklist.** IR-2's first step is
  "do not reboot" — a negative action, not a positive one. Playbooks must
  encode what **not** to do, because instinct under pressure often points
  the wrong way.
- **Scope honesty is a control.** IR-4 explicitly states that physical
  loss is beyond software mitigation. Recognising the limits of what can
  be controlled is part of the analysis, not an admission of defeat.
- **Every gap has a phase.** The control mapping is only useful if the
  gaps it surfaces are assignable. A gap without an owner is a liability;
  a gap with a phase is a roadmap item.
- **Frameworks overlap.** OWASP Top 10 A02 and ISO 27001 A.8.24 both
  cover cryptographic failures. The value of mapping to multiple
  frameworks is not redundancy — it is triangulation. A control that
  satisfies three frameworks is more defensible than one that satisfies
  one.
- **Complex documents need heredocs.** When writing Markdown with nested
  code blocks, paste into `nano` fails silently. `cat > file << 'EOF'`
  writes the content literally without interpretation. Small lesson,
  large time saved.

### Commits this session

| Commit  | Description                                              |
|---------|----------------------------------------------------------|
| `f0bd5ee` | fix(api): bind FastAPI to loopback; close R-01 in risk register |
| `b9d83ba` | docs: add session 10 journal; restructure R-04 with detection and containment |
| `2d31f35` | docs: add password policy with two-speed rotation model  |
| `2fa681d` | docs(journal): register session 11 — method discussions and password policy |
| `3805b03` | docs: add incident response playbook (NIST SP 800-61) with IR-1 |
| `08b27bd` | docs(incident-response): complete IR-2 to IR-5           |
| `e41f58a` | docs: add control mapping (OWASP Top 10, ASVS, ISO 27001, NIS2) |

### Next step

With the GRC layer complete, the project moves to code:

- **Phase 4** — authentication, RBAC, rate limiting (2-3 sessions)
- **Phase 6** — CI/CD pipeline with SAST, SCA, secrets scanning (1-2 sessions)

The order is a design decision: authentication first, because Phase 7
(deliberate vulnerabilities) requires user accounts to exist for IDOR to
be demonstrable.

---

## Session 13 — Login endpoint with JWT

**Goal:** continue Phase 4 (authentication). This session adds the login
flow: the ability to exchange credentials for a signed token.

The session was planned for 1 hour and finished slightly over. Two commits
were produced: one for the user model and hashing (session 12 continuation),
one for the login endpoint itself.

### Part 1 — User model, hashing, and user creation

The foundation of authentication is storing user credentials safely.

**Model added: `User`** in `backend/app/models.py`.

| Field           | Type             | Notes                                    |
|-----------------|------------------|------------------------------------------|
| `id`            | Integer, PK      | Auto-increment                           |
| `email`         | String(254), UNIQUE, indexed | 254 = RFC 5321 maximum       |
| `password_hash` | String(255)      | Argon2id hash (~95 chars typical)        |
| `role`          | String(20)       | `user` or `admin`                        |
| `is_active`     | Boolean          | Deactivation instead of deletion         |
| `created_at`    | DateTime (UTC)   | Same pattern as `Asset`                  |

**Design decisions:**

- **`role` as a string, not an Enum.** Adding a role to an Enum requires a
  migration. A string with a `Literal["user", "admin"]` in the Pydantic
  schema gives the same validation without the coupling to the database.
- **`is_active` instead of deleting users.** Preserves history for audit
  and non-repudiation. Login checks it; a deactivated user cannot
  authenticate.
- **UNIQUE constraint at the database level, not only in the application.**
  The application returns a clean 409 if the email exists; the database
  constraint is the last line of defence against race conditions.

**Hashing module created: `backend/app/security.py`.**

Contains `hash_password()` and `verify_password()` using `argon2-cffi`.

**Why argon2id and not bcrypt.** Both are acceptable per OWASP. Argon2id
is memory-hard: each hash requires 64 MB of RAM and 3 iterations. GPUs
cannot parallelise this easily because they lack the memory bandwidth to
run hundreds of concurrent hashes. bcrypt is CPU-bound, and a modern GPU
can test far more bcrypt hashes per second than argon2id hashes.

The default parameters (`m=65536, t=3, p=4`) are above the OWASP minimum.
In a production system they would be tuned so a single hash takes
~250-500 ms on the target hardware.

**Uniform error handling in `verify_password`.** The function catches
`VerifyMismatchError`, `VerificationError`, and `InvalidHashError`, and
returns `False` in all cases. Without this, a corrupted hash in the
database would raise an exception, the endpoint would return 500, and an
attacker would learn something about the state of that account. The three
failure cases are indistinguishable from the outside — which is the
point.

**Endpoint `POST /api/users`.** Currently unauthenticated, with an
explicit note in the docstring that this is temporary — once RBAC is in
place, the endpoint is restricted to `admin` role.

### Part 2 — Login endpoint with JWT

**Library chosen: `PyJWT`** over `python-jose`. The latter has been slow
to address CVEs and has lost mindshare. `PyJWT 2.15.1` is the standard.

**JWT secret handling.** The secret is:

- Generated on first startup with `secrets.token_urlsafe(64)` — 64 bytes
  of cryptographic randomness, encoded to URL-safe base64.
- Stored in `backend/.jwt_secret` with permissions `0600`.
- Added to `.gitignore` **before** the file was created.
- Loaded once, at module import, and cached in `_JWT_SECRET`.

**Why a persistent file and not in-memory generation.** If the secret
were regenerated on every restart, every previously issued token would
become invalid — technically fine, but it forces re-login on every service
restart and does not reflect production practice. In a real deployment the
secret comes from an environment variable injected by the deploy system.

**The critical security detail — `algorithms=["HS256"]` explicit.**

`jwt.decode()` is called with the algorithm list **explicitly**:

    jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])

Without this argument, PyJWT would accept any algorithm declared in the
token's own header. That enables the `alg: none` class of attacks
(CVE-2015-9235 and variants), where an attacker crafts a token with no
signature and a header claiming no algorithm is used, and the server
accepts it as valid.

The fix is one keyword argument. The bug has been exploited in the wild.
This is worth remembering for any interview question about JWT security.

**Token payload.**

    {
      "sub": "1",            # user id as string (RFC 7519)
      "role": "admin",       # embedded so downstream checks avoid DB hit
      "iat": 1791318462,     # issued at
      "exp": 1791319354      # expires at
    }

**Access token lifetime: 15 minutes.** JWTs cannot be revoked before
expiry. The standard mitigation is to make expiry short. A refresh token
mechanism (planned for the next session) allows longer sessions without
long-lived access tokens.

**Endpoint `POST /api/auth/login`.**

- Accepts `LoginRequest` (email + password)
- Returns `TokenResponse` (`access_token`, `token_type="bearer"`)
- On failure returns 401 with `detail: "Invalid email or password."`

**User enumeration prevention.** The same message is returned for:

- Email does not exist
- Password is wrong
- User exists but is inactive (`is_active=False`)

This prevents an attacker from probing the API with a list of candidate
emails and learning which ones are valid accounts. The behaviour was
verified explicitly with two `curl` calls — one with a valid email and
wrong password, another with a non-existent email. Both returned the same
response.

### Verification performed

1. Created user `filipe@example.com` with role `admin` and a 33-character
   password. Response was 201 with the user object, and no
   `password_hash` field.
2. Confirmed in the database that `password_hash` begins with
   `$argon2id$v=19$m=65536,t=3,p=4$...`. This confirms the algorithm and
   parameters are what the code requested.
3. Tried to create the same email again → 409 Conflict with a clear
   message.
4. Tried to create a user with a password of 5 characters → 422 from
   Pydantic before the endpoint ran.
5. Logged in with correct credentials → 200 with a JWT.
6. Decoded the payload of the issued token → confirmed `sub`, `role`,
   `iat`, `exp` and a 15-minute lifetime (900 seconds).
7. Logged in with wrong password → 401, `Invalid email or password.`
8. Logged in with non-existent email → 401, **same message**.

### Concepts learned

- **`EmailStr` is stricter than it looks.** It rejects `.local` because
  `.local` is an RFC 6762 reserved domain for mDNS, not a valid email
  domain. `example.com` is the only reserved domain that passes. This was
  a useful surprise during testing — the validation is genuine.
- **Argon2id has parameters that matter.** Reading a hash like
  `$argon2id$v=19$m=65536,t=3,p=4$...` and knowing what each segment means
  is a skill. `m` (memory), `t` (iterations), `p` (parallelism) determine
  the cost to an attacker.
- **JWT is signed, not encrypted.** Anyone can read the payload. Do not
  put secrets in it. The signature only proves it has not been altered.
- **The `algorithms` argument is not optional.** Passing it explicitly is
  the difference between a safe implementation and a vulnerable one.
- **Uniform error messages are a control.** Returning the same 401 for
  three different failure cases is not laziness — it is prevention of
  user enumeration.
- **Secrets belong in files that are gitignored, not in code.** The
  `.gitignore` entry was added *before* the file was created, so there was
  no window where the secret could have been accidentally committed.

### Files changed

- `backend/app/models.py` — added `User` model
- `backend/app/schemas.py` — added `UserCreate`, `UserRead`,
  `LoginRequest`, `TokenResponse`
- `backend/app/security.py` — created (argon2id hashing, JWT creation and
  validation)
- `backend/app/main.py` — added `POST /api/users` and `POST /api/auth/login`
- `backend/requirements.txt` — created, pinned to installed versions
- `.gitignore` — added `.jwt_secret`

### Commits this session

| Commit  | Description                                              |
|---------|----------------------------------------------------------|
| `68c7865` | feat(auth): add User model, argon2 hashing, and user creation endpoint |
| `60708fc` | feat(auth): add login endpoint with JWT access token     |

### Next step

Phase 4, session 3:

- Dependency `get_current_user` — extracts and validates the JWT from
  the `Authorization: Bearer <token>` header
- Protect the asset endpoints behind authentication
- Endpoint `GET /api/users/me` — first authenticated endpoint
- Role-based access control (RBAC) — `admin` vs `user` on a subset of
  endpoints
- Rate limiting at the Nginx level for `/api/auth/login`
- End-to-end tests covering the login → token → protected endpoint flow

---

## Session 14 — Authorization, RBAC, and rate limiting

**Goal:** complete the authentication flow by adding authorisation. Login
existed but nothing used it. This session makes the token useful: endpoints
now require it, and some require a specific role.

The session also closes R-05 (rate limiting) in the risk register and
updates the threat model to reflect the state of Phase 4.

### What was added

**`backend/app/dependencies.py`** — a new module containing the FastAPI
dependencies used across endpoints.

Why a separate file instead of placing them in `security.py` or `main.py`:

- `security.py` contains cryptographic primitives and knows nothing about
  FastAPI. `get_current_user` uses `Depends`, `HTTPBearer`, and
  `HTTPException` — FastAPI concepts. Mixing them would couple
  cryptography to the framework.
- `main.py` contains endpoints. Dependencies are not endpoints. Putting
  them there bloats the entry point and hides the reusable pieces.

Two dependencies:

**`get_current_user`**

    def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
        db: Session = Depends(get_db),
    ) -> models.User:
        ...

Steps performed on every authenticated request:

1. Extract the Bearer token from the `Authorization` header.
2. Decode and validate the JWT (signature, expiration).
3. Read the user id from the token subject.
4. Fetch the user from the database.
5. Reject if the user does not exist or is inactive.

Any failure raises HTTP 401 with a generic message. The client cannot
distinguish between missing header, invalid signature, expired token,
nonexistent user, or deactivated user.

**Design note — `HTTPBearer(auto_error=False)`.** By default, `HTTPBearer`
returns 403 when the `Authorization` header is absent. That is the wrong
code: missing credentials is 401, not 403 (RFC 7235). With
`auto_error=False` the scheme returns `None` and we raise 401 ourselves,
keeping the error shape consistent with the rest of the authentication
flow.

**Design note — `is_active` rechecked on every request.** The dependency
reads the user from the database on every authenticated call. This means
deactivating a user takes effect immediately: their existing token stops
working, even if it has not expired. This is the property that makes
deactivation a usable response to an incident. Without it, a deactivated
user would retain access for the remaining lifetime of their token (up to
15 minutes).

**`require_admin`**

    def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != "admin":
            raise HTTPException(status_code=403, ...)
        return user

Depends on `get_current_user`, so the full authentication flow runs first.
If the user is authenticated but does not have the admin role, the response
is **403 Forbidden**, not 401.

The distinction matters:

- **401** → the server does not know who the caller is
- **403** — the server knows, but the caller is not allowed

If 403 were returned as 401, the client would try to re-authenticate on
every attempt — an infinite loop, because the token was valid. 403 tells
the client to stop.

### Endpoints updated

| Endpoint                | Before          | After                          |
|-------------------------|-----------------|--------------------------------|
| `GET /`                 | Public          | Public (unchanged)             |
| `GET /api/hello`        | Public          | Public (unchanged)             |
| `GET /api/assets`       | Public          | Requires authentication        |
| `POST /api/assets`      | Public          | Requires authentication        |
| `POST /api/users`       | Public          | **Requires admin role**        |
| `GET /api/users/me`     | Did not exist   | **New — authenticated**        |
| `POST /api/auth/login`  | Public          | Public (unchanged)             |

### The bootstrap problem

In Session 1 (of the Phase 4 work), `POST /api/users` was unauthenticated
so that a first user could be created. That was the bootstrap mechanism.

This session **closes that door**: the endpoint now requires admin. The
comment in the docstring records the reasoning, because "why is this
endpoint suddenly locked?" is the sort of question that surfaces months
later:

    The bootstrap problem (creating the first admin when no user exists
    yet) was solved manually during development — the endpoint was
    unauthenticated for one session, and an admin user was created via
    curl. After that, the endpoint was locked down.

In a production system, the correct solution is not "leave it open for a
while". It is one of:

- A CLI command that creates the first admin: `python -m app.setup create-admin`
- An environment variable seeded on first boot (`ADMIN_EMAIL`, `ADMIN_PASSWORD`)
- A SQL seed file applied by the deployment process

This is recorded so the shortcut is explicit and not repeated by accident.

### Rate limiting at the Nginx edge

Two zones were added at the top of the Nginx site config, outside any
`server` block (this is required — zones are defined at the `http`
level):

    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m   rate=60r/m;

And two location blocks that use them:

    location = /api/auth/login {
        limit_req zone=login burst=3 nodelay;
        limit_req_status 429;
        ...
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;
        ...
    }

**Why two zones and not one.** A single rate cannot serve both purposes.
A rate tuned for login (5 per minute) breaks normal usage (listing assets,
fetching the user profile, submitting forms). A rate tuned for the
application (60 per minute) allows a script to attempt thousands of
password combinations per hour against the login endpoint. Differentiating
them is what makes the control fit for purpose.

**Why the exact-match location modifier.** `location = /api/auth/login`
uses the exact-match operator (`=`). Without it, the login endpoint would
fall under the prefix match `location /api/` and inherit the 60 r/m rate.
The Nginx matching algorithm prefers the more specific match — this is
what makes the stricter rate actually apply.

**Why `limit_req_status 429`.** Nginx's default when a rate limit is
exceeded is `503 Service Unavailable`. That code is misleading — the
service is available, the client is sending too many requests. `429 Too
Many Requests` is the correct code and is what was set.

**Verification.** The login endpoint was probed with a loop of 10
requests from a single client:

    for i in $(seq 1 10); do
      code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST https://192.168.1.173/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"teste@example.com","password":"..."}')
      echo "Pedido $i: $code"
    done

Observed result:

    Pedido 1: 401    ← auth rejected by FastAPI, Nginx allowed
    Pedido 2: 401
    Pedido 3: 401
    Pedido 4: 401
    Pedido 5: 429    ← Nginx refused (limit + burst exhausted)
    Pedido 6-10: 429

The transition from 401 to 429 confirms the mechanism is working. The
response body when the limit is hit is HTML (`<title>429 Too Many
Requests</title>`) rather than JSON — this is the signature that the
refusal came from Nginx, not from FastAPI. The request never reached the
backend.

**Known limitation — per-IP.** The limit is keyed by source IP. Behind
NAT, multiple users share the same IP and therefore the same bucket. In
the current lab each client has a distinct IP, so the limitation is
theoretical. In a production deployment, additional application-level
rate limiting keyed by authenticated user id would be necessary. This is
recorded in the risk register as a known limitation, not a gap.

### R-05 closed

With rate limiting implemented and verified, R-05 (No rate limiting at any
layer) was moved from §3 (Active risks) to §6 (Closed risks) in the risk
register. The entry includes:

- The configuration applied
- Why two zones were used
- The verification transcript
- The known limitation (per-IP)
- What was **not** implemented (`limit_conn_zone`), and why

R-05 is the second risk closed, after R-01. Both followed the same cycle:
identified → classified → treated → verified → documented with a commit
reference.

### Threat model updated

Fourteen status markers were updated in `docs/threat-model.md` following
the Phase 4 implementation.

| Component | Threat                                 | Before       | After         |
|-----------|----------------------------------------|--------------|---------------|
| Nginx     | I2 — open read endpoints               | planned      | implemented   |
| Nginx     | I3 — user enumeration at login         | planned      | implemented   |
| FastAPI   | S1 — no client identity                | planned      | implemented   |
| FastAPI   | S2 — `alg: none` JWT forgery           | planned      | implemented   |
| FastAPI   | S3 — weak JWT signing key              | planned      | implemented   |
| FastAPI   | S4 — JWT theft                         | planned      | **partial**   |
| FastAPI   | T4 — JWT payload tampering             | planned      | implemented   |
| FastAPI   | I1 — open read endpoints               | planned      | implemented   |
| FastAPI   | E2 — IDOR                              | planned      | **partial**   |
| FastAPI   | E3 — mass assignment on update         | planned      | implemented   |
| FastAPI   | E4 — JWT role tampering                | planned      | implemented   |

Two remain partially addressed:

- **S4 (JWT theft)** — short-lived access tokens (15 min) and a strict CSP
  are in place. Refresh tokens and `HttpOnly` cookies are not yet
  implemented. Marking this "implemented" would be dishonest.
- **E2 (IDOR)** — authentication exists, so the mechanism for IDOR now
  exists. The deliberate test case (introduce, detect, fix) is planned for
  Phase 7.

The distinction between `[implemented]` and `[partial]` is the whole point
of the status markers. A model that claims everything is done is a model
that is not being used.

### README updated

The roadmap was corrected to reflect actual progress:

- **Phase 4** — most items moved to `[x]`. Two remain open: JWT refresh
  tokens, and tests covering auth flows.
- **Phase 5** — six items moved to `[x]`; three remain open (Statement of
  Applicability, vulnerability and patch management policy, simulated
  incident exercise).

This is not cosmetic. The README previously said "Phase 5 is all pending"
when 75% of it had already been written. A roadmap that does not match
reality is worse than no roadmap — it is a false claim.

### Concepts learned

- **401 and 403 are different responses to different questions.** 401 asks
  "who are you?" — 403 says "I know who you are, you cannot do this". Code
  that returns 401 when the real problem is authorisation sends the client
  into a re-authentication loop that never resolves.
- **`HTTPBearer` defaults to 403.** The FastAPI security utilities do not
  always align with RFC 7235. Reading the defaults and overriding them
  where they are wrong is part of understanding the framework, not
  fighting it.
- **Deactivation has to be rechecked on every request.** A dependency that
  reads the user from the database on every call is slightly more
  expensive than one that trusts the JWT claims — and it is the difference
  between "deactivating a user takes effect now" and "takes effect in 15
  minutes". The cost is small; the property is important.
- **Rate limiting in Nginx requires attention to location matching.** The
  general rule (`location /api/`) will shadow a specific endpoint unless
  the specific one uses exact match (`location = ...`). Without that,
  setting a stricter rate on login looks correct in the config and has no
  effect.
- **A response's format tells you who produced it.** HTML from Nginx;
  JSON from FastAPI. Distinguishing them is the fastest way to know which
  layer acted.
- **Consistency between threat model, risk register, and README is the
  product.** Each of the three documents was updated in this session.
  Keeping them in sync is not bookkeeping; it is what makes them
  trustworthy as a set.

### Files changed

- `backend/app/dependencies.py` — created (`get_current_user`, `require_admin`)
- `backend/app/main.py` — endpoints protected; `GET /api/users/me` added;
  `POST /api/users` restricted to admin
- `deploy/nginx/secure-fullstack` — rate limiting zones and locations added
- `docs/risk-register.md` — R-05 closed; §5 distribution updated
- `docs/threat-model.md` — 14 status markers updated
- `README.md` — Phase 4 and Phase 5 progress corrected

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `d30a1ba` | feat(auth): add get_current_user and require_admin dependencies |
| `3a17149` | feat(nginx): add rate limiting for login and API endpoints      |
| `cde2df6` | docs(risk-register): close R-05 after rate limiting implementation |
| `cf5dcf3` | docs(threat-model): update status after Phase 4 implementation |
| `2d12eec` | docs(readme): reflect actual Phase 4 and Phase 5 progress       |

### Verification performed

1. Login as `filipe@example.com` (admin) → JWT issued, length 161.
2. Login as `joana@example.com` (user) → JWT issued, length 160.
3. `GET /api/users/me` **without** token → 401.
4. `GET /api/users/me` **with** `filipe`'s token → user object returned,
   no `password_hash` in the response.
5. `GET /api/assets` **without** token → 401.
6. `GET /api/assets` **with** `filipe`'s token → list of 3 assets.
7. `POST /api/users` **with** `filipe`'s token → 201, second user created
   (`joana@example.com`, role `user`).
8. `POST /api/users` **with** `joana`'s token → **403 Forbidden**, confirming
   the RBAC check.
9. Loop of 10 login attempts → transition from 401 to 429 at request 5,
   confirming rate limiting at the Nginx edge.

All nine passed as expected.

### Next step — remaining Phase 4 items

- **JWT refresh tokens.** A second token type with a longer lifetime,
  issued alongside the access token. Allows the client to obtain a new
  access token without asking the user to log in again, while keeping the
  access token lifetime short.
- **Tests covering auth flows.** At minimum: login success, login
  failure, protected endpoint without token (401), protected endpoint
  with wrong role (403), token expiry. These will run in the CI pipeline
  in Phase 6.

Only after these are complete does the Phase 4 checkbox in the README
close fully.

---

## Session 15 — Refresh tokens and Phase 5 closure

**Goal:** complete the last remaining item of Phase 4 (refresh tokens),
then close Phase 5 by producing the three remaining GRC documents:
Statement of Applicability, vulnerability management policy, and a
simulated incident exercise with post-mortem.

The session produced four documents and two code changes, and marked two
phases of the roadmap as complete.

### Part 1 — Refresh tokens

The access token issued by the login endpoint expires after 15 minutes.
This is correct for security: if it is stolen, its usefulness is limited.
It is inconvenient for the user, who would have to re-authenticate every
15 minutes.

Refresh tokens resolve that tension: a second, longer-lived token whose
only purpose is to obtain new access tokens without asking the user to
log in again.

**Design — type separation.** Both tokens are JWTs signed with the same
secret. Without a distinguishing claim, a stolen refresh token could be
presented as an access token, and the two-token model would collapse into
a single long-lived token. The solution is a `type` claim in the payload:

    {"sub": "1", "role": "admin", "type": "access",  "exp": ...}
    {"sub": "1", "role": "admin", "type": "refresh", "exp": ...}

- `get_current_user` calls `decode_token_of_type(..., "access")`
- `POST /api/auth/refresh` calls `decode_token_of_type(..., "refresh")`

A token with the wrong `type` is rejected even if the signature is valid.
This was verified with two explicit tests (access→refresh and
refresh→access), both returning 401.

**Refresh token rotation.** The `/api/auth/refresh` endpoint returns a
**new pair** of tokens, not just a new access token. This is the safer
behaviour: a leaked refresh token stops being valid the next time the
legitimate client refreshes. Without rotation, a stolen refresh token
remains usable for its full seven-day lifetime.

**Known limitation.** This implementation does not track revoked refresh
tokens. A leaked refresh token that has not been used since the leak
remains valid until the next legitimate refresh replaces it. A full
revocation scheme (a token version counter per user, or a persistent
denylist) is a future improvement, recorded in the docstring and in this
journal.

### Part 2 — Test suite

19 tests covering:

- Login success, wrong password, non-existent email, inactive user
- User enumeration prevention (same response for all three failure cases)
- Protected endpoints without token, with malformed token, with valid token
- `/api/users/me` returns the correct user, and does not expose the hash
- RBAC: admin can create users, regular user receives 403, anonymous 401
- Duplicate email returns 409
- Assets endpoint requires authentication
- Login returns both tokens
- Refresh works with a refresh token, and rejects an access token
- Protected endpoints reject a refresh token

The suite runs in ~20 seconds against a fresh in-memory database. The
real `lab.db` is never touched.

**Infrastructure.** `conftest.py` defines the fixtures:

- `db_session` — a fresh in-memory SQLite, created per test
- `client` — a `TestClient` with `get_db` overridden to use the test database
- `test_admin`, `test_user` — users with the corresponding roles
- `admin_token`, `user_token` — tokens obtained by calling the real login
  endpoint (not by minting tokens directly). Using the real endpoint means
  the fixtures exercise the same code path the client would, so a broken
  login flow fails tests immediately.

**Why `StaticPool`.** SQLite in-memory creates a distinct database per
connection. Without `StaticPool`, tables created on one connection would
not be visible to another, and every test would fail with "no such table".
The pool forces a single connection for the engine.

**Why the `with TestClient(app)` context.** Using `TestClient` without the
context manager does not trigger the FastAPI `lifespan`, so `create_all`
never runs and the tables do not exist. The context manager fixes that.

### Part 3 — Statement of Applicability

`docs/statement-of-applicability.md` (210 lines).

The SoA is a mandatory artefact under ISO 27001:2022 clause 6.1.3(d).
It records, for every control in Annex A:

- Whether the control is applicable
- Whether it is implemented, partial, or planned
- The justification for the applicability decision

**Format choice.** The full Annex A has 93 controls. Listing every one
individually would duplicate `docs/control-mapping.md`. Instead, the SoA
references the control-mapping for detail, and adds:

- Decision criteria for applicability
- Summary by theme (Organizational / People / Physical / Technological)
- Justification for the non-applicable categories
- Cross-references to the risk register for accepted/deferred controls

**Numbers.** 56 of 93 controls are applicable to this environment (~60%).
The 37 excluded are grouped by category, with rationale per category.

**Why "not applicable" is not a gap.** A control whose asset, role, or
activity does not exist in this environment is not missing — it is
irrelevant. The SoA records *why*, which is what an auditor checks.

### Part 4 — Vulnerability management policy

`docs/vulnerability-management-policy.md` (238 lines).

The policy defines how vulnerabilities in the lab's components are
identified, assessed, remediated, and verified.

**Key provisions:**

- **Multiple sources.** Dependabot, `pip-audit`, `npm audit`, Ubuntu
  Security Notices, Bandit, Trivy, GitHub Advisories. No single source
  is trusted to be complete.
- **Severity SLAs.** Critical 7 days, High 14 days, Medium 30 days, Low
  90 days. Measured from the moment the vulnerability is confirmed
  applicable, not from CVE publication.
- **Context adjustment.** CVSS is the starting point, not the conclusion.
  Severity may be adjusted up or down based on reachability, exposure,
  and environmental controls — with the rationale recorded. An
  adjustment without justification is itself a finding.
- **Exceptions are first-class.** A known, applicable, non-remediated
  vulnerability must be recorded with a reason, a compensating control,
  and a review date. Exceptions older than six months are treated as a
  finding in the annual review.
- **Verification of the policy itself.** Monthly metrics — number of
  open findings, number of exceptions, time since last OS update, time
  since last scan. A policy without metrics is a declaration of intent.

**Current state.** Only the manual sources are active. The automated
sources arrive in Phase 6 (CI/CD) and Phase 12 (Dependabot). This is
recorded explicitly — a document that claims capabilities that do not
exist is worse than one that records the truth.

### Part 5 — Simulated incident exercise

`docs/simulated-incident-exercise.md` (317 lines).

This is the first time a playbook from `docs/incident-response.md` was
**exercised** rather than written. A simulation was executed against the
lab, evidence was collected, and a full post-mortem was produced.

**Scenario.** A scripted sequence of 20 login attempts with wrong
passwords, sent from the Kali VM to `/api/auth/login`.

**Result.**

    401 401 401 401
    429 429 429 429 429 429 429 429 429 429
    429 429 429 429 429 429

Four requests reached the backend (401, rejected by FastAPI); sixteen
were refused at the Nginx edge (429). Total wall-clock time: three
seconds.

**What this proved:**

- **Prevention worked.** The rate limit was reached after four requests.
  The attacker is capped at a fixed cost per unit of time.
- **Resource cost was bounded.** Each backend login attempt consumes
  ~64 MB of RAM for argon2id hashing. Four attempts → ~256 MB. Twenty
  attempts → ~1.28 GB. The rate limiter reduces the resource cost of the
  attack by a factor of five.
- **User enumeration prevention held.** All four rejected attempts
  returned the same generic message, even though the attacker was
  targeting a non-existent account.
- **Logs told the whole story.** The complete attack can be reconstructed
  from the Nginx access log: origin IP, time window, request cadence,
  user-agent, and where each request was rejected (visible as the change
  in body size from 39 to 178 bytes).

**The finding — detection was not automatic.**

The attack was only noticed because the operator ran a manual `grep`
against the log afterwards. Nothing raised an alert when the rate limiter
began rejecting requests.

This is what the exercise exists to find. A prevention control that acts
silently is half a control: it stops the attack, but leaves the operator
blind to the fact that an attack occurred. In a production environment
with 24/7 operations, an unnoticed brute-force attempt is a serious
detection gap.

**Action items produced:**

1. Add an alert when the rate limiter begins rejecting requests
2. Configure structured logging (JSON) on the FastAPI side
3. Add threshold-based alerting for repeated failures per IP
4. (Future) Consider a full SIEM (already recorded as DP-05)

All three immediate items are scheduled for Phase 8.

**Cross-references updated.** The finding confirms what was already
recorded as R-06 (no audit trail) and in the control mapping for A.8.15
and A.8.16. No new risk entry was needed.

### Phase 5 — complete

With these three documents, Phase 5 is closed:

| Document                              | Lines | Purpose                              |
|---------------------------------------|-------|--------------------------------------|
| `docs/threat-model.md`                | ~1200 | STRIDE analysis of six components    |
| `docs/risk-register.md`               | ~800  | Active, closed, accepted, deferred   |
| `docs/password-policy.md`             | ~360  | Two-speed rotation, NIST-aligned     |
| `docs/incident-response.md`           | ~667  | Five playbooks, NIST SP 800-61       |
| `docs/control-mapping.md`             | ~428  | OWASP, ASVS, ISO 27001, NIS2         |
| `docs/statement-of-applicability.md`  | ~210  | ISO 27001 Annex A applicability      |
| `docs/vulnerability-management-policy.md` | ~238 | Identify, assess, remediate, verify |
| `docs/simulated-incident-exercise.md` | ~317  | Post-mortem with real evidence       |

**Total: roughly 4,200 lines of GRC documentation**, each traceable to a
recognised standard and cross-referenced to the others.

### Concepts learned

- **Type claims are what keep two-token models honest.** Without a `type`
  field in the payload, an access token and a refresh token are
  indistinguishable and the model collapses. The check is one line; the
  missing check is a complete rewrite of the security property.
- **Refresh rotation is safer than static refresh.** A refresh token that
  never changes remains usable for its full lifetime if leaked. Returning
  a new refresh token on every use bounds the exposure to the interval
  between the leak and the next legitimate refresh.
- **Test fixtures should exercise real code paths.** The `admin_token`
  fixture calls the login endpoint rather than minting a token directly.
  The cost is a few extra milliseconds; the benefit is that a broken
  login flow fails every test at once, instead of passing tests that
  silently bypass authentication.
- **Statement of Applicability is a decision document, not a checklist.**
  The value is not in the list of controls; it is in the justification
  for the ones that are not applied. An auditor reads the justifications.
- **A policy without metrics is a declaration of intent.** Adding
  measurement to the vulnerability policy is what makes it possible to
  tell, three months later, whether it is being followed.
- **Exercising a playbook is different from writing one.** The simulation
  revealed a detection gap that no amount of documentation would have
  surfaced. The evidence — the actual log — is what made the finding
  undeniable.
- **Controls that work silently leave the operator blind.** Rate limiting
  stops the attack; it does not announce it. Prevention and detection are
  separate requirements and neither substitutes the other.

### Files changed

- `backend/app/security.py` — refresh token creation and type-checked decode
- `backend/app/dependencies.py` — requires `type == "access"`
- `backend/app/schemas.py` — `TokenResponse.refresh_token`, `RefreshRequest`
- `backend/app/main.py` — login returns both tokens; `/api/auth/refresh` added
- `backend/tests/test_auth.py` — 4 new tests for refresh flow
- `backend/requirements.txt` — pytest and httpx added
- `backend/pytest.ini` — created
- `backend/tests/__init__.py`, `conftest.py` — created
- `docs/statement-of-applicability.md` — created
- `docs/vulnerability-management-policy.md` — created
- `docs/simulated-incident-exercise.md` — created
- `README.md` — Phases 4 and 5 marked complete

### Commits this session

| Commit  | Description                                                              |
|---------|--------------------------------------------------------------------------|
| `2f861b4` | test(auth): add pytest suite covering login, RBAC, and protected endpoints |
| `3fd3ea2` | feat(auth): add JWT refresh tokens with type separation                  |
| `8600392` | docs(readme): mark Phase 4 as complete                                   |
| `8fafa23` | docs(grc): add SoA, vulnerability management policy, and incident exercise |
| *(pending)* | docs(readme): mark Phase 5 as complete                                |

### Next step

Phase 6 — Security pipeline (CI/CD). A GitHub Actions workflow triggered
on push, running:

- **Lint:** ruff (Python), eslint (JS)
- **Tests:** pytest
- **SAST:** Bandit
- **SCA:** pip-audit, npm audit
- **Secrets scanning:** gitleaks
- **DAST:** OWASP ZAP baseline against the running lab

The report artefacts become evidence of the pipeline's behaviour, and
the pipeline itself becomes the mechanism that keeps the tests running.

The vulnerability management policy written in this session depends on
Phase 6 for its automated sources. The two phases are connected: the
policy describes what should happen, and the pipeline is what makes it
happen without manual intervention.

---

## Session 16 — CI/CD pipeline (Phase 6)

**Goal:** build a GitHub Actions pipeline that runs the tests and the
security scanners automatically on every push. Until this session, the
tests, the linters, and the scanners existed but only ran when invoked
manually. Phase 6 makes them run on their own.

The session produced four commits, added a `ruff.toml` configuration, and
discovered and fixed two issues along the way — the `B904` exception
chaining and the `host.docker.internal` resolution on Linux.

### Part 1 — Tools installed locally first

Before writing any workflow file, the tools were installed and run
manually in the development environment:

- `ruff` — Python linter and formatter
- `bandit` — SAST scanner for Python
- `pip-audit` — SCA scanner for Python dependencies

The principle: a workflow file describes *how* to run a set of tools. If
the tools have not been run manually first, the workflow becomes a place
to discover trivial errors (typos in commands, missing configuration) at
the cost of a 30-second round trip on the GitHub runner. Running locally
first means the workflow only needs to orchestrate tools that are already
known to work.

### Part 2 — Ruff configuration

The first `ruff check .` returned 20 findings. They fell into four
categories.

**Category 1 — `I001`, import ordering (5 files).** Cosmetic. Fixed
automatically by `ruff check --fix`.

**Category 2 — `F401`, unused import (1 file).** `pytest` was imported in
`test_auth.py` but never referenced. The tests use pytest fixtures by name
injection, not by direct call, so the import was redundant. Removed
automatically.

**Category 3 — `PIE790`, unnecessary `pass` (2 files).** `class Base` and
`class AssetCreate` had a `pass` after the docstring. In Python, a
docstring is a valid class body, so the `pass` was redundant. Removed
automatically.

**Category 4 — `B008`, function call in argument default (11 instances).**
This is the interesting one.

The rule exists because in generic Python, a default value is evaluated
**once**, when the module is imported, not on every call. So
`def f(x=now()):` would freeze `x` at the value of `now()` at import time.
Real bug.

**But FastAPI uses `Depends(...)` in argument defaults as its dependency
injection mechanism.** It is not a call that runs the dependency; it is a
marker object that FastAPI inspects. The B008 warning is a false positive
in this context.

Three options:

1. Add `# noqa: B008` on every one of the 11 endpoints. Works, but
   clutters the code and hides the fact that the rule exists.
2. Rewrite the endpoints to not use `Depends` in defaults. Would break
   FastAPI's design.
3. Configure ruff to recognise `fastapi.Depends` as an immutable call —
   telling the linter that this specific function is safe in a default
   argument.

Option 3 was chosen. The configuration lives in `backend/ruff.toml`:

    [lint.flake8-bugbear]
    extend-immutable-calls = ["fastapi.Depends", "fastapi.params.Depends"]

The choice is documented in the file itself, so that a future reader does
not have to guess why the rule was muted.

### Part 3 — B904, exception chaining

After the automatic fixes, four `B904` findings remained in three files.

The rule: when raising a new exception inside an `except` block, the
raise should specify `from err` or `from None`. Without it, Python keeps
the original exception in the chain, and any traceback handler will show:

    During handling of the above exception, another exception occurred:
    ValueError: invalid literal for int() with base 10: 'abc'

In our case, that `ValueError` was the result of `int(subject)` failing
because the JWT `sub` claim was not an integer. Exposing that to the
client is information leakage: the caller learns that the token subject
was non-numeric, which is more than they should know.

**`from None` was chosen for all four cases.** It suppresses the chained
exception. The client receives a uniform 401; the internal reason is not
in the response. This is the same principle as the generic login error
message used since Session 13 — multiple internal failure cases, one
external response.

The four corrected locations:

- `app/dependencies.py` — `int(subject)` in `get_current_user`
- `app/main.py` — `int(subject)` in the refresh endpoint
- `app/security.py` — two except clauses in `decode_token`

After the corrections, `ruff check .` returned `All checks passed!`.

### Part 4 — The GitHub Actions workflow

Created `.github/workflows/ci.yml`. The workflow triggers on:

- Push to `main`
- Pull request against `main`
- Manual invocation (`workflow_dispatch`)

**Six independent jobs:**

| Job             | Runs                                      | Typical duration |
|-----------------|-------------------------------------------|------------------|
| Lint (ruff)     | `ruff check .`                            | 9s               |
| Tests (pytest)  | `pytest` (19 tests)                       | 24s              |
| Security        | `bandit -r app/`, `pip-audit`             | 18s              |
| Secrets         | `gitleaks` against the full history       | 7s               |
| Frontend lint   | `npx eslint .`, `npx oxlint .`            | 12s              |
| DAST            | OWASP ZAP baseline against the live API   | 1m 32s           |

**Total run time: approximately 2 minutes.** The jobs run in parallel;
the total is the duration of the slowest job, not the sum.

**Why six jobs instead of one.** Each job is a separate status check in
the GitHub interface. A failure in one does not cancel the others. The
result is a matrix of pass/fail signals: an engineer looking at a PR sees
immediately whether the problem is in the code style, the tests, or the
security scan.

### Part 5 — The `--fix` problem in frontend lint

The `package.json` in the frontend defines:

    "lint": "run-s \"lint:*\"",
    "lint:oxlint": "oxlint . --fix",
    "lint:eslint": "eslint . --fix --cache",

The `--fix` flags modify the source files to correct problems
automatically. This is correct behaviour on a developer machine. It is
**wrong** in a CI runner for two reasons:

1. The runner is destroyed after the job. Any fix is lost, and the next
   run starts from the same broken state.
2. The job would pass, because the linter corrected the problem before
   reporting it. A failing state would be silently reported as success.

The workflow therefore calls the linters directly, without `--fix`:

    npx eslint .
    npx oxlint .

The choice is documented in a comment in the workflow file itself, so
that a future contributor who sees the `--fix` in `package.json` and
wonders why the CI does not use `npm run lint` finds the answer.

### Part 6 — Two attempts at DAST

The DAST job is structurally different from the others: it needs the
application running while the scan happens. The workflow therefore:

1. Installs the backend dependencies.
2. Starts the FastAPI server in the background with `nohup`.
3. Waits (up to 30 seconds) for the health check to succeed.
4. Runs the OWASP ZAP baseline scan.

**First attempt: failed after 1m22s.**

    Job spider failed to access URL http://host.docker.internal:8000
    check that it is valid : host.docker.internal: Name or service not known

`host.docker.internal` is a DNS name that Docker Desktop resolves on macOS
and Windows. **It does not exist on Linux** — and GitHub Actions runners
are Linux. The ZAP container could not reach the FastAPI server running on
the runner's host.

**Second attempt: corrected and passed.**

The container reaches the runner's host through the Docker bridge
gateway, which is `172.17.0.1` on a default installation. The target was
changed:

    target: "http://172.17.0.1:8000"

This IP is the same one that appears as `docker0` in the local VM (see
the first `ip addr` output in Session 1). The concept is identical —
the container and the host communicate through the same bridge, on the
same subnet.

The DAST job passed on the second attempt, in 1m32s.

**The `fail_action: false` setting is intentional.** On the first run of
a DAST scan against a new target, the ZAP baseline almost always reports
things — some are real, most are informational or false positives (the
scan hits FastAPI directly, without the Nginx security headers in the
path). Failing the build on the first scan would teach the team to ignore
the DAST result. Once the findings have been triaged and the rules tuned,
`fail_action` can be set to `true`.

### Part 7 — What the pipeline proves on every push

After Phase 6, the following is verified automatically on every commit to
`main`:

- **Code style:** Python and JavaScript conform to the project's rules.
- **Correctness:** all 19 authentication and authorisation tests pass.
- **Code security:** no patterns matching the Bandit rule set (eval,
  exec, weak hashes, `subprocess` with `shell=True`, etc.).
- **Dependency security:** no known CVEs in the Python dependency tree.
- **Secrets hygiene:** no secrets in the full Git history — verified with
  `gitleaks` scanning every commit.
- **Runtime behaviour:** the running API responds to the ZAP baseline
  scan without error.

**The last item — gitleaks — matters for a specific reason.** The
repository is currently private. It will eventually be made public as a
portfolio artefact. Running `gitleaks` over the full history means that
if a secret was ever committed, even in a commit that has since been
modified or removed, the pipeline would have flagged it now, before the
repository became visible.

### Part 8 — What the pipeline does NOT prove

Honesty about the pipeline's limits:

- **The DAST scan is a baseline.** It checks for common misconfigurations
  and obvious issues, not a full penetration test. Findings from ZAP do
  not replace manual review or a proper engagement.
- **The SAST scan (bandit) is pattern-based.** It does not understand
  application logic. A logically insecure function that uses safe
  primitives will not be flagged.
- **The SCA scan (pip-audit) depends on the vulnerability databases.**
  A CVE published today may not appear in the feed for hours or days.
- **The secrets scan (gitleaks) is signature-based.** A secret that does
  not match a known pattern — for example, a custom-format API key — may
  not be detected.
- **The pipeline runs on the diff, not on the deployment.** A green
  pipeline means the code passes the checks. It does not mean the
  deployed service is currently in the state the code describes.

These limits are the reason the pipeline is one layer among many, and
not the only control. They are documented so that the value of a green
checkmark is not overstated.

### Concepts learned

- **Default argument values are evaluated once.** This is the root of
  the B008 rule. In most Python code the rule is correct. In FastAPI it
  is a false positive because `Depends(...)` is a marker, not a call.
- **Configuring a linter is a design decision, not a workaround.** The
  `extend-immutable-calls` line in `ruff.toml` is documented and
  justified. It could have been silenced with 11 `# noqa` comments; that
  would have hidden the problem rather than resolved it.
- **Exception chaining is a form of information leakage.** The default
  behaviour of Python — showing the original exception alongside the
  replacement — is useful for debugging and dangerous for clients. The
  `from None` clause is one keyword that closes that leak.
- **`--fix` in CI masks failures.** A linter that corrects problems
  before reporting them turns a failure into a silent success on the
  runner. The correct behaviour is to report and let the developer fix.
- **The first CI run is a translation problem.** Every difference between
  the local environment and the runner's environment — Python version,
  Node version, available tools, DNS names — surfaces on the first run.
  This is not a defect of the pipeline; it is the pipeline doing its job
  of finding environmental assumptions.
- **DNS names are not portable.** `host.docker.internal` works on macOS
  and Windows because Docker Desktop implements it. On Linux it does
  not exist, and the correct substitute is the bridge gateway IP.
  Understanding the *why* makes the fix obvious; without the *why*, the
  fix looks like a magic number.
- **Six small jobs beat one large job.** Parallel execution, independent
  failure signals, and clear attribution of problems. The total runtime
  is the maximum of the individual durations, not the sum.

### Files changed

- `backend/ruff.toml` — created (linter configuration with justification)
- `.github/workflows/ci.yml` — created (6 jobs)
- `backend/app/database.py` — `pass` removed
- `backend/app/dependencies.py` — import order; `from None`
- `backend/app/main.py` — `from None`
- `backend/app/schemas.py` — import order; `pass` removed
- `backend/app/security.py` — import order; two `from None`
- `backend/tests/conftest.py` — import order
- `backend/tests/test_auth.py` — unused import removed; import order
- `backend/requirements.txt` — ruff, bandit, pip-audit added
- `README.md` — Phase 6 marked complete

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `c314a7c` | ci: add GitHub Actions workflow with lint, test, and security jobs |
| `f691f8e` | ci: add gitleaks and frontend lint jobs                         |
| `080818d` | ci: add DAST job with OWASP ZAP baseline scan                   |
| `e0329bc` | ci(zap): use docker bridge gateway instead of host.docker.internal |
| *(pending)* | docs(readme): mark Phase 6 as complete                       |
| *(pending)* | docs(journal): register session 16 — CI/CD pipeline           |

### Next step — Phase 7

Phase 7 is the deliberate vulnerability exercise. The plan:

1. Introduce a **SQL injection** in a controlled branch.
2. Introduce an **IDOR** in a controlled branch.
3. Introduce a **misconfigured CORS** in a controlled branch.
4. Let the pipeline (and manual testing) detect each one.
5. Fix each one in a separate commit.
6. Document the before/after with evidence.

The findings are **documented as intentional** at every step — the
branch name, the commit messages, and the eventual merge all state that
the vulnerability was introduced on purpose for the exercise. This is
the part of the repository that most differentiates it from a standard
portfolio: it is not just "we build a secure application", it is "we
understand how the application breaks, we can detect it, and we can
fix it".

The previous phases built the conditions for this exercise:

- Phase 4 introduced authentication and RBAC, without which IDOR has no
  meaning (there is no "another user's object" to access).
- Phase 6 introduced the pipeline, without which the detection would be
  entirely manual.
- Phase 5 introduced the risk register, without which the findings would
  not connect to a documented treatment plan.

Phase 7 uses all of it.

---

## Session 17 — Phase 7: SQL injection exercise

**Goal:** introduce a vulnerability deliberately, detect it with the
existing tools, fix it, and document the full cycle. This is the first of
three vulnerability exercises in Phase 7 (SQL injection, IDOR, CORS).

The session was the longest of the project so far and produced eight
commits across two pull requests. It also revealed two unrelated problems
in the pipeline that were fixed in passing, and one correction to an
earlier conclusion about what the SAST scanner detects.

### The approach

The exercise was executed as two pull requests, so that the Git history
records the cycle explicitly:

    PR #1 (branch vuln/sql-injection): introduce the vulnerability
    PR #2 (branch fix/sql-injection):  correct it

Both branches were merged to `main`. The vulnerability existed on `main`
for a few minutes, in an isolated lab, with the exercise documented in
the commit message and in the PR title. After the fix, `main` is clean
and the history shows the full sequence.

The decision to make the vulnerability visible in the main branch history
(rather than working on a scratch branch that never merges) was
deliberate: the value of the exercise is the historical record. A
reviewer looking at the commit log sees the introduction, the detection,
and the fix, in order.

### Part 1 — Introducing the vulnerability

A `search` query parameter was added to `GET /api/assets`, and the SQL
was built by string interpolation:

    query = text(
        f"SELECT id, hostname, ip_address, os, created_at "
        f"FROM assets WHERE hostname LIKE '%{search}%' ORDER BY id"
    )
    result = db.execute(query).fetchall()

This is the classic form of SQL injection. The `search` value becomes
part of the query text, so a value such as `' OR 1=1--` changes the SQL
that reaches the database engine.

The commit message (`4814a19`) states explicitly that this is an
exercise, references the threat model section that describes the threat,
and instructs not to copy the pattern.

### Part 2 — Confirming the vulnerability

Two `curl` requests were made against the endpoint, using a valid JWT:

**Control — normal behaviour:**

    GET /api/assets?search=ubuntu
    → 1 asset returned (ubuntu-lab)

**Attack — SQL injection:**

    GET /api/assets?search=%27%20OR%201%3D1--
    → 3 assets returned

The payload is `' OR 1=1--`. No hostname in the database contains this
string, so a functional filter would return zero rows. The fact that it
returned everything is the vulnerability.

The SQL that actually reached the engine was:

    SELECT ... FROM assets WHERE hostname LIKE '%' OR 1=1--%' ORDER BY id

`OR 1=1` is always true; `--` comments the remainder. The filter is
bypassed.

### Part 3 — What the CI pipeline did

The full picture only became clear after running the pipeline on the
vulnerable branch. Two commits in this session were corrections of
earlier statements that turned out to be wrong.

**Initial prediction (written in the first draft of `vuln-exercise-sqli.md`):**
the SAST scanner (bandit) would not detect the vulnerability, because
pattern-based scanners are known to miss certain classes of issue.

**Actual result, after the first CI run on the PR:**

| Job                    | Result     | Notes                                    |
|------------------------|------------|------------------------------------------|
| Lint (ruff)            | ❌ Failed  | Unrelated — see Part 4                   |
| Security (bandit)      | ❌ **Failed** | **B608 detected — the SQL injection**  |
| Secrets (gitleaks)     | ❌ Failed  | Unrelated — see Part 5                   |
| DAST (ZAP baseline)    | ✅ Passed  | Baseline scan does not perform injection tests |
| Frontend lint          | ✅ Passed  | —                                        |
| Tests (pytest)         | ✅ Passed  | No test covers the injection case         |

**Bandit fired.** The rule is B608 (`hardcoded_sql_expressions`),
severity Medium, confidence Low, CWE-89. The output pointed directly to
`app/main.py:104`.

This was a correction to the initial prediction, and it was recorded as
such. The document `vuln-exercise-sqli.md` was updated (commit `f18bc6d`)
to replace the incorrect statement with the actual result and a note
explaining that the earlier version had been written before the pipeline
ran.

**The lesson:** an assumption about a tool's behaviour is not a fact
until it is tested. The prediction was reasonable — pattern-based
scanners are known for this limitation — but in this specific case, for
this specific vulnerability, the scanner had the right rule and the rule
worked.

### Part 4 — Discovery: unpinned tool versions in CI

The ruff job failed with four `UP017` findings (`Convert to datetime.UTC
alias`). But the same ruff, on the same code, passed locally.

The cause: the workflow installed ruff with `pip install ruff` — without
a version pin. The runner downloaded the latest ruff, which had a newer
default rule set than the version installed locally. The same code
failed in one environment and passed in the other because the **tool**
was different, not the code.

**The immediate fix:** adapt the code to the newer rule (`datetime.UTC`
instead of `timezone.utc`) and pin the tool version in the workflow:

    run: pip install ruff==0.16.10
    run: pip install bandit==1.9.4 pip-audit==2.10.1

**The underlying principle:** any tool that runs in more than one
environment must have a pinned version. Without it, "the same code"
passes one day and fails the next, and the failure is attributed to the
wrong cause.

This is the same principle already applied in `requirements.txt` (fixed
versions) and in `package-lock.json` (fixed versions). It was simply
missing for the tools installed directly in the workflow.

The pinning was committed as `9340d90` and documented in the workflow
file itself, so that a future reader sees not only *what* version but
*why* it is pinned.

### Part 5 — Discovery: gitleaks permissions in pull requests

The gitleaks job failed after 6 seconds — too fast for a real scan of
the full history. The cause was not detection.

The `gitleaks/gitleaks-action` publishes findings in two ways: as a
comment on the pull request, and as SARIF in the repository's Security
tab. Both require permissions that are not granted by the default
`GITHUB_TOKEN`. Without those permissions, the action fails before it
runs the scan.

**The fix:** explicit permissions in the job:

    permissions:
      contents: read
      pull-requests: write
      security-events: write

Committed as `907de53`. After this change, the job runs in ~10 seconds
and reports cleanly.

**Why this matters beyond this exercise:** every GitHub Action that
writes back to the repository (comments, statuses, SARIF uploads) needs
explicit permissions. The default token is read-only. This is a change
from the earlier behaviour of GitHub and a common source of "the action
used to work and now it fails" issues.

### Part 6 — The fix

The corrected SQL uses parameter binding:

    query = text(
        "SELECT id, hostname, ip_address, os, created_at "
        "FROM assets WHERE hostname LIKE :search ORDER BY id"
    )
    result = db.execute(query, {"search": f"%{search}%"}).fetchall()

**The difference is the `:search` placeholder.** SQLAlchemy sends the
query and the value as two separate things to the database engine. The
engine treats the value as data, never as part of the query. A payload
that closes a string and appends SQL — `' OR 1=1--` — becomes a literal
string that no hostname contains.

The wildcards (`%`) are applied to the **value**, not the query. This
matters: the query is fixed and can be cached and audited; the value
changes per request and is not interpreted as code.

### Part 7 — Verification of the fix

Three checks were run against the fixed code, before the PR was merged:

**Check 1 — the attack payload:**

    GET /api/assets?search=%27%20OR%201%3D1--
    → []

An empty list. The payload is treated as a literal search string. The
injection is neutralised.

**Check 2 — normal functionality:**

    GET /api/assets?search=ubuntu
    → 1 asset (ubuntu-lab)

The fix did not break the normal case. A fix that removes the
vulnerability by removing the feature is not a fix.

**Check 3 — the SAST scanner on the fixed file:**

    $ bandit -r app/
    No issues identified.

Bandit no longer finds the vulnerability. Same tool, same command,
different code, different result.

The comparison between the two states of the same endpoint is the
proof:

| State             | Payload `' OR 1=1--`      | Result           |
|-------------------|----------------------------|------------------|
| Vulnerable        | `LIKE '%' OR 1=1--%'`      | All 3 assets     |
| Fixed             | `LIKE '%' OR 1=1--%'` as text | Empty list     |

Same payload. Different code. Opposite result. That is what a fix
demonstrates.

### Part 8 — The evidence document

`docs/vuln-exercise-sqli.md` was written and updated three times during
the session:

1. **Initial version** (`7853059`): described the vulnerability, the
   attack, the fix, and predicted that the CI would not detect it.
2. **Correction** (`f18bc6d`): replaced the incorrect prediction with
   the actual result (bandit did detect it) and a note explaining why
   the earlier version was wrong.
3. **Addition** (final commit of the session): added the pull request
   history and the outcome table.

The correction in step 2 is a deliberate choice. The document could have
been edited silently, and no one would have noticed. Instead, the
corrected version records the fact that the first version was wrong, and
why. This is what an audit trail looks like: not just the final state,
but the path to it.

### Part 9 — What the exercise demonstrated

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

### Concepts learned

- **A prediction about a tool is not a fact until tested.** The initial
  statement "bandit will not detect this" was reasonable and wrong. The
  correction is documented rather than hidden.
- **CI drift caused by unpinned versions is a real class of problem.**
  The same code passes and fails without changing. The fix is pinning,
  not debugging.
- **GitHub Actions writes need explicit permissions.** The default token
  is read-only. Every action that publishes results must declare what
  it needs.
- **The value of a fix is a change in observable behaviour.** "I changed
  the code" is not a fix. "The payload returned all rows before and
  returns none now" is a fix.
- **The history of the vulnerability is part of its value.** Merging the
  vulnerable code to `main` and then fixing it makes the log the
  artefact. A branch that never merges would leave no trace.
- **Corrections should be visible, not silent.** When a prediction turns
  out wrong, the correction is written down. Silently rewriting the
  document removes the evidence that the analysis was tested.
- **SAST has boundaries that are not bugs.** Bandit detected the SQL
  injection. It will not detect IDOR, because IDOR is a policy flaw, not
  a code pattern. The next exercise exists because the classes of
  vulnerability that pattern-based tools miss are the classes that need
  design and testing.

### Files changed

- `backend/app/main.py` — vulnerable version, then fixed version
- `docs/vuln-exercise-sqli.md` — created and updated three times
- `.github/workflows/ci.yml` — tool version pinning; gitleaks permissions
- `backend/app/models.py`, `backend/app/security.py` — `datetime.UTC`
  alias (adaptation to newer ruff rule)

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `4814a19` | vuln(sql-injection): introduce SQL injection in list_assets for Phase 7 exercise |
| `7853059` | docs(vuln): record SQL injection exercise — introduction, detection, and impact |
| `7dabb63` | fix(datetime): use datetime.UTC alias per ruff UP017            |
| `9340d90` | ci: pin tool versions to prevent silent drift between local and CI |
| `f18bc6d` | docs(vuln): correct the CI detection record — bandit did detect the SQL injection |
| `907de53` | ci(gitleaks): grant pull-requests and security-events permissions |
| `aae7677` | Merge pull request #1 (vulnerability)                          |
| `1edcd4b` | fix(sql-injection): replace string interpolation with parameter binding |
| `25525e5` | Merge pull request #2 (fix)                                    |

### Next step — Phase 7 continues

Two more exercises remain in Phase 7:

**IDOR** — a logic flaw, not a code pattern. The exercise will add an
ownership field to assets, create assets owned by two different users,
and demonstrate that user A can read user B's asset through the API.
Bandit will not detect this — the code is syntactically correct. The
detection will come from a test case and from manual review. This is the
complement to the SQL injection exercise: what pattern-based SAST cannot
find.

**CORS misconfiguration** — a configuration flaw. The exercise will
reintroduce a permissive CORS policy and demonstrate the impact, then
fix it. Detection is by header inspection and by the DAST scan.

After these two, the Phase 7 checklist is complete and Phase 8 (detection
and monitoring) follows.

---

## Session 18 — Phase 7: IDOR exercise

**Goal:** introduce a second vulnerability — this time a logic flaw
rather than a code pattern — and demonstrate that the CI pipeline cannot
detect it. The complement to the SQL injection exercise.

The session produced a complete cycle (PR #3 to introduce, PR #4 to fix)
and the first regression test in the project specifically written to
enforce an authorisation policy.

### The difference from the SQL injection exercise

The SQL injection exercise is what most people think of when they hear
"vulnerability". There is a visible flaw: a value is interpolated into a
query, and the shape of the bug is in the source code. A SAST scanner
with the right rule finds it. Bandit found it (B608).

IDOR is different. The code is syntactically correct. It uses the ORM
correctly. There is no interpolation, no `eval`, no `subprocess`, no
weak hash, no secret. What is missing is a **condition** — a check that
the code should have but does not. Nothing is wrong; something is absent.

This is the class of vulnerability that SAST cannot detect, and the
exercise is designed to demonstrate it side by side with the SQL
injection case.

### Part 1 — Setup

The exercise required a precondition that did not exist: assets needed
an owner.

The `Asset` model gained an `owner_id` column, a foreign key to
`users.id`, non-nullable and indexed. The existing rows (3 assets, all
belonging to the operator) were migrated with a manual `ALTER TABLE`
followed by an `UPDATE` to assign them to user 1.

**Why manual migration instead of Alembic.** SQLAlchemy's `create_all`
creates missing tables but does not alter existing ones. Introducing
Alembic for a single non-nullable column would have added a dependency
and a migration history for a schema that is still in flux. The manual
`ALTER TABLE` was sufficient and is documented here so that a future
reader knows why the migration is not in a migration folder.

The endpoints were updated accordingly:

- `list_assets` filters by `owner_id == current_user.id`
- `create_asset` sets `owner_id = current_user.id` from the token

The second is a defence against mass assignment: `owner_id` is
deliberately not a field in `AssetCreate`, so a client cannot create an
asset owned by another user.

A second user, Joana (role `user`), was created to provide a test
subject. Two users with separate inventories is the minimum setup for
the exercise — without it, there is no "another user's asset" to
attempt to access.

### Part 2 — Introducing the vulnerability

Branch `vuln/idor`, one new endpoint:

    @app.get("/api/assets/{asset_id}", response_model=AssetRead)
    def get_asset(
        asset_id: int,
        db: Session = Depends(get_db),
        _: models.User = Depends(get_current_user),
    ):
        asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
        if asset is None:
            raise HTTPException(404, "Asset not found.")
        return asset

The vulnerability is the **absence** of `models.Asset.owner_id ==
current_user.id` in the filter. The endpoint requires authentication —
a valid token is necessary to reach it. What is missing is the check on
the *object* once the caller is authenticated.

The docstring on the vulnerable endpoint states explicitly that this is
an exercise, why no scanner will detect it, and where the fix will be.
The commit message (`be911e6`) repeats the reasoning. Anyone reading the
history cannot mistake this for an accident.

### Part 3 — Confirming the vulnerability

Three requests, each producing the expected result:

| Request                            | User   | Asset | Result |
|------------------------------------|--------|-------|--------|
| `GET /api/assets/1` (Filipe's)     | Filipe | 1     | 200 — his asset |
| `GET /api/assets/4` (Joana's)      | Joana  | 4     | 200 — her asset |
| `GET /api/assets/1` (Filipe's)     | **Joana** | 1  | **200 — Filipe's asset** |

The third request is the vulnerability. Joana, whose token identifies
her as user 2, received asset 1 (owned by user 1). The `owner_id` field
in the response confirms the asset does not belong to her. The endpoint
returned it anyway.

### Part 4 — What the CI pipeline did

**Six green checks.**

The full pipeline ran against the vulnerable commit. No job failed. The
vulnerability was present and exploitable, and the CI was clean.

| Job                    | Result | Why it did not detect                 |
|------------------------|--------|---------------------------------------|
| Lint (ruff)            | ✅     | Valid Python                          |
| Tests (pytest)         | ✅     | No test covered cross-user access     |
| Security (bandit)      | ✅     | **No unsafe pattern to flag**         |
| Secrets (gitleaks)     | ✅     | No secret involved                    |
| Frontend lint          | ✅     | Backend-only change                   |
| DAST (ZAP baseline)    | ✅     | Baseline does not test authorisation  |

**The bandit result is the point of the exercise.** This is the same
scanner that detected the SQL injection exercise (B608). It did not
detect IDOR, and it could not: the vulnerable code has no string
interpolation, no `eval`, no `subprocess`, no weak hash, no secret. It
has a query missing a condition. There is no bandit rule for "missing
authorisation check" because that is not a syntactic property — it is a
property of the policy the code should implement.

**The route policy test also passed.** The test in
`tests/test_routes_policy.py` verifies that non-public endpoints require
authentication. The IDOR endpoint does require authentication. The test
is correct; it simply tests L1 (endpoint authentication) while the
vulnerability is at L2 (row-level authorisation). The two levels are
independent, and this exercise makes the distinction concrete.

### Part 5 — The fix

Branch `fix/idor`. Two changes to the endpoint:

**1. Add the ownership filter.**

    asset = (
        db.query(models.Asset)
        .filter(
            models.Asset.id == asset_id,
            models.Asset.owner_id == current_user.id,
        )
        .first()
    )

**2. Return 404, not 403, for another user's asset.**

This is a design decision worth explaining. 403 Forbidden would say
"this asset exists, but you cannot see it" — which confirms existence.
404 Not Found says "there is no asset with this id" — which is
technically false for the calling user, but indistinguishable from a
genuinely non-existent id. An attacker who enumerates ids learns only
which ids belong to them. They learn nothing about other users' assets.

The same principle as the generic login error message
(`"Invalid email or password."`) — multiple internal cases, one external
response — applied at the object level rather than the authentication
level.

### Part 6 — Verification

| Request                                | Before  | After   |
|----------------------------------------|---------|---------|
| Filipe → `/api/assets/1` (his)         | 200     | 200     |
| Joana  → `/api/assets/4` (hers)        | 200     | 200     |
| **Joana → `/api/assets/1` (Filipe's)** | **200** | **404** |

One row changed. That row is the fix. The two unchanged rows confirm the
fix did not break the legitimate cases.

### Part 7 — The regression test

`backend/tests/test_asset_authorization.py` — 6 tests:

1. `test_admin_can_read_own_asset` — 200
2. `test_user_can_read_own_asset` — 200
3. `test_user_cannot_read_admins_asset` — **404** ← the IDOR regression
4. `test_admin_cannot_read_users_asset` — 404 (the reverse direction)
5. `test_unauthenticated_cannot_read_any_asset` — 401
6. `test_list_shows_only_own_assets` — list filter verification

**Test 3 is the deliverable that matters most.** Without it, the fix
would be defensible only by the memory of the person who wrote it. With
it, the policy is enforceable by the pipeline: if the ownership filter
is removed in a future change, the test fails, and the CI blocks the
merge.

Test 4 asserts the reverse direction: an admin is not implicitly
authorised to read every asset. Admin status confers the ability to
manage *users*, not to bypass ownership. If a future policy change
grants admins cross-user access, this test fails, and the change becomes
deliberate rather than accidental.

### Concepts learned

- **The classes of vulnerability split by nature, not by severity.**
  SQL injection is a code pattern; IDOR is a logic flaw. The split
  determines what each defence layer can and cannot see. A scanner that
  is excellent against one class can be entirely blind to the other, and
  the difference is not "how good" the scanner is.
- **A missing check is not a syntax error.** Ruff checks syntax and
  style. Bandit checks patterns. Neither can see what is *not* there.
  The complement is a test that encodes the policy: "a user must not
  read another user's asset."
- **The three-level authorisation model is not academic.** L1
  (endpoint), L2 (row), L3 (field) are independent. The vulnerable
  commit implemented L1 and L3 correctly and missed L2. Any single-level
  check — including the route policy test — passes when the vulnerability
  is at a different level.
- **404 vs 403 is a design decision, not a detail.** 404 for "exists but
  not yours" denies the attacker the confirmation of existence. This
  applies the same principle as the generic login error, one level lower.
- **A regression test is the deliverable that turns a fix into a
  policy.** The fix corrects the behaviour today. The test enforces the
  policy tomorrow. Both are required.
- **Non-nullable columns require deliberate migration.** `create_all`
  does not alter existing tables. For a schema in flux, a manual
  `ALTER TABLE` is sufficient; the choice is documented so that a future
  reader does not look for a migration that does not exist.
- **An unhandled tool path is a hidden failure.** The ruff lint failed
  in the CI because the local run used `ruff check app/` while the CI
  used `ruff check .`. Same tool, same version, different scope. The
  fix is procedural: use the same command locally as in the CI.
- **The nature of the exercise determines the expected CI outcome.**
  For SQL injection, a clean CI would have been a failure of the SAST
  tool. For IDOR, a clean CI is the expected outcome and the point of
  the exercise. The same green checkmark means different things
  depending on what was being tested.

### Files changed

- `backend/app/models.py` — `owner_id` column added to `Asset`
- `backend/app/schemas.py` — `owner_id` exposed in `AssetRead`; not in
  `AssetCreate` (mass assignment prevention)
- `backend/app/main.py` — list and create scoped to owner; new
  `GET /api/assets/{id}` (vulnerable, then fixed)
- `backend/tests/test_asset_authorization.py` — created (6 tests)
- `backend/tests/test_routes_policy.py` — unused imports removed
- `docs/vuln-exercise-idor.md` — created (337 lines)

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `53d779d` | feat(assets): add owner scoping to assets (setup for IDOR exercise) |
| `be911e6` | vuln(idor): add GET /api/assets/{id} without ownership check   |
| `bffb2d5` | fix(lint): remove unused imports in test_routes_policy         |
| `6318675` | Merge pull request #3 (vulnerability)                          |
| `a75c437` | fix(idor): enforce ownership on GET /api/assets/{id}           |
| `b883c1d` | docs(vuln): record the IDOR exercise — introduction, detection, and fix |
| `9600eb5` | Merge pull request #4 (fix)                                    |

### Next step — Phase 7 continues

One more vulnerability exercise remains in Phase 7: **misconfigured
CORS**.

The exercise will:

1. Reintroduce a permissive CORS policy in the FastAPI application
   (the middleware was removed in Session 6 when Nginx unified the
   origin, but it can be added back in a permissive form for the
   exercise).
2. Demonstrate the impact with a browser-based attack: a page served
   from another origin (for example, the Kali VM on a different port)
   making an authenticated request to the lab API.
3. Detect it by inspecting the response headers and by observing the
   behaviour in the browser.
4. Fix it by removing the permissive policy or replacing it with an
   explicit allowlist of trusted origins.
5. Add a regression test that asserts the response does not include
   `Access-Control-Allow-Origin: *` (or, if a specific origin is
   allowed, that it is the expected one).

The CORS exercise is different from both previous exercises:

- **Not a code pattern** — the FastAPI middleware is syntactically
  correct. Ruff and bandit will pass.
- **Not a logic flaw in the traditional sense** — the code does exactly
  what it says; the *policy* is what is wrong.
- **Detectable by header inspection** — a simple `curl -I` reveals the
  presence of `Access-Control-Allow-Origin: *`. This is the first
  exercise where a *manual header check* is the primary detection, not
  an endpoint test.
- **Potentially detectable by the DAST scan** — the ZAP baseline may
  flag permissive CORS depending on configuration. If it does, this
  becomes the first Phase 7 exercise where the pipeline catches the
  vulnerability. Worth checking and documenting either way.

After the CORS exercise is closed, Phase 7 is complete and Phase 8
(detection and monitoring) begins. Phase 8 will implement the three
action items produced by the SQL injection exercise and by the simulated
incident exercise:

1. Structured logging in FastAPI (JSON).
2. Alert when the rate limiter begins rejecting requests.
3. Threshold-based alerting for repeated auth failures per IP.

---

## Session 19 — Phase 7: CORS exercise, and Phase 7 closure

**Goal:** complete the third and final vulnerability exercise in Phase 7
(misconfigured CORS), and close the phase.

The exercise followed the same two-PR pattern as the previous ones: PR #5
introduced the vulnerability, PR #6 fixed it. The technical work was
smaller than the previous two exercises; the value is in what the
comparison across the three exercises produces.

### Part 1 — The vulnerability

The `CORSMiddleware` was added with:

    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

The combination of the wildcard with credentials is the vulnerable
pattern. It is deceptive because Starlette does not send the literal `*`
when credentials are enabled — the browser would reject it. Starlette
echoes the specific origin of the request instead:

    access-control-allow-origin: https://evil.example.com
    access-control-allow-credentials: true

The response looks like a narrow allowlist. It is functionally a
wildcard. Recognising this requires knowing how the framework implements
the wildcard, not just what the configuration file says.

### Part 2 — Verification

Two `curl` requests were made, with different `Origin` headers:

- `Origin: https://example.com` → echoed in the response
- `Origin: https://evil.example.com` → echoed in the response

The two responses were structurally identical. The middleware does not
distinguish between the legitimate origin and the attacker origin. It
echoes whichever origin the caller supplies.

### Part 3 — Honest impact assessment

**In theory, the impact is severe.** A page on `evil.example.com` can
make authenticated cross-origin requests on behalf of a user currently
logged into the application. Every action the user can perform, the
attacker can perform.

**In this specific application, the impact is currently limited.** The
application uses JWT in the `Authorization` header, not cookies. The
browser does not attach the JWT automatically to cross-origin requests,
and JavaScript running on `evil.example.com` cannot read the JWT stored
on `192.168.1.173` — same-origin policy prevents it.

The vulnerability is **latent**: the configuration is wrong, but the
current architecture does not provide the conditions for exploitation.

**Why the finding still matters.** Three reasons recorded in the
document:

1. The configuration violates the principle of least privilege
   regardless of current exploitability.
2. The migration to `HttpOnly` cookies is planned in the password
   policy and threat model. The moment that migration happens, the CORS
   misconfiguration becomes immediately exploitable.
3. The subtlety — the response headers look restrictive but are not —
   is the specific lesson of the exercise.

This is the first exercise in Phase 7 where the impact assessment is not
"confirmed exploitable". The documentation states the limitation
explicitly, rather than overstating the finding. Overstating a finding
is a form of dishonesty that a reviewer notices.

### Part 4 — What the CI pipeline did

**Six green checks.** The full pipeline ran on the vulnerable commit
without a single failure.

| Job                 | Result | Why it did not detect                        |
|---------------------|--------|----------------------------------------------|
| ruff                | ✅     | Valid Python                                 |
| pytest              | ✅     | No test sent an `Origin` header              |
| bandit              | ✅     | Configuration, not a code pattern            |
| gitleaks            | ✅     | No secret                                    |
| Frontend lint       | ✅     | Backend-only change                          |
| **ZAP baseline**    | ✅     | **Sends no `Origin`, so the middleware never engages** |

**The ZAP result is worth its own note.** The baseline scan sends plain
HTTP requests. Without an `Origin` header, the CORS middleware does not
emit CORS headers, and the server looks the same with or without the
permissive configuration. A scanner configured to send `Origin` headers,
or an active scan, would have had a chance to detect this. The baseline
configuration in this pipeline did not.

### Part 5 — The fix

The `CORSMiddleware` was **removed entirely**, not replaced with a
restrictive allowlist.

**Why removal and not restriction.** The application is served by Nginx
on a single origin. Frontend and API share `https://192.168.1.173`.
There are no cross-origin requests. A restrictive allowlist would be
configuring for a scenario that does not exist — a form of security
theatre.

The source file now carries a comment explaining the decision, so that a
future developer who needs to add CORS finds the correct pattern
(explicit allowlist, no wildcards) rather than the convenient one.

### Part 6 — Verification of the fix

The same attack request, against the fixed version:

    $ curl -s -i -H "Origin: https://evil.example.com" \
        http://127.0.0.1:8000/api/hello
    HTTP/1.1 200 OK
    server: uvicorn
    content-type: application/json

No CORS headers of any kind. The browser now blocks the cross-origin
read at the same-origin policy level.

### Part 7 — The regression test

`tests/test_cors_policy.py` — 2 tests:

1. `test_api_does_not_emit_cors_headers` — a request with an `Origin`
   header must not receive CORS response headers.
2. `test_api_does_not_emit_cors_preflight_headers` — an OPTIONS request
   with `Access-Control-Request-Method` must not receive CORS headers.

Same pattern as the IDOR exercise: the test encodes the policy, so that
the CI blocks a future reintroduction of the permissive configuration.

### Part 8 — Phase 7 closure

The three exercises are now complete. The comparison is what makes the
phase valuable:

| Aspect                     | SQL Injection | IDOR       | CORS      |
|----------------------------|---------------|------------|-----------|
| Nature                     | Code pattern  | Logic flaw | Config    |
| **Detected by a scanner**  | ✅ bandit     | ❌         | ❌        |
| **CI turned red?**         | ✅            | ❌         | ❌        |
| Regression test added      | ❌ (gap)      | ✅ (6)     | ✅ (2)    |

**One of three was detected automatically. Two of three were not, and
neither could have been.** This is not a failure of the pipeline. It is
a demonstration of the boundary between what pattern-based scanners can
do and what requires human analysis, written tests, and policy
decisions.

The portfolio value is in the boundary. A repository that claims "the
code is secure" is not falsifiable. A repository that documents "here is
what the scanners catch, here is what they miss, and here is how the
gaps are covered" is a demonstration of engineering judgment.

### Part 9 — An honest gap in the phase

One inconsistency remains: the **SQL injection fix does not have a
regression test.** The IDOR and CORS fixes both added one. The SQL
injection fix was verified manually (the same attack returns an empty
list after the fix), but no automated test encodes the check.

This is recorded in `docs/vuln-exercise-cors.md` §9 as action item 1. It
is a small task — send the payload, assert the response — and it should
be completed before Phase 7 is formally closed in the README.

### Concepts learned

- **A framework's behaviour can be less obvious than its configuration
  suggests.** The `["*"]` + credentials pattern does not produce a
  literal wildcard in the response. It produces an echoed origin that
  looks like a specific allowlist. Knowing what the framework actually
  does requires reading the response, not just the source.
- **Latent risk is a valid category.** The configuration is wrong. The
  architecture makes it currently unexploitable. Both statements are
  true, and both belong in the analysis. Calling it "exploitable" would
  be dishonest; calling it "not a problem" would miss the point.
- **Configuration drift is a real class of finding.** CORS is a
  configuration, not code. Ruff and bandit do not check configuration.
  The defence is either a test that knows what the configuration should
  look like, or a manual review process that includes configuration
  files.
- **The scanner's coverage is determined by what it sends.** The ZAP
  baseline sends no `Origin` header, so the CORS middleware never
  engages. A scanner that sent `Origin` headers would have seen the
  response with CORS headers. The coverage is not a property of the
  scanner alone — it is a property of the scanner and the request it
  makes.
- **Three exercises produce a map, not a list.** A single exercise says
  "I can find and fix one thing". Three exercises, chosen to span
  distinct classes, say "I know the shape of the space — which defences
  cover which classes, and where the boundaries are".

### Files changed

- `backend/app/main.py` — CORS middleware added, then removed
- `backend/tests/test_cors_policy.py` — created (2 tests)
- `docs/vuln-exercise-cors.md` — created (344 lines)

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `6b4e975` | vuln(cors): add permissive CORS policy with credentials        |
| `8360c1f` | Merge pull request #5 (vulnerability)                          |
| `cb36f9c` | fix(cors): remove permissive CORS middleware                   |
| `520699a` | Merge pull request #6 (fix)                                    |

### Next step

Phase 7 is functionally complete pending one thing: the missing
regression test for the SQL injection fix.

The plan for the next session:

1. Add the SQL injection regression test (small, ~15 min).
2. Update the README to mark Phase 7 as complete (SQLi, IDOR, CORS).
3. Begin Phase 8 — detection and monitoring — which is the natural
   follow-up: the three exercises produced action items that require
   logging and alerting infrastructure to close.

Phase 8 will implement:

- Structured JSON logging in FastAPI (every request: timestamp, user,
  endpoint, status, duration).
- `auditd` with watches on `/etc/`, `~/secure-fullstack-lab/backend/`,
  and `~/pki/`.
- A correlation script that detects repeated auth failures.
- An alert when the rate limiter begins rejecting requests.

The last item is the one identified by the simulated incident exercise
(Session 15): the rate limiter blocks abuse silently, with no signal to
the operator. Phase 8 is where that gap closes.

---

## Session 20 — Phase 8: structured logging and auditd

**Goal:** start Phase 8 (detection and monitoring) by giving the system
two capabilities it did not have: machine-readable HTTP request logs,
and kernel-level audit of file and privilege events.

Both are prerequisites for the rest of the phase. The correlation script
(sub-task 4) will read the JSON logs. The alert for the rate limiter
(sub-task 5) will key off the status codes those logs record. Without
structured logs, both would require parsing free-form text.

### Part 1 — Structured JSON logging

The default Uvicorn access log emits one line of human-readable text per
request:

    INFO:     127.0.0.1:41440 - "GET /api/hello HTTP/1.1" 200 OK

This is readable, and useless for analysis. Filtering by user, computing
latency percentiles, or correlating a burst of 401s with a source IP all
require parsing a free-form string. A log aggregation tool cannot do it
without a schema.

**The replacement.** A `JsonFormatter` and a `RequestLoggingMiddleware`
in `app/logging_config.py` produce one JSON object per request:

    {"timestamp": "2026-10-14T20:29:56.367394+00:00", "level": "info",
     "logger": "app.request", "message": "http_request",
     "event": "http_request", "method": "GET", "path": "/api/hello",
     "query": "", "status_code": 200, "duration_ms": 16.69,
     "client_ip": "127.0.0.1", "user_agent": "curl/8.18.0",
     "user_id": null}

**Fields and their origin.**

| Field         | Origin                                              |
|---------------|-----------------------------------------------------|
| `timestamp`   | UTC, from `datetime.now(timezone.utc)`              |
| `level`       | logging level (lowercase)                           |
| `logger`      | the Python logger name (`app.request`)              |
| `event`       | fixed string, `http_request`, for filtering         |
| `method`      | request method                                      |
| `path`        | request path, no query string                        |
| `query`       | query string (separate field, not merged with path) |
| `status_code` | response status                                     |
| `duration_ms` | monotonic clock, `time.perf_counter()`              |
| `client_ip`   | `X-Real-IP` header (Nginx), else socket peer        |
| `user_agent`  | `User-Agent` header                                 |
| `user_id`     | from `request.state`, set by `get_current_user`     |

**Why `time.perf_counter()` and not `time.time()`.** The latter is
wall-clock and can jump backwards on NTP adjustment. `perf_counter()` is
monotonic and intended for measuring durations.

**The `user_id` integration.** The middleware runs **before** the
dependencies. At that point the JWT has not been validated and the
application does not yet know who the caller is. The dependency
`get_current_user` writes the resolved user to `request.state.user_id`
after validation, and the middleware reads that attribute after the
response is generated. This is the standard FastAPI pattern for
propagating request-scoped information between the dependency layer and
the middleware layer.

**The `client_ip` fallback.** Nginx sets `X-Real-IP` on every proxied
request. When the API is reached directly on the loopback interface
(during tests or local curl), the header is absent and the socket peer
address is used instead. Both cases are correct and both appear in the
log.

**Deliberately not logged.** Request body, response body, the
`Authorization` header. The JWT is never written to disk. This is
recorded in `docs/password-policy.md` §3. The decision is not a
limitation of the middleware — it is the middleware's design.

**Disabling the Uvicorn access log.** With the middleware emitting JSON,
the default Uvicorn log would duplicate every request. The systemd unit
gained `--no-access-log`. The startup lines (`Started server process`,
`Uvicorn running on ...`) remain — they are not per-request and are
useful as-is.

**A limitation that was discovered, not fixed.** The login endpoint
reports `"user_id": null` even on success. The reason is that the login
endpoint does not use `get_current_user` — it is a public endpoint that
authenticates the user inside its own body. The middleware therefore
never sees a `request.state.user_id`. To fix this, the login endpoint
would have to set `request.state.user_id = user.id` after
authentication. This is a small task, recorded here as an action item,
and not done in this session to keep the scope of the change contained.

### Part 2 — What the logs revealed about the application

Two requests, timed by the middleware, produced an observation that no
human review would have surfaced:

| Endpoint            | Duration |
|---------------------|----------|
| POST /api/auth/login| 1171 ms  |
| GET /api/users/me   | 49 ms    |
| GET /api/users/me   | 45 ms    |

The login endpoint is approximately 25× slower than the others. The
cause is argon2id: each login verifies a password hash, and each
verification consumes ~64 MB of RAM and 3 iterations of work. The cost
is intentional — it is the property that makes GPU-based cracking
expensive. A legitimate user pays it once. An attacker pays it for every
guess, which is why the rate limiter (Phase 4) matters as much as the
hash parameters (Phase 4).

**Structured logging turned this from an invisible property into a
recorded number.** A text log would show `200 OK` for both requests and
say nothing about the difference. This is the first concrete return on
the investment in logging — before any correlation script or alert is
written.

### Part 3 — auditd

**Why auditd, and not just the existing logs.** The system already had
three log sources:

| Source                 | What it records                       |
|------------------------|---------------------------------------|
| Nginx access log       | HTTP requests arriving at the edge    |
| FastAPI structured log | HTTP requests the application handles |
| journalctl             | Systemd service events                |

What none of them recorded: **changes to files on the host**. If an
attacker (or a mistake) modified `/etc/ssh/sshd_config`, deleted
`lab.db`, or read the CA private key, nothing in those three sources
would show it. The Nginx log would show the request that caused it (if
it went through the web), but not the filesystem consequence.

`auditd` fills the gap. It records kernel-level events: file opens,
writes, attribute changes, and `execve` calls with specific filters.

**The rules.** Fifteen rules, in
`/etc/audit/rules.d/secure-fullstack.rules`, versioned in
`deploy/hardening/audit-rules.conf`.

**Watch type: writes vs reads.**

For `/etc/` and its subdirectories, the rule is `-p wa` (write +
attribute). Reads are deliberately excluded: every process reads
`/etc/passwd`, `/etc/hosts`, and others; a read watch would produce
millions of events per hour with no security value. Writes are what
matter for integrity, and writes are rare.

For `~/pki/`, the rule is `-p rwa` (read, write, attribute). The
directory contains a handful of files, and the private key of the CA is
the single most critical asset in the lab. Any read of that directory is
worth knowing about, and the volume is manageable.

**The `privilege_escalation` rule.** This is a syscall-level rule, not a
file watch:

    -a always,exit -F arch=b64 -S execve -F euid=0 -F auid>=1000 -F auid!=-1 -k privilege_escalation

The filters:

- `arch=b64` — 64-bit syscalls only (the alternative would double every
  event on a 64-bit system)
- `execve` — process execution
- `euid=0` — the process runs as root
- `auid>=1000` — the original login user is a human (system users have
  lower IDs)
- `auid!=-1` — exclude processes with no login session (daemons,
  kernel threads)

The combination captures exactly: **a human escalated to root**. Not the
system's own root processes, not a boot process — a person running
`sudo`. This is the trigger any investigation starts from.

**The `failure` mode.** `auditctl -s` reports `failure 1`, which is not
an error — it is the mode. Three modes exist:

- `0` (silent) — audit failures are ignored
- `1` (printk) — audit failures are written to the kernel log (default)
- `2` (panic) — audit failures reboot the system

`printk` is the correct default. `panic` is used in high-assurance
environments where the alternative — losing an audit event — is worse
than a reboot. It carries its own risk: a flood of audit events could
cause an unintended reboot, which is a denial of service by design. For
this lab, `printk` is right.

### Part 4 — Verification

**Privilege escalation:**

    $ sudo ls /root
    $ sudo ausearch -k privilege_escalation --start recent

Produces records with `auid=1000`, `euid=0`, `comm="ls"`, and
`key="privilege_escalation"`. The audit trail now shows who escalated,
what they ran, and when.

**File write:**

    $ sudo touch /etc/ssh/sshd_config.d/test.txt
    $ sudo rm /etc/ssh/sshd_config.d/test.txt
    $ sudo ausearch -k ssh_config_d --start recent

Produces two records with `nametype=CREATE` and `nametype=DELETE`,
attributed to `auid=1000`, `comm="touch"` and `comm="rm"`. Any future
write to that directory — including an attempt to re-enable password
authentication in `sshd_config` — will leave the same trace.

### Concepts learned

- **Logs are a schema, not a message.** Text logs are for humans to
  read interactively. Structured logs are for machines to filter,
  aggregate, and correlate. The same event, in two formats, has very
  different value when something has to be found later.
- **The middleware / dependency boundary requires explicit
  propagation.** Middleware runs before dependencies, so it cannot read
  the JWT. `request.state` is the mechanism for the dependency layer to
  hand information back to the middleware after the response.
- **Measuring reveals what review does not.** The argon2id cost was
  known — it was chosen deliberately in Phase 4. Seeing it as a number
  (1171 ms against 49 ms) is different from knowing it in the abstract.
  A structured log turns "this should be slow" into "this is how slow,
  and it is in the right place".
- **Watches differentiate by direction, not only by path.** Reads and
  writes on the same file have very different meanings and very
  different volumes. Configuring reads on `/etc/` would flood the audit
  log; configuring only writes leaves the events that matter.
- **The failure mode of an audit system is a design decision.** `panic`
  is tempting for its strong guarantee. It is also a denial-of-service
  vector. `printk` is the compromise that keeps auditing useful without
  letting it take the system down.
- **What is *not* logged is part of the design.** The middleware does
  not capture request bodies or the `Authorization` header. This is
  stated in the code and in the policy, so that a future contributor
  who wants to "improve logging" finds the reasoning and does not
  silently reintroduce the leak.

### Files changed

- `backend/app/logging_config.py` — created
- `backend/app/dependencies.py` — writes `request.state.user_id`
- `backend/app/main.py` — calls `setup_logging()`, adds the middleware
- `deploy/systemd/secure-fullstack-api.service` — `--no-access-log`
- `deploy/hardening/audit-rules.conf` — created (15 rules)

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `9678a3b` | feat(logging): add structured JSON logging for HTTP requests   |
| `ba5d79f` | chore(deploy): sync systemd unit with --no-access-log flag     |
| `0bc409b` | feat(monitoring): add auditd rules for sensitive paths         |

### Next step — Phase 8 continues

Three sub-tasks remain in Phase 8:

1. **GoAccess** — a terminal dashboard for the Nginx access log,
   giving real-time visibility into HTTP traffic at the edge.
2. **Correlation script** — a script that reads the structured logs and
   surfaces patterns that are worth attention (repeated 401s per IP,
   bursts of 429s, requests from unexpected user agents). This is the
   script that closes the finding from the simulated incident exercise
   (Session 15): the rate limiter blocks abuse silently, and nothing
   reports when it acts.
3. **Alert when the rate limiter fires** — the specific case of the
   correlation script that watches for the transition from 200/401 to
   429 in the Nginx log, which is the signature of the rate limiter
   doing its job.

After these three, Phase 8 is complete and Phase 9 (configuration as
code with Ansible) begins.

---

## Session 21 — Phase 8: GoAccess, correlation check, and closing the loop

**Goal:** finish Phase 8 by delivering the two remaining detection
capabilities — a dashboard view of Nginx traffic, and an automatic alert
when the rate limiter fires.

### Part 1 — GoAccess

[GoAccess](https://goaccess.io/) parses the Nginx access log and produces
a self-contained HTML report: visitor hosts, requested files, status
codes, user agents, bandwidth.

**The first attempt failed, and the failure was informative.** Running
GoAccess against the log produced output of `{0} @ {0/s}` and no visible
progress. The assumption was that the tool had not parsed the file. The
`ls` on the output file contradicted this: the report had been generated,
with a size of ~720 KB. The `{0}` in the terminal was a cosmetic detail
of the counters, not a sign of failure.

**The lesson.** A tool that produces output on stdout is not necessarily
reporting its state accurately. Verifying the artefacts (the generated
files) is more reliable than reading the progress line.

**Why the report is not served.** Two reasons, both valid:

1. **The report is sensitive.** It contains client IPs, request paths,
   and user agents. On an Internet-facing deployment this is exactly
   the class of data that helps an attacker profile the application.
2. **The CSP blocks it.** The application enforces `script-src 'self'`.
   The GoAccess report uses inline JavaScript. Serving it through Nginx
   would require weakening the CSP for one path — which would affect
   the application's response headers too.

The decision was to keep the report off the web server entirely:
generated to `/var/lib/goaccess/report.html`, mode `640`, owner
`root:root`. Access is via the host or by copying off-band. The CSP
stays strict. **The security control determined the architecture, not
the other way around.**

**Automation.** A script
(`deploy/monitoring/generate-goaccess-report.sh`) generates the report
with two properties:

- **Fails safe on an empty log.** If the log is empty (at boot, after
  rotation), the script exits cleanly with a message, rather than
  producing an empty report.
- **Atomic rename.** The report is generated to a temporary `.html`
  file and renamed to the final name. A reader never sees a half-written
  report.

A systemd timer runs it hourly (`OnCalendar=hourly`, `OnBootSec=5min`,
`Persistent=true`).

**A small fix during the session.** The first version of the service
used `SYSLOG_IDENTIFIER` (uppercase) as a key in `[Service]`. systemd
rejected it as unknown — the directive is `SyslogIdentifier`
(camelCase). The consequence was cosmetic but the warning was correctly
caught and fixed.

### Part 2 — The correlation check

This is the sub-task that closes the finding from the simulated
incident exercise: **the rate limiter blocks abuse silently, and
nothing alerts when it fires.**

**The discovery that shaped the design.** The first version of the
script read only the FastAPI structured log. It detected nothing when
25 login attempts were sent against the API. The attacker's view was:

    401 401 401 401 429 429 429 ... (21 more 429s)

But when the script ran, it reported zero 429s. The reason: **the 429s
never reached FastAPI.** The rate limiter acts at the Nginx edge.
When it fires, the request is refused before the application sees it.
The FastAPI log correctly showed 4 requests (the ones that passed) and
the Nginx log correctly showed 21 requests (the ones that did not). No
single log source was complete.

**This is the central lesson of the session.** Every layer in the
stack sees a different subset of what happens:

| Source                  | Sees                                    |
|-------------------------|-----------------------------------------|
| Nginx access log        | Everything that arrives at the edge     |
| FastAPI structured log  | Everything that reaches the application |
| auditd                  | Everything that touches the filesystem  |
| journalctl              | Service lifecycle events                |

A detection system that reads one source has a blind spot defined by
what that source does not see.

**The redesigned script reads two sources:**

- **Nginx access log** (COMBINED format) — for 429s.
- **FastAPI structured log** (JSON) — for 401 bursts from a single IP
  and for 5xx errors.

The two are correlated by time window, not by request id (this lab does
not propagate request ids). For the alert classes implemented, that is
sufficient.

**Alert classes and thresholds:**

| Category    | Source  | Threshold                        |
|-------------|---------|----------------------------------|
| `429_BURST` | Nginx   | > 10 rate-limited requests       |
| `401_BURST` | FastAPI | > 20 failed auths from one IP    |
| `5XX_BURST` | FastAPI | > 5 server errors                |

**Verification.** After sending 25 login attempts with wrong
credentials:

    ALERT [429_BURST] 21 requests were rate-limited at the Nginx edge
        top paths: /api/auth/login (21); top IPs: 192.168.1.173 (21)

**21 of 25 requests were refused at the edge.** The 4 that reached
FastAPI are the ones below the rate limit, and they appear in the
FastAPI log as 401s. The full picture requires both logs.

**Where alerts go.** `/var/log/secure-fullstack/alerts.log` (mode 640,
owner root:root) and stdout (journald, identifier `correlation-check`).

**Automation.** A systemd timer runs the script every 5 minutes
(`OnUnitActiveSec=5min`, `Persistent=true`). The 5-minute cadence was
chosen over the hourly cadence used for the GoAccess report because
this script is a detection control — it should not wait up to an hour
to notice abuse.

**Known limitation, documented.** The Nginx side of the script counts
every 429 in the current log file, not only those within the lookback
window. The Nginx log rotates daily
(`/etc/logrotate.d/nginx`), so the imprecision is bounded to 24 hours.
A stricter implementation would parse each line's timestamp and filter
by time. This is documented in the script itself, in the monitoring
README, and here.

### Part 3 — What this session completed

| Phase 8 sub-task                    | Status |
|-------------------------------------|--------|
| Structured JSON logging             | Done   |
| auditd with 15 rules                | Done   |
| GoAccess report + hourly timer      | Done   |
| Correlation check script            | Done   |
| Alert when the rate limiter fires   | Done   |

**Phase 8 is complete.** The system now has:

- Structured logs that a machine can filter and aggregate.
- Kernel-level audit of file and privilege events.
- A traffic dashboard for the Nginx edge.
- A correlation script that turns logs into alerts.
- Automated timers for both the report and the check.

And it has a finding that connects back to the earlier incident
exercise: the detection gap identified in Session 15 is now closed,
with evidence in the form of the `429_BURST` alert produced by a real
attack simulation.

### Concepts learned

- **Every log sees a layer.** The correlation finding is not specific
  to this project — it is the reason SIEMs exist. A single log source
  always has a defined blind spot, and the blind spot is a function of
  where the source sits in the architecture.
- **Verify the artefact, not the progress output.** GoAccess printed
  `{0}` while producing a 720 KB report. Reading progress bars and
  counters is less reliable than reading the files they should have
  produced.
- **The control can determine the architecture.** The CSP was written
  in Phase 2. In Phase 8 it blocked a report. The decision was not to
  weaken the CSP, but to move the report. This is the reverse of the
  common pattern ("the architecture forced us to relax the control").
- **Failing safe is different from failing loudly.** Both scripts
  detect the trivial error case (empty log) and exit cleanly, rather
  than producing misleading output. The habit comes from the same
  principle as `lab_boundary` in the Hermes project.
- **A finding closed with evidence is worth more than a finding
  closed by assertion.** The simulated incident exercise (Session 15)
  said "detection is not automatic". Session 21 closes that with a
  real alert produced by a real attack simulation.
- **Automation makes the difference between a demonstration and a
  control.** Running the correlation script by hand proves it works.
  Running it every five minutes as a systemd timer makes it a control
  that operates without the operator remembering to invoke it.

### Files changed

- `deploy/monitoring/generate-goaccess-report.sh` — created
- `deploy/monitoring/goaccess-report.service` — created
- `deploy/monitoring/goaccess-report.timer` — created
- `deploy/monitoring/correlation-check.sh` — created
- `deploy/monitoring/correlation-check.service` — created
- `deploy/monitoring/correlation-check.timer` — created
- `deploy/monitoring/README.md` — created and expanded

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `7903107` | feat(monitoring): add GoAccess report generator with hourly timer |
| `aeab272` | feat(monitoring): add correlation check script                 |
| `f74ba6e` | feat(monitoring): add correlation check timer and update README |

### Next step — Phase 9

Phase 9 is **configuration as code**, with three sub-tasks:

1. **Ansible playbooks** that reproduce the current server state:
   SSH hardening, UFW rules, Fail2Ban, auditd, the systemd units for
   the application and the monitoring scripts.
2. **Lynis** — a hardening audit tool that produces a score against a
   known baseline (CIS). Run before the playbook, run after, compare.
3. **Privilege separation.** This is the largest item and the one that
   closes risk **R-02**. The application currently runs as the operator
   account (`filipe`). The plan:

   - Create a dedicated system user `secure-app` with no login shell
     and no `sudo`.
   - Migrate `lab.db` ownership to that user.
   - Update the systemd unit to run the FastAPI service as `secure-app`.
   - Adjust Nginx static file permissions so the served directory is
     readable by `www-data` without depending on `/home/filipe/` being
     traversable by other users.
   - Revoke the `chmod o+x /home/filipe` permission that was needed
     when Nginx first served from the operator's home directory.

   This last step closes two findings at once: R-02 (app runs as the
   operator) and the residual sub-issue noted when Nginx first started
   serving the SPA.

---

## Session 22 — Phase 9: Lynis, Ansible, and privilege separation

**Goal:** close Phase 9 by adding configuration as code (Ansible) and
finishing the largest item of the phase: separating the application
from the operator account.

### Part 1 — Lynis baseline and corrections

Lynis was installed and a first audit was run before making any
changes. The **baseline score was 71**.

A baseline before hardening is the same discipline as a test before a
refactor: it establishes what "before" means, so that "after" can be
compared. Without it, the work is a collection of changes without a
measurement.

The audit produced **1 warning** and 30 suggestions:

| Category | Count | Nature |
|----------|-------|--------|
| Warning | 1 | `KRNL-5830` — reboot pending |
| Suggestions | 30 | Mixed |

**Only 1 warning** is a good result for an Ubuntu install. A default
Ubuntu Desktop usually produces 10-15. The hardening from Phases 2-8
had already done most of the work.

**Corrections applied** (those that are applicable to this context):

| Item | Result |
|------|--------|
| CUPS / legacy-printer-app | Disabled. Port 631 no longer listening. |
| Unused network protocols (dccp, sctp, rds, tipc) | Disabled via `/etc/modprobe.d/` |
| SSH `MaxSessions 10 → 2` | Applied to the hardening drop-in |
| SSH `ClientAliveCountMax 3 → 2` | Applied |
| Orphaned packages | Purged via `apt autoremove` |
| Reboot pending | Rebooted |

**Corrections deliberately not applied**, with rationale:

| Suggestion | Reason |
|-----------|--------|
| GRUB password | No physical console access to the VM |
| Separate partitions | Requires reinstalling the VM |
| Disable USB drivers | The VM has virtual USB only |
| `LogLevel INFO → VERBOSE` | INFO is sufficient for Fail2Ban; VERBOSE floods the journal without adding detection value |
| Remove printer drivers | Part of the Ubuntu Desktop metapackage |

**A discovery along the way.** Removing the `cups` package caused
Ubuntu to install `legacy-printer-app` as a replacement, which
immediately started running. The service was found by checking
`systemctl list-units` after the removal, not by assuming the removal
had done what it appeared to do. **This is the pattern: after a change,
verify the outcome, not the command's success message.**

After the reboot and the applicable corrections, the Lynis score was
**73** — a +2 improvement.

The small delta is expected. Lynis weights heavily on things that a
Desktop install cannot achieve (separate partitions, no printer
drivers, no USB). The same work on an Ubuntu Server would show 80+.
The context determines the ceiling, not the work.


### Part 2 — Ansible

Ansible was installed and a playbook was written to reproduce the
manual hardening as code.

**Structure:**

    deploy/ansible/
    ├── ansible.cfg
    ├── inventory.yml
    └── hardening.yml

The inventory points to `localhost` with `ansible_connection: local`.
The playbook runs from within the target host — no SSH, no host keys,
no passwords. Privilege escalation is requested per play
(`become: true`), not globally.

**What the playbook covers:**

- SSH hardening drop-in (all the directives from Phase 3, plus the
  Lynis refinements)
- UFW (default policies, three rules, enabled)
- Fail2Ban (jail configuration, custom filter for `sshd-session`)
- auditd (15 rules, including the privilege escalation rule)
- Disabled network protocols
- umask in `/etc/login.defs`
- Privilege separation (Phase 9's largest item — see Part 3)

**Handlers validate before restarting.** Each handler runs the
service's own config check (`sshd -t`, `fail2ban-client -t`,
`augenrules --load`) before restarting. A syntax error written by the
playbook fails the handler, not the running service. Without this,
a typo in the SSH config would break access — the break-glass is the
VMware console, but a break is still a break.

**An early failure worth recording.** The first version of the
handlers used `block:` to group the validation and the restart. Ansible
did not resolve them: "The requested handler was not found". The fix
was to use a single `shell` command with `&&`:

    ansible.builtin.shell: sshd -t && systemctl restart ssh

If the validation fails, `&&` stops the restart. The behaviour is the
same; the construct is one Ansible actually supports.

**Idempotency verified:**

- Dry-run (`--check --diff`): 5 changed tasks, all file rewrites
- First real run: `changed=8` (5 files + 3 handlers)
- Second run: `changed=0`

The `changed=0` is the important number. It means the playbook
describes a state, and the state is that state. If the VM disappeared,
the playbook would take a fresh host to the same configuration in
minutes.

**A refinement after the initial run.** The code-copy tasks used
`shell` + `rsync` with `changed_when: false`. That is a lie to the
inventory: the task *can* change the system, but the playbook reports
it never does. The fix was to replace them with
`ansible.posix.synchronize` using `checksum: yes`, `archive: no`, and
`delete: yes`. The result:

- `changed` fires only when file contents differ, not when timestamps
  differ
- The handler that restarts the API fires only on real code changes
- Idempotency is honest, not cosmetic

### Part 3 — Privilege separation

This was the largest item in Phase 9 and the one that closes **R-02**
(the highest-severity risk in the register: the application ran as the
operator account, with access to the PKI directory and the SSH key).

**Before:**

    filipe (operator)
      ├── runs uvicorn
      ├── owns lab.db
      ├── has sudo
      ├── owns ~/pki/ca.key
      └── receives the Kali SSH key

A single compromise of `filipe` was a compromise of everything.

**After:**

    secure-app (system user)
      ├── runs uvicorn
      └── owns lab.db and .jwt_secret

    filipe (operator)
      ├── has sudo
      └── owns ~/pki/

    www-data (Nginx)
      └── serves /var/www/secure-fullstack

The application cannot read `~/pki/`, cannot read the SSH key, and
cannot escalate. A compromise of the application is contained.

**What changed:**

| Item | Before | After |
|------|--------|-------|
| Process user | `filipe` | `secure-app` (no shell, no sudo, no home) |
| Code | `~/secure-fullstack-lab/backend/` | `/opt/secure-fullstack/backend/` |
| Venv | `~/.../.venv` | `/opt/secure-fullstack/venv/` |
| Database | `~/.../backend/lab.db` | `/var/lib/secure-fullstack/lab.db` |
| JWT secret | `~/.../backend/.jwt_secret` | `/var/lib/secure-fullstack/.jwt_secret` |
| Frontend | `~/.../frontend/dist/` | `/var/www/secure-fullstack/` |
| Nginx `root` | `/home/filipe/...` | `/var/www/secure-fullstack` |
| `/home/filipe` | `drwxr-x--x` (`o+x`) | `drwxr-x---` |

**The migration, step by step, with what each step revealed:**

1. **Created the user.** `useradd --system --no-create-home --shell
   /usr/sbin/nologin secure-app`. Verified that `sudo` is denied for
   this user (it is — the user is not in the sudoers group).

2. **Moved the database first, before touching the service.** This
   creates the destination before the source is removed. The reverse
   order leaves the application with nothing to open if anything goes
   wrong.

3. **Moved the code and the venv.** Two surprises:
   - The venv was created by `pip install` running as `root`, so the
     files were `root:root` with mode `640` (because the umask 027 from
     Phase 9 was already in effect). The `secure-app` could not read
     them. The fix was `chown -R secure-app:secure-app` on the venv.
   - The `uvicorn` entrypoint script (`bin/uvicorn`) has an internal
     `from uvicorn.main import main` that fails on this version of the
     package. The fix was to use `python3 -m uvicorn` instead, which
     uses the public API.

4. **Moved the `.jwt_secret`.** The `security.py` was patched to point
   to the new path, and the systemd unit restarted. The app then read
   the secret and issued tokens successfully.

5. **Moved the frontend.** Copied `dist/` to `/var/www/secure-fullstack/`,
   changed the Nginx `root`, reloaded. The Vue app loads.

6. **Revoked `chmod o+x /home/filipe`.** Until this point, the `o+x`
   on the home directory was required for Nginx to serve static files
   from there. With the files now under `/var/www/`, the permission
   is no longer needed and represents an unnecessary exposure. Revoking
   it was the final step, and it was done only after confirming that
   every service still worked without it.

**Verified after every step:**

- `/api/hello` responds on both `127.0.0.1:8000` and `https://192.168.1.173`
- Login works (secure-app reads `users` and `.jwt_secret`)
- Asset creation works (secure-app writes to `lab.db`)
- The Vue SPA loads from `/var/www/`
- `/home/filipe` is `drwxr-x---` — no other user can traverse

**R-02 closed.** The application now runs as a dedicated, unprivileged,
shell-less system user. A compromise of the application no longer
gives access to the CA key, the SSH key, or `sudo`.


### Concepts learned

- **A baseline before hardening is not optional.** Without the 71
  score, the work would have been "I changed a bunch of things". With
  it, the work is "I improved from 71 to 73, and here is why the delta
  is small in this environment". The number does not have to be
  impressive; it has to be a number.
- **The context sets the ceiling.** Lynis on an Ubuntu Desktop cannot
  reach 80 by design. The score reflects the environment as much as
  the work. An auditor reading "73 on a Desktop" and "73 on a Server"
  sees two different levels of effort.
- **Remove is not the same as disable, and neither is the same as
  done.** Removing `cups` installed `legacy-printer-app`. The removal
  had succeeded; the service was still running. Verify the outcome,
  not the command's exit code.
- **Ansible's idempotency is only worth the truth of its `changed`
  counter.** `changed_when: false` silences the counter. The task still
  changes the system; the inventory just stops knowing about it.
  `synchronize` with `checksum: yes` makes `changed` mean what it
  says: the file contents differ.
- **Handlers that can break a service must validate before
  restarting.** The `sshd -t && systemctl restart ssh` pattern fails
  safely: a bad config stops the restart. The alternative is a service
  that restarts into a broken state.
- **Migration order matters.** Move the destination first, verify,
  then remove the source. In practice: copy `lab.db` to
  `/var/lib/secure-fullstack/`, update the path, restart, verify. Only
  then is the old file safe to delete (in our case we used `mv`, which
  is atomic — but the principle is the same).
- **The privilege separation makes the pipeline's assumptions
  visible.** Every place where a service needed to read a file from
  `/home/filipe/` was an implicit privilege. The migration surfaced
  them all: the venv (owned by root), the `.jwt_secret` (owned by
  filipe), the `dist/` (owned by filipe). None of them were visible
  until we tried to remove the `o+x` on the home directory and
  discovered what still depended on it.
- **`chmod o+x` on a home directory is a smell, not a necessity.**
  It was a workaround for "the web server needs to read from here".
  The correct answer is "the web server should not need to read from
  here". The migration was the difference between the two.

### Files changed

- `deploy/ansible/ansible.cfg` — created
- `deploy/ansible/inventory.yml` — created
- `deploy/ansible/hardening.yml` — created, then extended with the
  privilege separation tasks and the `synchronize` refinements
- `backend/app/database.py` — `DATABASE_URL` points to
  `/var/lib/secure-fullstack/lab.db`
- `backend/app/security.py` — `_JWT_SECRET_FILE` points to
  `/var/lib/secure-fullstack/.jwt_secret`
- `deploy/systemd/secure-fullstack-api.service` — `User=secure-app`,
  `WorkingDirectory` and `ExecStart` under `/opt/`
- `deploy/nginx/secure-fullstack` — `root /var/www/secure-fullstack`

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| `406cc5d` | feat(ansible): add hardening playbook with idempotent tasks    |
| `4c82064` | docs(readme): register the incomplete SoA as a gap             |
| `a00da9e` | feat(security): isolate the application under a dedicated system user |
| *(pending)* | feat(ansible): add privilege separation and use synchronize |

### Phase 9 — closed

With this session, Phase 9 is complete:

- Ansible playbook reproduces the full server state (SSH, UFW,
  Fail2Ban, auditd, protocols, umask, privilege separation).
- Idempotency verified: `changed=0` on the second run.
- Lynis score measured before and after: 71 → 73.
- R-02 closed. The application runs as `secure-app`, a user with no
  shell, no sudo, and no access to the operator's home.

### Next step — Phase 10

Phase 10 is **backup and restore**:

1. Automated backup of `lab.db` (and the `.jwt_secret` — losing either
   means losing the ability to authenticate).
2. Defined RTO and RPO. Not "we have backups" but "we can restore in
   N minutes and lose at most M minutes of data".
3. **A real restore test.** Delete the database, restore from backup,
   measure the time. A backup that has never been restored is a hope,
   not a control.
4. Encrypted backup of the CA key, stored offline.


---

## Session 23 — Phase 10: Backup and restore

**Goal:** implement automated backups with a defined RPO, measure the
RTO with a real restore, and document the whole thing.

The phase exists because "I have backups" is not a control. A backup
that has never been restored is a hope. The work here is to make the
backup into something that has been proven to work.

### Part 1 — The backup script

`deploy/backup/backup.sh`, run by a systemd oneshot unit called by an
hourly timer (see Part 3).

**What it backs up:**

- `/var/lib/secure-fullstack/lab.db` — the SQLite database (users,
  assets).
- `/var/lib/secure-fullstack/.jwt_secret` — the signing key for JWTs.

**Why the secret is included.** If the secret is lost, the application
cannot authenticate anyone: every token issued so far is invalid, and
every refresh token stored by a client is useless. The database can be
restored from a backup; the secret cannot. Including it in the backup
turns "the disk failed" into "we restored and everything works".

**Why the database is copied with `sqlite3 .backup` and not `cp`.**
The `cp` command reads the file page by page. If a write happens during
the copy, the backup can be half-before and half-after the transaction
— a file that SQLite will refuse to open, or that will open with
corrupted data. The `.backup` command asks the SQLite engine itself to
produce a consistent snapshot, coordinating with any in-progress writes.
This is the difference between "I have a copy of the file" and "I have
a backup that can be restored".

**SHA256 hashes.** Each backup is accompanied by a `.sha256` file
containing the hash of the backup. Before restoring, the hash can be
verified to confirm that the file has not been corrupted in storage.

**Retention: 7 days.** The script removes files older than 7 days.
This is enough to recover from "I deleted something a week ago" without
accumulating months of backups in a lab that generates little data.

**Runs as `root`.** The database is owned by `secure-app`; the backup
directory is owned by `secure-app`. The backup runs as `root` on
purpose: a compromise of the application cannot delete its own
backups. The backup is a control **outside** the application, not
inside it.

### Part 2 — RTO, RPO, and a real restore test

**RPO (Recovery Point Objective): 24 hours.**
The timer runs daily at 03:00. If the database is lost at 02:59, the
most recent backup is from 03:00 the previous day: almost 24 hours of
data are lost. For a lab with very little data change, this is
acceptable. Reducing the interval to hourly (or every five minutes)
would reduce the RPO proportionally; the trade-off is disk space and
I/O, both negligible for a 28 KB database.

**RTO (Recovery Time Objective): measured at 1.394 seconds.**

The measurement was taken with `time` around the four recovery
commands:

    sudo cp /var/backups/secure-fullstack/lab-<ts>.db /var/lib/secure-fullstack/lab.db
    sudo chown secure-app:secure-app /var/lib/secure-fullstack/lab.db
    sudo chmod 640 /var/lib/secure-fullstack/lab.db
    sudo systemctl restart secure-fullstack-api.service

The database is 28 KB, so the copy is instant; the restart dominates.
This number is meaningful, not aspirational — it was measured on the
same machine that would perform the recovery.

**The test, step by step:**

1. Record the current state: 4 assets owned by the operator.
2. **Remove the database.** `mv /var/lib/secure-fullstack/lab.db
   /var/lib/secure-fullstack/lab.db.broken`. The application keeps
   running; on restart, SQLAlchemy's `create_all` recreates an empty
   `users` table. The login endpoint now returns 401 for the
   previously valid credentials, because the user is gone from the
   database.
3. **Restore the database.** Copy from `/var/backups/`, fix ownership
   and permissions, restart the service.
4. **Verify.** The login works again. The assets are back.

**A note on an early mistake in the test.** The first attempt used
`GET /api/hello` as the "is the database needed" endpoint. That
endpoint does not touch the database — it returns a hardcoded JSON
message. The test therefore "passed" without the database, proving
nothing. The fix was to use the **login endpoint**, which reads the
`users` table. The mistake is recorded here because it is instructive:
**the test must exercise the thing the backup is supposed to protect**.


### Part 3 — Automation

The backup script is called by a systemd oneshot unit, which is
scheduled by a timer:

- `backup.service` — runs `backup.sh`, as `root`.
- `backup.timer` — `OnCalendar=*-*-* 03:00:00`, `Persistent=true`.

**`Persistent=true` matters.** If the VM is off at 03:00, the timer
fires the next time the VM boots. A backup that only runs if the
machine happens to be on at 03:00 is not a backup; it is a hope. This
setting makes the schedule survive reboots.

**Verified.** Started manually with `systemctl start backup.service`,
which produced a second backup pair in `/var/backups/secure-fullstack/`
(database + secret + hashes). The timer is listed with `NEXT` pointing
to the following 03:00.

### Concepts learned

- **A backup is not a backup until it has been restored.** The 1.4s RTO
  is not a number I estimated; it is a number measured while the
  database was actually missing, with the login endpoint returning 401
  until the restore completed. This is the difference between a control
  and a claim.
- **`.backup` vs `cp`.** SQLite has a dedicated backup command for a
  reason. A file copy of a database in use is a race condition that
  usually looks like a backup and occasionally is a corrupt file. The
  `.backup` command coordinates with the engine.
- **The test must exercise the thing being protected.** My first test
  used `/api/hello`, which does not touch the database. The "test
  passed" and proved nothing. The fix — using the login endpoint —
  immediately showed the problem (401 because the user was gone). A
  test that cannot fail is not a test.
- **RPO is a choice, not an accident.** 24 hours is acceptable because
  the lab changes little. The same script with `OnCalendar=hourly`
  would give 1 hour. The number is a decision, documented, not a
  side effect of "we run it once a day".
- **Backups live outside the application.** The backup runs as `root`
  and writes to a directory the application cannot modify. A
  compromised application cannot delete its own backups. If the
  application could run the backup, it could also delete the backup.
- **A backup of the database is not a backup of the secret.** The
  `.jwt_secret` is not in the database, and losing it does not show up
  as "the data is missing" — it shows up as "every token is invalid
  and nobody can log in until a new secret is generated". Both files
  are in the backup because both are necessary for the application to
  function.

### Files changed

- `deploy/backup/backup.sh` — created
- `deploy/backup/backup.service` — created
- `deploy/backup/backup.timer` — created
- `deploy/backup/README.md` — created

### Commits this session

| Commit  | Description                                                    |
|---------|----------------------------------------------------------------|
| *(pending)* | feat(backup): automated database and secret backup          |

### Phase 10 — complete

- Automated backup of the database and the JWT secret.
- Verified integrity with SHA256.
- **Real restore test performed**, not simulated.
- **RTO measured: 1.394 seconds.**
- **RPO defined: 24 hours.**
- Documented in `deploy/backup/README.md` and this JOURNAL.

### Next step — Phase 11

Phase 11 is **supply chain**: containerise the backend and demonstrate
the supply-chain tooling.

1. **Containerfile** for the FastAPI backend (Podman).
2. **Run as non-root**, read-only filesystem where possible.
3. **Trivy** scan of the image — CVEs in the image layers.
4. **SBOM** with Syft in CycloneDX format.
5. **Image signing** with cosign.

**Scope note (from Session 11).** This is the backend only. The
frontend and the Nginx proxy remain deployed as they are. Rebuilding
the whole deployment to demonstrate the concept would be work without
new information. The JOURNAL entry from Session 11 records the
reasoning; it stands.
