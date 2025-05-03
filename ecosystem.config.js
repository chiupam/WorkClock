module.exports = {
  apps: [{
    name: "work",
    script: "python",
    args: "-m uvicorn app.main:app --host 0.0.0.0 --port 8000",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: "500M",
    env: {
      NODE_ENV: "production",
      PYTHONPATH: "/app"
    },
    log_date_format: "YYYY-MM-DD HH:mm:ss Z"
  }]
}; 