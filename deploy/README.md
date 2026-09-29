# Deployment

Configuration files for running the application as system services.

## Services

| Service                          | Runs                      | Port | Notes                             |
|----------------------------------|---------------------------|------|-----------------------------------|
| `secure-fullstack-api.service`   | FastAPI backend (uvicorn) | 8000 | Managed by systemd                |
| Nginx                            | Serves Vue build + proxy  | 80   | Installed from apt, own service   |

**Note:** the frontend is no longer run as a systemd service. It is compiled
with `npm run build` and served as static files by Nginx. See the Nginx
configuration in `/etc/nginx/sites-available/secure-fullstack` (a copy should
be kept in `deploy/nginx/` once created).

## Install the API service on a new machine

1. Copy the service file:

        sudo cp deploy/systemd/secure-fullstack-api.service /etc/systemd/system/

2. Reload systemd:

        sudo systemctl daemon-reload

3. Enable at boot:

        sudo systemctl enable secure-fullstack-api.service

4. Start now:

        sudo systemctl start secure-fullstack-api.service

5. Check status:

        sudo systemctl status secure-fullstack-api.service

## Nginx setup (summary)

1. Install:

        sudo apt install -y nginx

2. Create `/etc/nginx/sites-available/secure-fullstack` with:
   - root pointing at `frontend/dist/`
   - `location /api/` proxying to `http://127.0.0.1:8000`
   - SPA fallback (`try_files $uri $uri/ /index.html`)

3. Enable the site:

        sudo ln -s /etc/nginx/sites-available/secure-fullstack /etc/nginx/sites-enabled/
        sudo rm /etc/nginx/sites-enabled/default
        sudo nginx -t
        sudo systemctl reload nginx

4. Rebuild the frontend whenever the source changes:

        cd frontend
        npm run build

## Common operations

        # Restart the backend after a code change
        sudo systemctl restart secure-fullstack-api.service

        # Reload Nginx after editing its config (no downtime)
        sudo nginx -t && sudo systemctl reload nginx

        # Follow logs
        journalctl -u secure-fullstack-api.service -f
        tail -f /var/log/nginx/secure-fullstack.access.log
        tail -f /var/log/nginx/secure-fullstack.error.log

## Notes

- The service files here are **copies**. The real files live in
  `/etc/systemd/system/`. When you edit one, edit it there first, then copy
  it back here and commit.
- `ExecStart` uses **absolute paths**. `~` and shell variables are not
  expanded by systemd.
- The `User=` and `Group=` in the API service mean the process runs as a
  normal user, **not as root**.
- **Temporary permission note:** Nginx (`www-data`) needs to traverse
  `/home/filipe/` to reach `frontend/dist/`. This was solved with
  `chmod o+x /home/filipe`. In a later hardening session, the built assets
  should be moved to `/var/www/secure-fullstack/` so this permission can be
  revoked.
