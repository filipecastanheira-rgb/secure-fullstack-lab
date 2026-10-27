#!/usr/bin/env bash
#
# Correlation check for the Secure Fullstack Lab.
#
# Reads TWO log sources and looks for patterns that deserve attention:
#
#   1. Nginx access log (COMBINED format) — what arrived at the edge,
#      including requests refused by the rate limiter (429) which never
#      reach the application.
#
#   2. FastAPI structured log (JSON) — what the application handled,
#      including authenticated requests with a user id, and application
#      errors.
#
# Neither source is complete on its own. The rate limiter acts at the
# Nginx layer; when it blocks a request, the application never sees it.
# A detection script that reads only the FastAPI log would miss every
# rate-limited request. A script that reads only the Nginx log would
# miss the user id associated with an application error.
#
# The two are correlated by time window, not by request id (this lab does
# not propagate request ids). For the alert classes implemented here,
# that is sufficient.
#
# Alerts are written to /var/log/secure-fullstack/alerts.log and to
# stdout (which systemd captures into the journal for this unit).

set -euo pipefail

# --- Configuration ----------------------------------------------------------

LOOKBACK="6 minutes ago"
API_UNIT="secure-fullstack-api.service"
NGINX_LOG="/var/log/nginx/secure-fullstack.access.log"
ALERTS_LOG="/var/log/secure-fullstack/alerts.log"

THRESHOLD_429=10         # rate-limited requests at the Nginx edge
THRESHOLD_401_PER_IP=20  # failed auths from a single IP (from FastAPI)
THRESHOLD_5XX=5          # server errors of any kind (from FastAPI)

# --- Setup ------------------------------------------------------------------

mkdir -p "$(dirname "${ALERTS_LOG}")"
touch "${ALERTS_LOG}"
chmod 640 "${ALERTS_LOG}"

emit_alert() {
    local category="$1"
    local message="$2"
    local details="$3"
    local timestamp
    timestamp="$(date --iso-8601=seconds)"

    printf '%s [%s] %s\n' "${timestamp}" "${category}" "${message}" \
        >> "${ALERTS_LOG}"
    if [ -n "${details}" ]; then
        printf '    %s\n' "${details}" >> "${ALERTS_LOG}"
    fi

    echo "ALERT [${category}] ${message}"
    if [ -n "${details}" ]; then
        echo "    ${details}"
    fi
}

# --- Source 1: Nginx access log (edge) --------------------------------------

# awk filters the access log by time window and by status code. The
# timestamp ($4, e.g. "[19/Oct/2026:20:02:11") is converted by hand to a
# sortable YYYYMMDDHHMMSS key and compared with the cutoff, so only the
# last LOOKBACK is counted. Nginx logs in server local time, which is also
# what `date` uses here. No awk time functions are needed, so it works
# with both mawk (the Ubuntu default) and gawk.

if [ -r "${NGINX_LOG}" ]; then
    # Keep only the lines inside the lookback window.
    CUTOFF="$(date -d "${LOOKBACK}" +%Y%m%d%H%M%S)"
    NGINX_RECENT="$(awk -v cutoff="${CUTOFF}" '
        BEGIN {
            cutoff = cutoff ""
            n = split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", names, " ")
            for (i = 1; i <= n; i++) mon[names[i]] = sprintf("%02d", i)
        }
        {
            split(substr($4, 2), a, /[\/:]/)
            if (!(a[2] in mon)) next
            key = a[3] mon[a[2]] a[1] a[4] a[5] a[6]
            if (key >= cutoff) print
        }
    ' "${NGINX_LOG}")"

    # 429s — the rate limiter fired. These requests never reached FastAPI.
    COUNT_429="$(awk '$9 == 429' <<< "${NGINX_RECENT}" | wc -l)"
    if [ "${COUNT_429}" -gt "${THRESHOLD_429}" ]; then
        TOP_PATHS="$(awk '$9 == 429 {print $7}' <<< "${NGINX_RECENT}" \
            | sort | uniq -c | sort -rn | head -3 \
            | awk '{print $2" ("$1")"}' | paste -sd, -)"
        TOP_IPS="$(awk '$9 == 429 {print $1}' <<< "${NGINX_RECENT}" \
            | sort | uniq -c | sort -rn | head -3 \
            | awk '{print $2" ("$1")"}' | paste -sd, -)"
        emit_alert "429_BURST" \
            "${COUNT_429} requests were rate-limited at the Nginx edge" \
            "top paths: ${TOP_PATHS}; top IPs: ${TOP_IPS}"
    fi
else
    echo "Nginx log not readable: ${NGINX_LOG}" >&2
fi

# --- Source 2: FastAPI structured log (application) -------------------------

LOG_JSON="$(journalctl -u "${API_UNIT}" --since "${LOOKBACK}" --no-pager -o cat 2>/dev/null \
    | grep '"event": "http_request"' \
    || true)"

if [ -n "${LOG_JSON}" ]; then

    # 401s by source IP — credential guessing against the application.
    echo "${LOG_JSON}" \
        | jq -r 'select(.status_code == 401) | .client_ip' \
        | sort | uniq -c | sort -rn \
        | while read -r count ip; do
            if [ "${count}" -gt "${THRESHOLD_401_PER_IP}" ]; then
                emit_alert "401_BURST" \
                    "${count} failed authentications from ${ip}" \
                    ""
            fi
        done

    # 5xx — application errors. Not an attack, but a signal.
    COUNT_5XX="$(echo "${LOG_JSON}" | jq -r 'select(.status_code >= 500) | .path' | wc -l)"
    if [ "${COUNT_5XX}" -gt "${THRESHOLD_5XX}" ]; then
        PATHS_5XX="$(echo "${LOG_JSON}" | jq -r 'select(.status_code >= 500) | .path' \
            | sort | uniq -c | sort -rn | awk '{print $2" ("$1")"}' | paste -sd, -)"
        emit_alert "5XX_BURST" \
            "${COUNT_5XX} server errors since ${LOOKBACK}" \
            "paths: ${PATHS_5XX}"
    fi
fi

exit 0
