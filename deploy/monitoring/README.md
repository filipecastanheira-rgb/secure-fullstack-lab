# Monitoring

Runtime monitoring utilities for the Secure Fullstack Lab.

## What is here

| File                          | Purpose                                         |
|-------------------------------|-------------------------------------------------|
| `generate-goaccess-report.sh` | Generate a GoAccess HTML report from the Nginx access log |
| `goaccess-report.service`     | Systemd oneshot unit that runs the script       |
| `goaccess-report.timer`       | Systemd timer that runs the unit hourly         |

## The GoAccess report

[GoAccess](https://goaccess.io/) parses the Nginx access log and produces
a self-contained HTML report with traffic statistics: visitor hosts,
requested files, status codes, user agents, and more.

**The report is intentionally not served by Nginx.** It is generated to
`/var/lib/goaccess/report.html` with mode `640` and owner `root:root`.
It contains client IPs, request paths, and user agents — information that
would help an attacker profile the application. On an Internet-facing
deployment this is exactly the class of data that should not be public.

**How to access it.** On the host:

    sudo cat /var/lib/goaccess/report.html > /tmp/report.html
    sudo chown $(id -u):$(id -g) /tmp/report.html

Then copy `/tmp/report.html` to a workstation via `scp` and open it in a
browser. Alternatively, use `ssh -L` port forwarding to view it over a
local port.

**Why not just serve it?** The Nginx configuration enforces a strict
Content Security Policy (see `deploy/nginx/secure-fullstack`) with
`script-src 'self'`. The GoAccess report uses inline JavaScript, so the
browser blocks it. Rather than weaken the CSP for one file — which would
also affect the application's own responses — the report is kept off the
web server entirely.

This is a case where the security control (the CSP) determined the
architecture (a report not served by the web server). The CSP was not
relaxed to accommodate the report; the report was moved to accommodate
the CSP.

## Installing the timer

    sudo cp deploy/monitoring/goaccess-report.service /etc/systemd/system/
    sudo cp deploy/monitoring/goaccess-report.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now goaccess-report.timer

Check the schedule:

    sudo systemctl list-timers goaccess-report.timer

The timer runs hourly (`OnCalendar=hourly`) and 5 minutes after boot
(`OnBootSec=5min`). It uses `Persistent=true` so a run missed while the
host was off is executed at the next opportunity.

## Manual invocation

    sudo systemctl start goaccess-report.service

Or run the script directly:

    sudo /home/filipe/secure-fullstack-lab/deploy/monitoring/generate-goaccess-report.sh

## Notes on the script

- **Runs as root.** The Nginx access log is owned by `www-data:adm` and
  not readable by the operator account.
- **Detects the empty-log case.** If the log is empty, the script exits
  cleanly with a message. This matters at boot and after log rotation.
- **Atomic rename.** The report is generated to a temporary file ending
  in `.html` (GoAccess requires a known extension) and renamed to the
  final name. A reader never sees a half-written report.
- **Reads-only by default.** The script does not modify the Nginx access
  log. It does not run `logrotate`.

## Related

- `docs/JOURNAL.md` session 21 — the record of the GoAccess integration
  and the decision not to serve the report.
- `docs/threat-model.md` — the CSP enforcement that influenced the
  architecture decision.
