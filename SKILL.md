# Skill: 1ai-social

**Base directory**: /home/openclaw/projects/1ai-social

Social media automation engine for organic audience growth.

## Usage

This skill allows AI agents to:
1. Schedule posts across platforms
2. Run engagement automation
3. Plan content calendars
4. Track analytics

## Available Tools

### scheduler
Schedule content for posting.
- `platform` (required): "x", "instagram", "tiktok", "linkedin"
- `content` (required): Post content
- `media` (optional): Path to media file
- `schedule_time` (optional): ISO timestamp

### engagement
Run engagement actions.
- `action` (required): "like", "comment", "follow", "unfollow", "dm"
- `platform` (required): Platform to engage on
- `target` (optional): Target account or hashtag

### planner
Generate content calendar.
- `niche` (required): Content niche
- `days` (optional): Number of days (default: 7)

## Integration

To add to OpenClaw:

```json
{
  "mcpServers": {
    "1ai-social": {
      "command": "python3",
      "args": ["/home/openclaw/projects/1ai-social/mcp_server.py"]
    }
  }
}
```
