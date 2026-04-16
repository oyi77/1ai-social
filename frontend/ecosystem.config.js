module.exports = {
  apps: [{
    name: '1ai-social-frontend',
    script: 'npm',
    args: 'start',
    cwd: '/home/openclaw/projects/1ai-social/frontend',
    env: {
      NODE_ENV: 'production',
      PORT: '8201',
      NEXT_PUBLIC_API_URL: 'http://localhost:8200',
      NEXT_PUBLIC_APP_NAME: '1AI Social',
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    error_file: '/home/openclaw/projects/1ai-social/frontend/logs/error.log',
    out_file: '/home/openclaw/projects/1ai-social/frontend/logs/out.log',
  }]
};
