# 1ai-social: Comprehensive Content Engine Plan

## Executive Summary

Building a unified social media automation engine that combines:
- **larry-playbook** (viral content formula - 234K views proven)
- **content-generator** (video generation pipeline)
- **berkahkarya-saas-bot** (Telegram bot with payment + video)
- **social-media-engagement** (audience interaction)
- **social-media-upload** (multi-platform distribution)

---

## Part A: Integration Sources

### A1. Content Generation Skills (from ~/.opencode/skills/content/)

| Skill | Function | Use in 1ai-social |
|-------|----------|---------------------|
| `larry-playbook` | Viral TikTok formula (234K+ views), confidence system, memory/learning | **CORE** - viral hooks + content strategy |
| `content-generator` | NVIDIA → BytePlus → FFmpeg pipeline | Video generation |
| `humanizer` | Natural tone captions | Caption polishing |
| `faceless-youtube` | YouTube automation | Platform destination |
| `ai-newsletter` | Newsletter automation | Content repurposing |
| `seedance` | BytePlus video | Video provider |
| `grok-video-generation` | Grok video | Alternative video |

### A2. Social Media Skills (from ~/.opencode/skills/marketing/)

| Skill | Function | Use in 1ai-social |
|-------|----------|---------------------|
| `social-media-engagement` | Likes, comments, follows, DMs | Audience interaction |
| `social-media-upload` | Multi-platform distribution | Post distribution |
| `twitter-automation` | Twitter automation | Platform-specific |
| `content-scheduler` | Content scheduling | Scheduling layer |

### A3. berkahkarya-saas-bot (from ~/projects/)

**HUGE RESOURCE** - Contains:
- Telegram bot for user interaction
- Video generation via Kling, Runway, etc.
- Payment integration (Midtrans, Tripay)
- Affiliate system
- Direct social media publishing capability
- User credit system

### A4. viraloop Reference
- Source: https://github.com/mutonby/viraloop
- Purpose: Viral content automation patterns
- Integration: Study for best practices

---

## Part B: Architecture Design

### B1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      1ai-social Engine                        │
├─────────────────────────────────────────────────────────────────────┤
│  Input Layer                                                  │
│  ├── User (Telegram/CLI/API)                               │
│  ├── Scheduler (cron-based)                                  │
│  └── Webhook (from berkahkarya-saas-bot)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Orchestrator Layer                                          │
│  ├── content_planner.py    → Generate content calendar        │
│  ├── viral_generator.py  → Generate using larry-playbook    │
│  ├── video_pipeline.py   → Generate video (content-gen)     │
│  ├── caption_polisher.py → Humanize captions               │
│  └── post_distributor.py → Upload to platforms            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Integration Layer                                           │
│  ├── larry_playbook_client   → viral hooks + confidence   │
│  ├── content_generator_client → video generation          │
│  ├── humanizer_client        → caption polishing          │
│  ├── social_upload_client    → multi-platform posting     │
│  ├── engagement_client      → likes/comments/follows      │
│  └── berkahkarya_client    → bot + payment + user mgmt   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  Output Layer                                               │
│  ├── X (Twitter)                                           │
│  ├── Instagram                                             │
│  ├── TikTok                                                │
│  ├── LinkedIn                                             │
│  └── Facebook                                             │
└─────────────────────────────────────────────────────────────┘
```

### B2. Data Flow

```
User Request: "Generate viral content for AI niche"
         │
         ▼
┌─────────────────────────────────────────┐
│  1. Viral Generator (larry-playbook)    │
│     - Generate hooks (confidence-based) │
│     - Select proven formula            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  2. Video Pipeline (content-generator) │
│     - NVIDIA image (if needed)         │
│     - BytePlus Seedance video         │
│     - FFmpeg loop + compress          │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  3. Caption Polisher (humanizer)     │
│     - Platform-specific captions       │
│     - Hashtag optimization           │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  4. Post Distributor                  │
│     - Schedule optimal time           │
│     - Upload to all platforms         │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  5. Analytics Tracker                │
│     - Log views/engagement           │
│     - Update confidence scores        │
│     - Learn from results              │
└─────────────────────────────────────────┘
```

---

## Part C: File Structure

### C1. Project Layout

```
1ai-social/
├── README.md
├── SKILL.md
├── COMPREHENSIVE_PLAN.md          ← This file
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── config.yaml
├── mcp_server.py                   # MCP control plane
├── CLAUDE.md                      # AI instructions
├── scripts/
│   ├── __init__.py
│   ├── orchestrator.py            # Main pipeline
│   ├── config.py                 # Configuration
│   ├── scheduler.py              # Post scheduling
│   ├── planner.py               # Content calendar
│   ├── analytics.py             # Metrics tracking
│   └── integrations/
│       ├── __init__.py
│       ├── larry_playbook.py   # → larry-playbook
│       ├── content_generator.py # → content-generator
│       ├── humanizer.py        # → humanizer
│       ├── social_upload.py    # → social-media-upload
│       ├── engagement.py       # → social-media-engagement
│       └── berkahkarya.py     # → berkahkarya-saas-bot
├── data/
│   ├── content_queue.json
│   ├── scheduled.json
│   ├── posted.json
│   └── analytics.json
├── logs/
└── tests/
```

### C2. Key Scripts

| Script | Purpose | Integrates With |
|--------|---------|-----------------|
| `orchestrator.py` | Main pipeline | All below |
| `scheduler.py` | Queue + timing | cron, data/ |
| `planner.py` | Content calendar | larry-playbook |
| `analytics.py` | Track metrics | memory files |
| `larry_playbook.py` | Viral hooks | larry-playbook skill |
| `content_generator.py` | Video gen | content-generator |
| `humanizer.py` | Caption polish | humanizer skill |
| `social_upload.py` | Distribution | social-media-upload |
| `engagement.py` | Audience interaction | social-media-engagement |
| `berkahkarya.py` | Bot + payment | berkahkarya-saas-bot |

---

## Part D: Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up project structure
- [ ] Create config.yaml
- [ ] Build MCP server
- [ ] Set up data storage

### Phase 2: Content Generation (Week 2)
- [ ] Integrate larry-playbook client
- [ ] Integrate content-generator client
- [ ] Implement viral hook generation
- [ ] Implement video pipeline

### Phase 3: Distribution (Week 3)
- [ ] Integrate social-upload client
- [ ] Implement scheduling system
- [ ] Multi-platform posting
- [ ] Caption optimization

### Phase 4: Engagement (Week 4)
- [ ] Integrate engagement client
- [ ] Like/comment automation
- [ ] Follow/unfollow logic
- [ ] DM automation

### Phase 5: Analytics & Learning (Week 5)
- [ ] Track views/engagement
- [ ] Update confidence scores
- [ ] Memory/learning system
- [ ] Performance reporting

### Phase 6: berkahkarya Integration (Week 6)
- [ ] Connect to bot
- [ ] Payment integration
- [ ] User management
- [ ] Credit system

---

## Part E: Key Integration Points

### E1. Larry Playbook Integration

```python
# From larry-playbook - Proven Viral Formula
# 234K+ views proven hooks:
# - "My landlord said X, so I showed them what AI thinks..."
# - "My mum was skeptical about AI until..."

# Confidence System:
# - High (2.0x): 100K+ views proven
# - Medium (1.5x): 50K+ views
# - Low (1.0x): New untested
```

### E2. Content Generator Integration

```python
# Pipeline: LLM → NVIDIA Image → BytePlus Video → FFmpeg
# Cost: ~$0.031 per 60s TikTok video
# Output: 9:16, 60s, ~8MB MP4
```

### E3. berkahkarya-saas-bot Integration

```python
# Features to use:
# - Telegram user interface
# - Payment (Midtrans, Tripay)
# - Credit system
# - Video generation (Kling, Runway)
# - Affiliate system
# - Social media direct publish
```

---

## Part F: Environment Variables

```bash
# 1ai-social
1AI_SOCIAL_SECRET_KEY="..."

# Larry Playbook
POST_BRIDGE_API_KEY="pb_live_xxx"

# Content Generator
NVIDIA_API_KEY="nvapi-xxx"
BYTEPLUS_API_KEY="xxx"
GROQ_API_KEY="gsk_xxx"

# berkahkarya-saas-bot
BOT_TOKEN="xxx"
DATABASE_URL="postgresql://..."
REDIS_URL="redis://..."

# Social Platforms
TWITTER_COOKIES="..."
INSTAGRAM_SESSION="..."
TIKTOK_SESSION="..."
```

---

## Part G: Success Metrics

| Metric | Target | Measurement |
|--------|--------|--------------|
| Views per post | 50K+ average | Platform analytics |
| Engagement rate | 8%+ | (likes+comments)/views |
| Save rate | 2%+ | Saves/views |
| Share rate | 1%+ | Shares/views |
| Cost per post | <$0.50 | API costs |
| ROI | 100x+ | Views/cost |

---

## Part H: References

- **larry-playbook**: ~/.opencode/skills/content/larry-playbook/SKILL.md
- **content-generator**: ~/.opencode/skills/content/content-generator/SKILL.md
- **humanizer**: ~/.opencode/skills/content/humanizer/SKILL.md
- **social-media-engagement**: ~/.opencode/skills/marketing/social-media-engagement/SKILL.md
- **social-media-upload**: ~/.opencode/skills/marketing/social-media-upload/SKILL.md
- **berkahkarya-saas-bot**: ~/projects/berkahkarya-saas-bot/
- **viraloop**: https://github.com/mutonby/viraloop

---

## Part I: Next Steps

1. Approve this plan
2. Begin Phase 1 implementation
3. Set up MCP server
4. Test integrations one by one
5. Build full pipeline
6. Deploy and iterate

---

**Plan Created**: 2026-04-16
**Last Updated**: 2026-04-16
