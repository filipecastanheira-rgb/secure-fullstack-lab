# Hardening

Configuration files that turn a stock Ubuntu VM into a hardened server.

These files are **copies**. The real ones live in the locations shown in each
section below. When you change one, edit the real file first, then copy it
back here and commit.

## Files in this folder

| File                          | Real location                                    | Purpose                        |
|-------------------------------|--------------------------------------------------|--------------------------------|
| `sshd-hardening.conf`         | `/etc/ssh/sshd_config.d/99-hardening.conf`       | SSH hardening                  |
| `fail2ban-jail.local`         | `/etc/fail2ban/jail.local`                       | Fail2Ban configuration         |
| `fail2ban-secure-sshd.conf`   | `/etc/fail2ban/filter.d/secure-sshd.conf`        | Custom Fail2Ban filter for SSH |
| `ufw-rules.txt`               | (documentation only — see below)                 | UFW rules reference            |

## Overview

Four layers of defense, each independent:

    ┌──────────────────────────────────┐
    │  UFW          — network filter   │   Only SSH (from one IP), 80, 443
    ├──────────────────────────────────┤
    │  Fail2Ban     — dynamic bans     │   Bans IPs with repeated auth failures
    ├──────────────────────────────────┤
    │  sshd         — auth hardening   │   Key-only, no root, allowlist of users
    ├──────────────────────────────────┤
    │  Nginx + TLS  — application      │   HTTPS, security headers, no HTTP
    └──────────────────────────────────┘

## SSH hardening (`sshd-hardening.conf`)

Placed as a drop-in under `/etc/ssh/sshd_config.d/`. Applied **after** the
main config because of the `99-` prefix. Key settings:

- `PasswordAuthentication no` — passwords disabled entirely
- `PermitRootLogin no` — root can never log in over SSH
- `AllowUsers filipe` — allowlist; everyone else is rejected before auth
- `KbdInteractiveAuthentication no` + `ChallengeResponseAuthentication no`
  — disables alternate interactive auth paths (a common gotcha)
- `MaxAuthTries 3` — cuts the connection after 3 failed attempts
- `LoginGraceTime 30` — limits the unauthenticated window
- `AllowTcpForwarding no` — prevents using the server as a jump host
- `AllowAgentForwarding no` — avoids leaking the client's keys
- `X11Forwarding no` — no GUI over SSH

**Break-glass:** if SSH access is lost, use the VMware console. This has been
the safety net throughout.

**To reinstall on a new machine:**

    sudo cp sshd-hardening.conf /etc/ssh/sshd_config.d/99-hardening.conf
    sudo sshd -t          # validate BEFORE restarting
    sudo systemctl restart ssh

## SSH key setup (client side)

The connecting client (Kali) generates a keypair and copies the public key:

    ssh-keygen -t ed25519 -C "kali-lab@192.168.1.125"
    ssh-copy-id filipe@192.168.1.173

Test that key auth works **before** disabling passwords. The order matters —
if you disable passwords first and the key is wrong, you lock yourself out.

## UFW (`ufw-rules.txt`)

UFW defaults: `deny incoming`, `allow outgoing`. Only three rules:

    sudo ufw allow from 192.168.1.125 to any port 22 proto tcp comment 'SSH from Kali'
    sudo ufw allow 80/tcp  comment 'HTTP (redirects to HTTPS)'
    sudo ufw allow 443/tcp comment 'HTTPS'

Notes:

- SSH is restricted to one source IP (`192.168.1.125` = the Kali VM).
- HTTP/HTTPS are open to the lab network (any source), because the browser
  may come from any address on the lab segment.
- **Order matters:** define the SSH rule BEFORE running `ufw enable`, or you
  lose remote access.

**To reinstall:**

    cat ufw-rules.txt | grep '^ufw ' | while read -r line; do sudo $line; done
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw enable

## Fail2Ban (`fail2ban-jail.local` + `fail2ban-secure-sshd.conf`)

Bans IPs that fail SSH authentication repeatedly. Uses **UFW as the ban
backend** so bans are visible in `ufw status`.

**Key settings:**

- `bantime = 1h`, `findtime = 10m`, `maxretry = 5`
- `banaction = ufw` — must be `ufw`, not the default `iptables`, because
  UFW uses its own chains and raw iptables rules would be ignored.
- `backend = systemd` — reads from the journal instead of flat log files.

**Why a custom filter?** Two reasons:

1. On OpenSSH 9.x+ (Ubuntu 24.04+), the authentication worker process is
   named `sshd-session`, **not** `sshd`. The packaged filter restricts to
   `_COMM=sshd` and misses every entry.
2. We also want to count `Connection closed by authenticating user ...`
   as a failed attempt — otherwise clients that give up before sending a
   key go unnoticed.

The custom filter (`secure-sshd`) also overrides `journalmatch` to match on
`_SYSTEMD_UNIT=ssh.service` only, which captures both the listener and the
session worker.

**To reinstall:**

    sudo cp fail2ban-jail.local      /etc/fail2ban/jail.local
    sudo cp fail2ban-secure-sshd.conf /etc/fail2ban/filter.d/secure-sshd.conf
    sudo fail2ban-client -t          # validate
    sudo systemctl restart fail2ban

**To verify the filter works against real logs:**

    sudo fail2ban-regex systemd-journal /etc/fail2ban/filter.d/secure-sshd.conf

**To check status and unban an IP:**

    sudo fail2ban-client status sshd
    sudo fail2ban-client set sshd unbanip 192.168.1.125

## Network assumption

This lab assumes:

- **Ubuntu VM** at `192.168.1.173`
- **Kali VM** at `192.168.1.125`

If either IP changes, update:

- The UFW rule for SSH (`from 192.168.1.125`)
- Any references in this README
- The frontend `config.js` (only if the Ubuntu IP changes)

The lab runs on an isolated virtual network — home network details are
deliberately not documented here.

## Not done yet (future sessions)

- Move the frontend build to `/var/www/` so we can revoke the `o+x`
  permission on `/home/filipe/`.
- Optionally restrict SSH to a fixed MAC-based reservation on the router,
  so the UFW rule can be narrowed to a single IP with confidence.
