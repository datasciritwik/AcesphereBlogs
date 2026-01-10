# AcesphereAI Blog Agent 🤖

An autonomous AI-powered blog publishing system that generates 2-3 SEO-optimized articles per day about AI hiring and HR tech.

## Features

- **Automated Topic Planning** - LLM-powered topic generation from business context and SEO keywords
- **Web Research** - Optional research module for gathering facts and statistics
- **SEO-Optimized Writing** - Articles with proper structure, internal/external links, and meta tags
- **Git-Based Publishing** - Automatic commit and push to trigger Netlify deployments
- **Scheduled Execution** - GitHub Actions CRON runs 3 times daily

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file:

```bash
GROQ_API_KEY=gsk_your-api-key-here
NOTIFICATION_WEBHOOK=https://discord.com/api/webhooks/...  # Optional
```

### 3. Run the Agent

```bash
# Full pipeline - generates and publishes an article
python main.py

# Dry run - test without publishing
python main.py --dry-run

# Topic only - generate topic brief without writing
python main.py --topic-only
```

### 4. Build the Static Site

```bash
python build_site.py
```

## Project Structure

```
AcesphereBlogs/
├── agent/                    # Core agent modules
│   ├── config.py            # Configuration loader
│   ├── topic_planner.py     # Topic generation
│   ├── researcher.py        # Web research
│   ├── writer.py            # Article generation
│   └── publisher.py         # Git publishing
├── data/                     # Configuration data
│   ├── business_context.yaml # Company info
│   ├── keywords.yaml         # SEO keywords
│   └── published_posts.json  # Post index
├── content/posts/            # Generated articles (Markdown)
├── site/                     # Built static site (HTML)
├── .github/workflows/        # GitHub Actions
├── main.py                   # Entry point
├── build_site.py             # Static site builder
├── netlify.toml              # Netlify config
└── requirements.txt          # Python dependencies
```

## Configuration

### Business Context (`data/business_context.yaml`)

Defines your company's identity, target audience, brand voice, and content pillars.

### Keywords (`data/keywords.yaml`)

SEO keyword clusters that drive topic generation. Includes primary keywords, related terms, and long-tail topics.

## GitHub Actions Setup

Required secrets in your GitHub repository:

- `GROQ_API_KEY` - Your Groq API key
- `NOTIFICATION_WEBHOOK` (optional) - Discord/Slack webhook for notifications
- `NETLIFY_BUILD_HOOK` (optional) - Netlify build hook URL

The workflow runs at:

- 6:00 AM UTC
- 2:00 PM UTC
- 10:00 PM UTC

## Netlify Deployment

1. Connect this repository to Netlify
2. Build command: `python build_site.py`
3. Publish directory: `site`

Netlify will auto-deploy when new posts are pushed.

## How It Works

```
┌─────────────────┐
│   Scheduler     │  (GitHub Actions CRON)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Topic Planner  │  → Generates unique topic brief
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Researcher    │  → Gathers facts from web (optional)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Writer      │  → Creates SEO-optimized article
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Publisher     │  → Saves to Git, pushes to origin
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Netlify      │  → Auto-builds and deploys site
└─────────────────┘
```

## License

MIT
