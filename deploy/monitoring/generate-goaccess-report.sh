#!/usr/bin/env bash
#
# Generate a GoAccess HTML report from the Nginx access log.
#
# Runs as root, because:
#   - the Nginx access log is owned by www-data:adm and not readable by
#     the operator user
#   - the output directory /var/lib/goaccess/ is owned by root
#
# The report is intentionally NOT served by Nginx. It contains client
# IPs, request paths, and user agents — information that would help an
# attacker profile the application. It lives in /var/lib/goaccess/ and
# is accessed on the host or copied off-band.

set -euo pipefail

LOG_FILE="/var/log/nginx/secure-fullstack.access.log"
OUTPUT_DIR="/var/lib/goaccess"
OUTPUT_FILE="${OUTPUT_DIR}/report.html"
# GoAccess requires the output file to end in .html, .csv, or .json.
# So the temporary file also ends in .html, but its name differs from
# the final file to keep the atomic-rename property.
TMP_FILE="${OUTPUT_DIR}/report.partial.html"

mkdir -p "${OUTPUT_DIR}"
chmod 755 "${OUTPUT_DIR}"

if [ ! -s "${LOG_FILE}" ]; then
    echo "Log file is empty or missing: ${LOG_FILE}" >&2
    echo "Nothing to report. Skipping generation." >&2
    exit 0
fi

# Generate to a temporary file first, then rename atomically. A reader
# never sees a half-written report.
goaccess "${LOG_FILE}" \
    --log-format=COMBINED \
    --output="${TMP_FILE}" \
    --ignore-crawlers

mv "${TMP_FILE}" "${OUTPUT_FILE}"
chmod 640 "${OUTPUT_FILE}"

echo "Report generated: ${OUTPUT_FILE}"
ls -la "${OUTPUT_FILE}"
