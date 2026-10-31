# Container

Containerised backend for the Secure Fullstack Lab.

## What is here

| File | Purpose |
|------|---------|
| `Containerfile` | Defines the image: python:3.14-slim, non-root user, app code, venv |

## Why containerise only the backend?

The frontend is served by Nginx as static files. The Nginx process is
already running on the host. Containerising the frontend would mean
running a container just to serve static files, which adds complexity
without adding security or functionality. The backend is the piece
that runs arbitrary Python code and handles the database, so it is the
piece worth putting in a container.

## Build

    podman build -t secure-fullstack-api:0.3 -f deploy/container/Containerfile ./backend

## Run

    podman run -d --name secure-api-test \
      -p 8001:8000 \
      -v /tmp/container-data:/var/lib/secure-fullstack \
      --tmpfs /tmp \
      localhost/secure-fullstack-api:0.3

The `-v` mount maps the host directory where the database and JWT
secret are stored. The `--tmpfs` is for temporary files that the
application may write; the rest of the filesystem is read-only by
default because the image does not contain a writable layer.

Update 2026-10-31: the statement above is wrong. The command shown does
not use `--read-only`, so the container has a writable layer.
`--read-only` was dropped for the test run because SQLite needs to create
a journal file next to the database (see Session 24 in
`docs/JOURNAL.md`), and the read-only root filesystem is listed as
deferred in the main README. The `--tmpfs /tmp` and the `-v` mount are as
described. Not tested: whether `--read-only` combined with the `-v` mount
and `--tmpfs /tmp` would work.

## Scan for vulnerabilities

    trivy image --image-src podman localhost/secure-fullstack-api:0.3

**Known Trivy cache issue:** if the scan reports Python vulnerabilities
that are not present in the image, run `trivy image --image-src podman
--clear-cache localhost/secure-fullstack-api:0.3`. Trivy caches layer
metadata and can misreport packages that were upgraded in a later layer.

## Scan results (as of 2026-10-18)

| Component | Total | CRITICAL | HIGH | MEDIUM | LOW |
|-----------|-------|----------|------|--------|-----|
| Debian base | 166 | 0 | 44 | 58 | 61 |
| Python packages | 0 | 0 | 0 | 0 | 0 |

**Note on the Debian base vulnerabilities.** These are inherited from
the `python:3.14-slim` image. They cannot be fixed from this
repository: they require a newer base image from the upstream Python
project. In a production deployment, the base image would be updated
on a schedule and the vulnerabilities tracked in the risk register.
For the lab, they are documented as a known limitation of the base
image.

## Run as non-root

The Containerfile creates a dedicated user `appuser` (UID 10001) and
switches to it before running uvicorn. The container does not run as
root. This means that a compromise of the application does not give
root access inside the container, and the container itself cannot
modify its own filesystem.

## Related

- `docs/JOURNAL.md` session 24 — the record of the containerisation
  work.
