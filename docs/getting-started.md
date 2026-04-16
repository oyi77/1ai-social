# Getting Started

Welcome to 1AI Social! This guide will help you set up and start using the platform to automate your social media content.

## Prerequisites

Before you begin, make sure you have:

- **Python 3.11 or higher** installed
- **PostgreSQL 14+** database server
- **Redis 6+** for caching and background jobs
- **Docker and Docker Compose** (recommended for local development)
- A code editor (VS Code, PyCharm, etc.)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/1ai-social.git
cd 1ai-social
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file and update it with your settings:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/1ai_social

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# AI Provider (choose one)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Social Platform Credentials
TWITTER_API_KEY=your-twitter-key
TWITTER_API_SECRET=your-twitter-secret
INSTAGRAM_CLIENT_ID=your-instagram-id
INSTAGRAM_CLIENT_SECRET=your-instagram-secret
```

### 4. Initialize the Database

```bash
# Run migrations
alembic upgrade head

# (Optional) Seed with sample data
python scripts/seed_data.py
```

## First Run

### Using Docker Compose (Recommended)

The easiest way to get started is with Docker Compose:

```bash
docker-compose up
```

This starts:
- Web application on `http://localhost:8000`
- PostgreSQL database
- Redis cache
- Background worker for scheduled posts

### Manual Start

If you prefer to run services separately:

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start PostgreSQL
pg_ctl -D /usr/local/var/postgres start

# Terminal 3: Start the web app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 4: Start the background worker
celery -A app.worker worker --loglevel=info
```

## Connect Your First Social Account

1. **Open the application** at `http://localhost:8000`

2. **Create an account** or log in

3. **Navigate to Settings** → **Connected Accounts**

4. **Click "Connect Account"** and choose a platform:
   - **X (Twitter)**: Authorize via OAuth
   - **Instagram**: Connect via Facebook Business
   - **TikTok**: Authorize via TikTok for Business
   - **LinkedIn**: Connect via LinkedIn OAuth

5. **Follow the OAuth flow** to grant permissions

6. **Verify connection** by checking the green checkmark next to the platform

## Create Your First Post

### Quick Post

1. Go to **Dashboard** → **Create Post**

2. Choose your content type:
   - Write manually
   - Generate with AI
   - Upload media

3. Select target platforms (you can post to multiple at once)

4. Click **Post Now** or **Schedule for Later**

### AI-Generated Content

1. Click **Generate with AI**

2. Enter a topic or prompt:
   ```
   "Write a motivational post about productivity"
   ```

3. Review the generated content

4. Edit if needed

5. Select platforms and post

### Schedule a Post

1. Create your post content

2. Click **Schedule**

3. Choose date and time

4. Select timezone

5. Click **Schedule Post**

Your post will be automatically published at the scheduled time.

## Next Steps

- Explore [Features](features.md) to learn about advanced capabilities
- Set up [Campaigns](features.md#campaigns) for recurring content
- Configure [Analytics](features.md#analytics) to track performance
- Check out [Deployment](deployment.md) for production setup

## Getting Help

- Check the [FAQ](faq.md) for common questions
- Report issues on GitHub
- Join our community Discord

Happy posting! 🚀
