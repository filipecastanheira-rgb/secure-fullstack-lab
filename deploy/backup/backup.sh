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
# Retention: 7 daily backups. Older ones are removed.

set -euo pipefail

DB_SOURCE="/var/lib/secure-fullstack/lab.db"
SECRET_SOURCE="/var/lib/secure-fullstack/.jwt_secret"
BACKUP_DIR="/var/backups/secure-fullstack"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
DB_BACKUP="${BACKUP_DIR}/lab-${TIMESTAMP}.db"
SECRET_BACKUP="${BACKUP_DIR}/jwt-${TIMESTAMP}.secret"
RETENTION_DAYS=7

mkdir -p "${BACKUP_DIR}"

# 1. Database — consistent snapshot
sqlite3 "${DB_SOURCE}" ".backup '${DB_BACKUP}'"
chmod 640 "${DB_BACKUP}"
sha256sum "${DB_BACKUP}" > "${DB_BACKUP}.sha256"

# 2. JWT secret — direct copy (small file, no concurrent writers)
cp "${SECRET_SOURCE}" "${SECRET_BACKUP}"
chmod 600 "${SECRET_BACKUP}"
sha256sum "${SECRET_BACKUP}" > "${SECRET_BACKUP}.sha256"

# 3. Retention — remove files older than RETENTION_DAYS
find "${BACKUP_DIR}" -name 'lab-*.db' -type f -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name 'jwt-*.secret' -type f -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name '*.sha256' -type f -mtime +${RETENTION_DAYS} -delete

# 4. Report
echo "Backup completed:"
echo "  Database: ${DB_BACKUP}"
echo "  Secret:   ${SECRET_BACKUP}"
ls -lh "${BACKUP_DIR}" | tail -5
