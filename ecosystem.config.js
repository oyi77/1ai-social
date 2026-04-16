module.exports = {
  apps: [{
    name: '1ai-social',
    script: 'python3',
    args: '-m 1ai_social.mcp_server',
    cwd: '/home/openclaw/projects/1ai-social',
    env: {
      MCP_TRANSPORT: 'http',
      PORT: '8200',
      HOST: '0.0.0.0',
      DATABASE_URL: 'postgresql://localhost/1ai_social',
      REDIS_URL: 'redis://localhost:6379/0',
      SECRET_KEY: 'change-me-in-production',
      ENCRYPTION_KEY: '',
      SENTRY_DSN: '',
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    error_file: '/home/openclaw/projects/1ai-social/logs/error.log',
    out_file: '/home/openclaw/projects/1ai-social/logs/out.log',
  }]
};
