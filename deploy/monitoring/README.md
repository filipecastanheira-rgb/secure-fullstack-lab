# Monitoring

Runtime monitoring utilities for the Secure Fullstack Lab.

## What is here

| File                                | Purpose                                          |
|-------------------------------------|--------------------------------------------------|
| `generate-goaccess-report.sh`       | Generate a GoAccess HTML report from the Nginx access log |
| `goaccess-report.service`           | Systemd oneshot unit for the GoAccess report    |
| `goaccess-report.timer`             | Systemd timer that runs the report hourly       |
| `correlation-check.sh`              | Read log sources and emit alerts on abuse patterns |
| `correlation-check.service`         | Systemd oneshot unit for the correlation check  |
| `correlation-check.timer`           | Systemd timer that runs the check every 5 minutes |

## The GoAccess report

[GoAccess](https://goaccess.io/) parses the Nginx access log and produces
a self-contained HTML report with traffic statistics: visitor hosts,
requested files, status codes, user agents, and more.

**The report is intentionally not served by Nginx.** It is generated to
`/var/lib/goaccess/report.html` with mode `640` and owner `root:root`.
It contains client IPs, request paths, and user agents — information that
would help an attacker profile the application.

**Secondary reason.** The Nginx configuration enforces a strict Content
Security Policy with `script-src 'self'`. The GoAccess report uses inline
JavaScript, so the browser blocks it. Rather than weaken the CSP for one
file — which would affect the application's own responses — the report
is kept off the web server entirely. The control determined the
architecture, not the other way around.

**Access.** On the host:

    sudo cat /var/lib/goaccess/report.html > /tmp/report.html
    sudo chown $(id -u):$(id -g) /tmp/report.html

Then copy `/tmp/report.html` to a workstation and open it in a browser.

## The correlation check

`correlation-check.sh` reads **two log sources** and looks for abuse
patterns:

- **Nginx access log (COMBINED)** — the edge, where the rate limiter
  acts. A 429 here means a request was refused before reaching the
  application.
- **FastAPI structured log (JSON)** — the application, where user ids
  and application errors live.

**Why two sources.** Neither is complete on its own. When the rate
limiter fires, the request never reaches FastAPI, so the FastAPI log
does not know it happened. A script that read only the FastAPI log would
miss every rate-limited request. This was discovered empirically during
the exercise — see `docs/JOURNAL.md` session 21.

**Alert classes:**

| Category    | Source | Threshold (default)         |
|-------------|--------|-----------------------------|
| `429_BURST` | Nginx  | > 10 rate-limited requests  |
| `401_BURST` | FastAPI| > 20 failed auths from one IP |
| `5XX_BURST` | FastAPI| > 5 server errors           |

**Where alerts go.** `/var/log/secure-fullstack/alerts.log` (mode 640,
owner root:root), and stdout (captured by systemd/journald under the
identifier `correlation-check`).

**Known limitation.** The Nginx side counts every 429 in the current log
file, not only those within the lookback window. The Nginx log rotates
daily (`/etc/logrotate.d/nginx`), so the imprecision is bounded to 24
hours. A stricter implementation would parse the timestamp from each
line. The limitation is documented in the script itself.

## Installation

    sudo cp deploy/monitoring/*.service /etc/systemd/system/
    sudo cp deploy/monitoring/*.timer   /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now goaccess-report.timer
    sudo systemctl enable --now correlation-check.timer

Check the schedules:

    sudo systemctl list-timers 'goaccess-report.timer' 'correlation-check.timer'

## Manual invocation

    sudo systemctl start goaccess-report.service
    sudo systemctl start correlation-check.service

Or run the scripts directly:

    sudo /usr/local/sbin/generate-goaccess-report.sh
    sudo /usr/local/sbin/correlation-check.sh

## Notes on the scripts

- **Both run as root.** The Nginx access log is owned by `www-data:adm`
  and is not readable by the operator account.
- **The GoAccess generator detects the empty-log case** and exits
  cleanly. It also generates to a `.html`-suffixed temporary file and
  renames it atomically, so a reader never sees a half-written report.
- **The correlation script does not send notifications.** For this lab,
  the alerts log and the journal are the alert channel. Forwarding to a
  real notifier (email, webhook, Slack) is deliberately out of scope.

## Related

- `docs/JOURNAL.md` sessions 20 and 21 — the record of the logging,
  auditd, GoAccess, and correlation work.
- `docs/threat-model.md` — the CSP enforcement that influenced the
  GoAccess architecture decision.
- `docs/simulated-incident-exercise.md` — the exercise that identified
  the need for automatic detection when the rate limiter fires.
