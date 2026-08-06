# Supervisor Production Environment Configuration

This guide applies when the backend, Celery worker, and Celery beat run directly on the production host under Supervisor. It does not configure Docker Compose.

## Environment File Selection

The backend resolves its configuration file in this order:

1. The absolute path in `APP_ENV_FILE`.
2. The repository-root `.env` file when `APP_ENV_FILE` is not set.

Production processes must set `APP_ENV_FILE` to the production file explicitly. Do not choose the file from the `ENVIRONMENT` value inside the file: the process must select a file before it can read that value.

Use this layout on the production server, replacing `/srv/full-stack-fastapi-template` with the deployed repository path:

```text
/srv/full-stack-fastapi-template/
  .env_prod
  backend/
  .venv/
```

Keep `.env_prod` out of source control. Restrict it to the account that starts the application, for example with mode `600`.

## Manual Production Verification

Before adding or changing Supervisor programs, verify that the production file can be read by the deployed Python environment:

```bash
cd /srv/full-stack-fastapi-template/backend
APP_ENV_FILE=/srv/full-stack-fastapi-template/.env_prod \
  /srv/full-stack-fastapi-template/.venv/bin/python \
  -c 'from app.core.config import settings; print(settings.ENVIRONMENT)'
```

The command must print the expected production environment name and must not print any secrets.

For a temporary foreground API start, use the same variable:

```bash
cd /srv/full-stack-fastapi-template/backend
APP_ENV_FILE=/srv/full-stack-fastapi-template/.env_prod \
  /srv/full-stack-fastapi-template/.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000
```

## Supervisor Programs

Create or update the production Supervisor file, for example `/etc/supervisor/conf.d/fsft.conf`. Replace the paths, user, log directory, and any host or port values with the deployment's real values.

```ini
[program:fsft-backend]
directory=/srv/full-stack-fastapi-template/backend
command=/srv/full-stack-fastapi-template/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
user=appuser
environment=APP_ENV_FILE="/srv/full-stack-fastapi-template/.env_prod",PYTHONUNBUFFERED="1"
autostart=true
autorestart=unexpected
startsecs=5
stopasgroup=true
killasgroup=true
stdout_logfile=/var/log/supervisor/fsft-backend.log
stderr_logfile=/var/log/supervisor/fsft-backend-error.log

[program:fsft-celery-worker]
directory=/srv/full-stack-fastapi-template/backend
command=/srv/full-stack-fastapi-template/.venv/bin/celery -A app.core.celery:celery_app worker --concurrency=1 --hostname=fsft-worker@%%h
user=appuser
environment=APP_ENV_FILE="/srv/full-stack-fastapi-template/.env_prod",PYTHONUNBUFFERED="1"
autostart=true
autorestart=unexpected
startsecs=5
stopasgroup=true
killasgroup=true
stdout_logfile=/var/log/supervisor/fsft-celery-worker.log
stderr_logfile=/var/log/supervisor/fsft-celery-worker-error.log

[program:fsft-celery-beat]
directory=/srv/full-stack-fastapi-template/backend
command=/srv/full-stack-fastapi-template/.venv/bin/celery -A app.core.celery:celery_app beat --pidfile=/tmp/fsft-celerybeat.pid
user=appuser
environment=APP_ENV_FILE="/srv/full-stack-fastapi-template/.env_prod",PYTHONUNBUFFERED="1"
autostart=true
autorestart=unexpected
startsecs=5
stopasgroup=true
killasgroup=true
stdout_logfile=/var/log/supervisor/fsft-celery-beat.log
stderr_logfile=/var/log/supervisor/fsft-celery-beat-error.log
```

`%%h` is intentional: Supervisor expands `%%` to a literal `%`, allowing Celery to receive `%h` as the host placeholder.

Every Python process that imports the application must receive the same `APP_ENV_FILE`, including one-off migration or maintenance commands.

## Reload and Check

After validating the configuration syntax and paths, reload Supervisor and restart all three processes:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart fsft-backend fsft-celery-worker fsft-celery-beat
sudo supervisorctl status
```

Confirm each program reports `RUNNING`, then inspect the configured Supervisor logs. If a process fails immediately, first check that `.env_prod` exists, that `appuser` can read it, and that `APP_ENV_FILE` uses an absolute path.

## Local Development

On Windows PowerShell, select the development file before starting the backend locally:

```powershell
$env:APP_ENV_FILE = "$PWD\.env_dev"
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Start a new shell, or remove `APP_ENV_FILE`, when switching environments so the current PowerShell session does not retain the previous selection.

## Docker Compose Boundary

This configuration does not change Docker Compose. The current Compose file has its own `env_file` entries, so a Compose deployment needs a separate, explicit environment-file selection design.
