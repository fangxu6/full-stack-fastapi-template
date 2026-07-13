module.exports = {
  apps: [
    {
      name: "fsft-backend",
      cwd: "D:/Workspace/full-stack-fastapi-template/backend",
      script: "cmd",
      args: "/c D:/Workspace/full-stack-fastapi-template/.venv/Scripts/python.exe -m uvicorn app.main:app --reload",
      interpreter: "none",
      min_uptime: 5000,
      max_restarts: 10,
      restart_delay: 3000,
      time: true,
      env: {
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "fsft-frontend-dev",
      cwd: "D:/Workspace/full-stack-fastapi-template/frontend",
      script: "cmd",
      args: "/c bun run dev --host 0.0.0.0",
      interpreter: "none",
      min_uptime: 5000,
      max_restarts: 10,
      restart_delay: 3000,
      time: true,
      env: {
        VITE_API_URL: "http://localhost:8000"
      }
    }
  ]
}
