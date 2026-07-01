# Wealth Deployment Notes

This directory tracks the local LAN deployment files for `/home/lewis/wealth`.

## Deployment assumptions

- This app is deployed as a single-user site.
- The first registered account becomes the owner account.
- The owner account is stored as `users.role = 'admin'`.
- `admin` only gates system-management tools such as backup, scraper controls, version status, and audit logs.

## Topology

- Frontend static files: `/home/lewis/wealth/frontend/dist`
- Nginx site config: `/etc/nginx/sites-enabled/wealth`
- Backend service: `wealth-backend.service`
- Backend listen address: `127.0.0.1:8000`
- LAN entrypoint: `http://192.168.0.215/`
- API proxy path: `http://192.168.0.215/api/*`

Nginx serves the Vite build directly and rewrites `/api/*` to the FastAPI backend without the `/api` prefix.

## Backend systemd service

Tracked source:

```bash
/home/lewis/wealth/deploy/wealth-backend.service
```

Install or update:

```bash
sudo cp /home/lewis/wealth/deploy/wealth-backend.service /etc/systemd/system/wealth-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now wealth-backend.service
```

Check status:

```bash
systemctl is-enabled wealth-backend.service
systemctl is-active wealth-backend.service
systemctl status wealth-backend.service --no-pager -l
```

Read logs:

```bash
journalctl -u wealth-backend.service -n 100 --no-pager
```

## Nginx site

Tracked source:

```bash
/home/lewis/wealth/deploy/nginx-wealth.conf
```

Install or update:

```bash
sudo cp /home/lewis/wealth/deploy/nginx-wealth.conf /etc/nginx/sites-available/wealth
sudo ln -sfn /etc/nginx/sites-available/wealth /etc/nginx/sites-enabled/wealth
sudo nginx -t
sudo systemctl reload nginx
```

## Frontend build

```bash
cd /home/lewis/wealth/frontend
npm run build
```

## Verification

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://192.168.0.215/api/health
curl -I http://192.168.0.215/
```

Expected results:

- Backend health returns `200 OK`
- LAN API health returns `200 OK`
- LAN frontend returns `200 OK`

## Owner account checks

After first-time setup:

```bash
sqlite3 /home/lewis/wealth/backend/wealth.db "select id, username, role, created_at from users order by id;"
```

Expected result:

- The first account should show `role=admin`
- Later accounts, if any, should default to `role=user`

## Rollback

Disable the backend service:

```bash
sudo systemctl disable --now wealth-backend.service
```

Start backend manually:

```bash
cd /home/lewis/wealth/backend
/home/lewis/wealth/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Restore Nginx by copying a known-good config back to `/etc/nginx/sites-available/wealth`, then run:

```bash
sudo nginx -t
sudo systemctl reload nginx
```
