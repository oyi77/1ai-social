# 1ai-social

Social Media Automation Engine for BerkahKarya.

## Features

1. **Scheduling**: Schedule posts across X, Instagram, TikTok, LinkedIn.
2. **Planning**: Content calendar and planning.
3. **Engagement**: Automated likes, comments, follows, DMs.
4. **Analytics**: Track reach, engagement, follower growth.
5. **Multi-platform**: Single workflow, distribute everywhere.

## Supported Platforms

- X (Twitter)
- Instagram
- TikTok
- LinkedIn
- Facebook
- YouTube

## Directory Structure

- `scripts/`: Automation scripts
- `data/`: Content database
- `logs/`: Execution logs

## Usage

```bash
# Schedule a post
python3 scripts/scheduler.py --platform x --content "Hello world"

# Run engagement routine
python3 scripts/engagement.py --action like --count 20

# Generate content plan
python3 scripts/planner.py --niche "AI" --days 7
```

## Integration

Connects with:
- `1ai-ads` - Paid amplification
- `1ai-engage` - Cold outreach
- `berkahkarya-hub` - Orchestration
