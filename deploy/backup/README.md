# Backup

Database and secret backups for the Secure Fullstack Lab.

## What is backed up

| Asset | Path | Reason |
|-------|------|--------|
| SQLite database | `/var/lib/secure-fullstack/lab.db` | All application data (users, assets) |
| JWT secret | `/var/lib/secure-fullstack/.jwt_secret` | Without it, the API cannot start |

**Not backed up:**

- The CA private key (`~/pki/ca.key`). It is handled separately (see
  `docs/JOURNAL.md`, R-03). An encrypted backup of the CA key is a
  Phase 10 follow-up, not part of this script.
- The application code. It lives in Git. If the code is lost, `git
  clone` restores it. The backup script does not duplicate Git.
- The venv. It can be recreated from `requirements.txt`.

## RPO — Recovery Point Objective

**24 hours.** The backup timer runs once a day at 03:00. If the database
is lost at 02:59, the most recent backup is from 03:00 the previous day:
almost 24 hours of data are lost.

If the RPO needs to be lower, the timer interval can be reduced
(`OnCalendar=hourly`). The trade-off is disk space and I/O — for a
28 KB database, both are negligible. The current 24h is a deliberate
choice: the lab sees very little data change.

## RTO — Recovery Time Objective

**Measured: 1.4 seconds.**

The recovery procedure is:

    sudo cp /var/backups/secure-fullstack/lab-<timestamp>.db /var/lib/secure-fullstack/lab.db
    sudo chown secure-app:secure-app /var/lib/secure-fullstack/lab.db
    sudo chmod 640 /var/lib/secure-fullstack/lab.db
    sudo systemctl restart secure-fullstack-api.service

The measurement was taken with `time` around the four commands. The
database is 28 KB, so the copy is instant. The dominant cost is the
service restart (~1 second).

**This was measured, not assumed.** A backup that has never been
restored is a hope. The restoration was performed on 2026-10-17 and
the login endpoint was tested afterwards to confirm that the data was
intact. See `docs/JOURNAL.md` session 23 for the full test.

## How the backup works

- **`sqlite3 .backup`** is used for the database, not `cp`. The
  `.backup` command asks the SQLite engine for a consistent snapshot
  even if a write is in progress. A `cp` can produce a file that is
  half-before and half-after a transaction.
- **SHA256** is stored alongside each backup. Verifying the hash
  detects corruption introduced after the backup was created.
- **Retention is 7 days.** Older files are removed by the script.
- **The service runs as `root`, and the backup directory is `root:root`,
  mode `0700`.** The database is owned by `secure-app`, but the
  application user has no access to the backups: a compromise of the
  application cannot delete or replace them. `backup.sh` creates the
  directory with these permissions on every run (`install -d`).
  *History:* until 2026-10-22 the directory was owned by `secure-app`,
  which allowed a compromised application to delete or replace the
  backups and their checksums. Confirmed by test and fixed on
  2026-10-22 (see R-10 in `docs/risk-register.md`).

## Verification

Check that a backup is intact:

    sudo sha256sum -c /var/backups/secure-fullstack/lab-<timestamp>.db.sha256

Check the schedule:

    sudo systemctl list-timers backup.timer

View the last run:

    sudo journalctl -u backup.service -n 20
