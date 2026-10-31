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

**Scope of this number:** the restore was manual, performed on
2026-10-17 on the same machine that holds the backups, with a 28 KB
database. It does not include recovering a lost machine, fetching
backups from elsewhere or decrypting them.

*Update 2026-10-30:* backups are now encrypted with age, and the
restore starts with a decryption step:

    sudo age -d -i /root/backup-age/backup-key.txt -o /var/lib/secure-fullstack/lab.db /var/backups/secure-fullstack/lab-<timestamp>.db.age
    sudo chown secure-app:secure-app /var/lib/secure-fullstack/lab.db
    sudo chmod 640 /var/lib/secure-fullstack/lab.db
    sudo systemctl restart secure-fullstack-api.service

Measured with `time` around these four commands: 0.698 s, with a 45 KB
database, on the same machine, with the API unit sandboxed as of
2026-10-30. This is not a like-for-like comparison with the 1.4 s above
(different database size, different unit, and the `cp` is replaced by
the decryption). Decrypting alone took 0.02 s. Afterwards the SQLite
integrity check returned `ok` and the login endpoint returned 200. The
private key is on the same machine, so the time to fetch a key from
elsewhere is not part of this number.

## How the backup works

- **`sqlite3 .backup`** is used for the database, not `cp`. The
  `.backup` command asks the SQLite engine for a consistent snapshot
  even if a write is in progress. A `cp` can produce a file that is
  half-before and half-after a transaction.
- **SHA256** is stored alongside each backup. Verifying the hash
  detects corruption introduced after the backup was created. It proves
  integrity, not that the backup can be restored, and the hash sits in
  the same directory as the file it protects.
- **Retention is 7 days.** Older files are removed by the script.
- *Update 2026-10-31:* The retention logic (`find -mtime +7`) has not yet been observed deleting a file. The 24 plaintext backups (12 database, 12 JWT secret) dated 2026-10-23 to 2026-10-30 are still present because none has yet crossed the exact 7-day threshold at 03:00 (the timer schedule); they will be deleted starting 2026-11-01. This is expected behaviour, not a failure.
- **The service runs as `root`, and the backup directory is `root:root`,
  mode `0700`.** The database is owned by `secure-app`, but the
  application user has no access to the backups: a compromise of the
  application cannot delete or replace them. `backup.sh` creates the
  directory with these permissions on every run (`install -d`).
  *History:* until 2026-10-22 the directory was owned by `secure-app`,
  which allowed a compromised application to delete or replace the
  backups and their checksums. Confirmed by test and fixed on
  2026-10-22 (see R-10 in `docs/risk-register.md`).

## Limitations

- Backups are on the same machine as the data, so losing the machine
  loses both.
- Backups are not encrypted, and the JWT secret is stored next to the
  database. Protection is file permissions only.
  *Update 2026-10-30:* the database and the JWT secret are now
  encrypted with age (`.age` files) for the public key in
  `deploy/backup/recipients.txt`, installed as
  `/etc/secure-fullstack/backup-recipients.txt`. The private key is on
  the same machine (`/root/backup-age/backup-key.txt`, root, mode 600),
  so the encryption protects copies of the backups that leave the
  machine, not the backups against root on it. It was kept there on
  purpose: for a lab with one operator, a lost key would mean losing
  every backup. There is no second recovery key. `backup.sh` stops if
  the recipients file is missing and never writes a plaintext backup.
  The SHA-256 files are now computed over the encrypted files.
  Backups made before 2026-10-30 19:42 are plaintext and are removed by
  the 7-day retention, which now covers both formats.
- Accepted for the lab, with the rationale and the production design,
  in AR-07 (`docs/risk-register.md`).

## Verification

Check that a backup is intact:

    sudo sha256sum -c /var/backups/secure-fullstack/lab-<timestamp>.db.sha256

*Update 2026-10-30:* for encrypted backups the file is
`lab-<timestamp>.db.age.sha256`. The hash is over the encrypted file, so
it can be checked without the private key.

Check the schedule:

    sudo systemctl list-timers backup.timer

View the last run:

    sudo journalctl -u backup.service -n 20
