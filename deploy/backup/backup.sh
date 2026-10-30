#!/usr/bin/env bash
#
# Backup the Secure Fullstack Lab database and JWT secret.
#
# Uses 'sqlite3 .backup' instead of 'cp'. The '.backup' command asks the
# SQLite engine to produce a consistent snapshot, even if a write is in
# progress. A plain 'cp' can produce a corrupted file: half the pages
# before the write, half after.
#
# The .jwt_secret is included because without it the application cannot
# start (it would generate a new one, invalidating every previously
# issued token and every stored refresh token).
#
# Both files are encrypted with age for the public keys in
# /etc/secure-fullstack/backup-recipients.txt. The private key is on this
# machine (/root/backup-age/), so the encryption protects copies of the
# backups that leave it, not the backups against root on this machine.
#
# Retention: 7 daily backups. Older ones are removed.

set -euo pipefail

DB_SOURCE="/var/lib/secure-fullstack/lab.db"
SECRET_SOURCE="/var/lib/secure-fullstack/.jwt_secret"
BACKUP_DIR="/var/backups/secure-fullstack"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
DB_BACKUP="${BACKUP_DIR}/lab-${TIMESTAMP}.db.age"
SECRET_BACKUP="${BACKUP_DIR}/jwt-${TIMESTAMP}.secret.age"
RETENTION_DAYS=7
RECIPIENTS="/etc/secure-fullstack/backup-recipients.txt"
PLAIN_TMP="${BACKUP_DIR}/.lab-plain.tmp"

# The plaintext snapshot only exists as a temporary file in the backup
# directory and is removed when the script exits, even on failure.
trap 'rm -f "${PLAIN_TMP}"' EXIT

# Never fall back to a plaintext backup.
if [ ! -r "${RECIPIENTS}" ]; then
    echo "Recipients file not readable: ${RECIPIENTS}" >&2
    exit 1
fi

# The backup directory must be owned by root and closed to everyone else.
# If the application user could write here, a compromised application
# could delete or replace the backups and their checksums.
install -d -m 700 -o root -g root "${BACKUP_DIR}"

# 1. Database — consistent snapshot, encrypted with age
sqlite3 "${DB_SOURCE}" ".backup '${PLAIN_TMP}'"
age -R "${RECIPIENTS}" -o "${DB_BACKUP}" "${PLAIN_TMP}"
rm -f "${PLAIN_TMP}"
chmod 640 "${DB_BACKUP}"
sha256sum "${DB_BACKUP}" > "${DB_BACKUP}.sha256"

# 2. JWT secret — encrypted straight from the source (small file, no
# concurrent writers), so no plaintext copy is written
age -R "${RECIPIENTS}" -o "${SECRET_BACKUP}" "${SECRET_SOURCE}"
chmod 600 "${SECRET_BACKUP}"
sha256sum "${SECRET_BACKUP}" > "${SECRET_BACKUP}.sha256"

# 3. Retention — remove files older than RETENTION_DAYS
find "${BACKUP_DIR}" \( -name 'lab-*.db' -o -name 'lab-*.db.age' \) -type f -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" \( -name 'jwt-*.secret' -o -name 'jwt-*.secret.age' \) -type f -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name '*.sha256' -type f -mtime +${RETENTION_DAYS} -delete

# 4. Report
echo "Backup completed:"
echo "  Database: ${DB_BACKUP}"
echo "  Secret:   ${SECRET_BACKUP}"
ls -lh "${BACKUP_DIR}" | tail -5
