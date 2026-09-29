# Deployment

Configuration files for running the application as system services.

## Services

| Service                          | Runs                          | Port |
|----------------------------------|-------------------------------|------|
| `secure-fullstack-api.service`   | FastAPI backend (uvicorn)     | 8000 |
| `secure-fullstack-web.service`   | Vue frontend (Vite dev server)| 5173 |

## Install on a new machine

1. Copy the service files to systemd:

        sudo cp deploy/systemd/*.service /etc/systemd/system/

2. Reload systemd so it picks up the new files:

        sudo systemctl daemon-reload

3. Enable them at boot:

        sudo systemctl enable secure-fullstack-api.service secure-fullstack-web.service

4. Start them now:

        sudo systemctl start secure-fullstack-api.service secure-fullstack-web.service

5. Check status:

        sudo systemctl status secure-fullstack-api.service secure-fullstack-web.service

## Common operations

        # Restart the backend after a code change
        sudo systemctl restart secure-fullstack-api.service

        # Follow logs in real time
        journalctl -u secure-fullstack-api.service -f
        journalctl -u secure-fullstack-web.service -f

        # Logs from the last 10 minutes
        journalctl -u secure-fullstack-api.service --since "10 min ago"

        # Stop / start without uninstalling
        sudo systemctl stop secure-fullstack-api.service
        sudo systemctl start secure-fullstack-api.service

## Notes

- The service files here are **copies**. The real files live in
  `/etc/systemd/system/`. When you edit one, edit it there first, then copy
  it back here and commit.
- `ExecStart` uses **absolute paths**. `~` and shell variables are not
  expanded by systemd.
- The `User=` and `Group=` in the API service mean the process runs as a
  normal user, **not as root**. It only needs to bind a high port and read
  project files — no privilege elevation.
- The `web.service` runs the **Vite development server**, which is fine for a
  lab but is **not production-grade**. When Nginx is introduced, this service
  will be replaced: the frontend will be compiled with `npm run build` and
  served as static files by Nginx.
