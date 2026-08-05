const path = require("node:path")

const projectRoot = __dirname.replaceAll("\\", "/")
const pm2JsonPrefix = path
  .join(projectRoot, "scripts", "pm2-json-prefix.cjs")
  .replaceAll("\\", "/")
const python = path
  .join(projectRoot, ".venv", "Scripts", "python.exe")
  .replaceAll("\\", "/")
const celery = path
  .join(projectRoot, ".venv", "Scripts", "celery.exe")
  .replaceAll("\\", "/")

const quoteArg = (value) => `"${value.replaceAll('"', '\\"')}"`
const cmdArgs = (command, args) =>
  `/c ${[process.execPath, pm2JsonPrefix, "--", command, ...args]
    .map(quoteArg)
    .join(" ")}`

module.exports = {
  apps: [
    {
      name: "fsft-backend",
      cwd: "D:/Workspace/full-stack-fastapi-template/backend",
      script: "cmd",
      args: cmdArgs(python, [
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--port",
        "8000",
      ]),
      interpreter: "none",
      min_uptime: 5000,
      max_restarts: 3,
      restart_delay: 3000,
      time: false,
      env: {
        PYTHONUNBUFFERED: "1"
      },
      env_production: {
        APP_ENV_FILE: "D:/Workspace/full-stack-fastapi-template/.env.production"
      }
    },
    {
      name: "fsft-frontend-dev",
      cwd: "D:/Workspace/full-stack-fastapi-template/frontend",
      script: "cmd",
      args: "/c bun run dev --host 0.0.0.0",
      interpreter: "none",
      min_uptime: 5000,
      max_restarts: 3,
      restart_delay: 3000,
      time: true,
      env: {
        VITE_API_URL: "http://localhost:8000"
      }
    },
    {
      name: "fsft-celery-worker",
      cwd: "D:/Workspace/full-stack-fastapi-template/backend",
      script: "cmd",
      args: cmdArgs(celery, [
        "-q",
        "-A",
        "app.core.celery:celery_app",
        "worker",
        "--pool=solo",
        "--concurrency=1",
      ]),
      interpreter: "none",
      min_uptime: 5000,
      max_restarts: 3,
      restart_delay: 3000,
      time: false,
      env: {
        PYTHONUNBUFFERED: "1"
      },
      env_production: {
        APP_ENV_FILE: "D:/Workspace/full-stack-fastapi-template/.env.production"
      }
    },
    {
      name: "fsft-celery-beat",
      cwd: "D:/Workspace/full-stack-fastapi-template/backend",
      script: "cmd",
      args: cmdArgs(celery, ["-q", "-A", "app.core.celery:celery_app", "beat"]),
      interpreter: "none",
      min_uptime: 5000,
      max_restarts: 3,
      restart_delay: 3000,
      time: false,
      env: {
        PYTHONUNBUFFERED: "1"
      },
      env_production: {
        APP_ENV_FILE: "D:/Workspace/full-stack-fastapi-template/.env.production"
      }
    }
  ]
}
