# Database Migrations

This directory contains Alembic database migrations for 1ai-social.

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Upgrade to latest schema
alembic upgrade head

# Downgrade one migration
alembic downgrade -1

# View migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "Description of changes"
```

## Migration Files

- `001_initial_schema.py` - Initial schema with all tables (platforms, contents, hooks, posts, analytics_records)

## Tables

### platforms
- id (PK)
- name (unique)
- credentials
- user_id
- tenant_id (nullable, Wave 3)
- created_at, updated_at

### contents
- id (PK)
- text
- platform
- media_url, video_path, video_duration, video_format, video_width, video_height
- hashtags, mentions (JSON as text)
- tenant_id (nullable, Wave 3)
- created_at

### hooks
- id (PK)
- content_id (FK)
- platform_id (FK)
- text, confidence, type
- tenant_id (nullable, Wave 3)
- created_at

### posts
- id (PK, string)
- content_id (FK)
- platform_id (FK)
- scheduled_time, published_time
- status, platform_post_id, error_message
- tenant_id (nullable, Wave 3)
- created_at, updated_at

### analytics_records
- id (PK)
- post_id (FK)
- platform_id (FK)
- content_type, views, likes, shares, comments, engagement_rate
- tenant_id (nullable, Wave 3)
- recorded_at

## Wave 3: Multi-Tenancy

All tables include a `tenant_id` column (nullable) for future multi-tenancy support. Wave 3 will populate this column and add constraints.

## Testing Migrations

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Verify tables exist
psql -d 1ai_social -c "\dt"
```
