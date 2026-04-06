# Supplyn X Growth Agent

An autonomous X (Twitter) growth system built for **@app_supplyn** — the AI-powered personalised supplement stack builder at [supplyn.app](https://supplyn.app).

Built with Claude AI (Anthropic), APScheduler, Tweepy, and SQLite. Posts threads and tweets on a schedule, monitors trends, surfaces reply and engagement opportunities, and learns from its own performance over time.

**Goal:** Maximum followers + supplyn.app conversions.

---

## What the Agent Does

### Fully Automated (runs 24/7 without you)

| When | What |
|---|---|
| Mon/Wed/Fri — 8:30 AM | Posts a full thread (8–10 tweets) on supplement/health topics |
| Tue/Thu — 8:30 AM | Posts a hot take or question tweet |
| Sat — 9:00 AM | Posts a conversion tweet (drives traffic to supplyn.app) |
| Daily — 12:15 PM | Posts an education or observation tweet |
| Daily — 6:45 PM | Posts a second thread (Mon/Wed/Fri) or single tweet |
| Wed/Sun — 7:30 PM | Posts a conversion tweet (drives supplyn.app signups) |
| Every 2 hours | Scans trending supplement keywords, flags viral opportunities |
| Every 15 minutes | Monitors @app_supplyn mentions, sorts by follower count |
| Every hour | Drafts replies to VIP accounts (Huberman, Attia, Bryan Johnson, etc.) |
| Every 6 hours | Generates follow suggestions in the health/supplement niche |
| Sunday 9 PM | Analyses performance, updates strategy for next week |

**~14 posts per week, fully automated.**

### Suggestion Mode (never auto-posts — you act manually)

| Command | What it shows | Time needed |
|---|---|---|
| `python main.py replies` | Reply drafts for VIP account posts | 5 min/day |
| `python main.py mentions` | People who tagged @app_supplyn, sorted by follower count | 5 min/day |
| `python main.py follow-report` | Health/supplement accounts worth following | 5 min every 2 days |
| `python main.py engagement` | Tweets worth liking or quote-tweeting | 5 min/day |

> **Why suggestion mode?** X's ToS prohibits automated likes, replies, and follows. Automating these gets accounts suspended. The agent does the research; you take the action. It's also better for growth — human-timed replies outperform bot-timed ones.

---

## Content Strategy: 60 / 25 / 15

| Type | Share | Purpose | Examples |
|---|---|---|---|
| **Education** | 60% | Builds followers and trust | Supplement science, ingredient breakdowns, industry exposés, hot takes |
| **Build in Public** | 25% | Humanises the brand | Supplyn journey, product decisions, founder observations |
| **Conversion** | 15% | Drives supplyn.app signups | Direct product tweets, "we built this to solve X" stories |

Every thread ends with a direct CTA to supplyn.app. Education earns the right to sell.

### Tweet Types

| Type | What it does |
|---|---|
| `hot_take` | Controversial but defensible opinion about the supplement industry |
| `question` | Thought-provoking question that reveals a hidden assumption |
| `observation` | Sharp insight about supplements, health tech, or building Supplyn |
| `meme` | Self-aware, slightly ironic take on the wellness/biohacking world |
| `conversion` | Direct founder-voiced tweet driving people to supplyn.app |

### Thread Formula

- **Tweet 1 — Hook:** Bold claim or shocking industry stat. Stops the scroll.
- **Tweet 2 — Setup:** Why this matters right now. Make it personal.
- **Tweets 3–8 — Meat:** One evidence-backed insight per tweet. Short. No fluff.
- **Tweet 9 — Summary:** "If you remember one thing from this thread..."
- **Tweet 10 — CTA:** Always points to supplyn.app with a specific benefit hook.

---

## What You Do Each Week (15 min/day)

**Every morning (5 min):**
```bash
python main.py replies
```
Pick 3–5 reply drafts, post them manually on X. This is the **#1 growth lever** — one good reply on a Huberman thread can bring 200+ followers in a single day.

**Every evening (5 min):**
```bash
python main.py mentions
```
Reply personally to anyone who tagged @app_supplyn with 1,000+ followers.

**Every 2 days (5 min):**
```bash
python main.py follow-report
```
Follow 10–15 suggested accounts. In tight niches, 20–30% follow back.

**Every Sunday (2 min):**
```bash
python main.py report
python main.py update-learnings
```
Review what performed best. The agent updates its strategy automatically.

---

## Setup

### 1. API Keys You Need

#### Anthropic (AI content generation)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Add a payment method (minimum $5 credit)
3. **API Keys** → **Create Key** → copy it

#### X Developer Portal (posting to Twitter)
1. Go to [developer.x.com](https://developer.x.com) → create an account
2. Create a **Project** and an **App**
3. Go to your App → **User authentication settings**
   - Enable **OAuth 1.0a**
   - Set permissions to **Read and Write**
   - Callback URL: `https://localhost`
   - Website URL: `https://supplyn.app`
   - Save
4. Go to **Keys and Tokens**:
   - **Consumer Key** → `X_API_KEY`
   - **Consumer Secret** → `X_API_SECRET`
   - Click **Generate** on Access Token → `X_ACCESS_TOKEN` + `X_ACCESS_TOKEN_SECRET`
   - Click **Generate** on Bearer Token → `X_BEARER_TOKEN`

> **Important:** Generate the Access Token AFTER setting Read+Write permissions. A token issued under Read-only won't be able to post.

> **X API billing:** Use **Pay Per Use** (not Basic at $100/month). At ~180 tweets/month, your X API cost is roughly **$0.04/month**.

### 2. Local Setup (Mac)

```bash
cd x-growth-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
X_BEARER_TOKEN=...
X_USERNAME=app_supplyn
DRY_RUN=false
TIMEZONE=Europe/London
NICHE=personalised supplements, health tech, AI wellness
```

### 3. Initialise and Test

```bash
# Check all keys are working
python main.py init

# Preview a tweet without posting
python main.py --dry-run post-tweet

# Preview a thread without posting
python main.py --dry-run post-thread

# Preview a conversion tweet
python main.py --dry-run post-tweet --type conversion
```

If you see content in the terminal, everything works.

### 4. Go Live

```bash
python main.py run
```

---

## Deploying to Hetzner (Recommended)

Running on a server means the agent works 24/7 without your Mac being on. **Hetzner CX22 costs €3.79/month** and can run 5–8 agents simultaneously.

### Step 1 — Create the Server

1. Go to [hetzner.com](https://hetzner.com) → Cloud → create account
2. **New Project** → **Add Server**
3. Pick:
   - Location: **Nuremberg** (or closest to you)
   - OS: **Ubuntu 24.04**
   - Plan: **CX22** (€3.79/mo, 4GB RAM)
4. Add your SSH key or set a root password
5. Click **Create** — you'll receive an IP address

### Step 2 — Connect

```bash
ssh root@YOUR_SERVER_IP
```

### Step 3 — Install Dependencies

```bash
apt update && apt upgrade -y
apt install python3 python3-pip python3-venv git screen -y
```

### Step 4 — Upload the Agent

Run this on your **Mac** (not the server):

```bash
scp -r /Users/mamount/Downloads/otmanechcherifelkettani-coder.github.io/x-growth-agent root@YOUR_SERVER_IP:/root/supplyn-agent
```

### Step 5 — Set Up Environment on the Server

```bash
cd /root/supplyn-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Fill in all your API keys. Save with `Ctrl+X` → `Y` → Enter.

### Step 6 — Initialise and Test

```bash
python main.py init
python main.py --dry-run post-tweet
```

### Step 7 — Run Permanently

```bash
screen -S supplyn
source venv/bin/activate
python main.py run
```

Press `Ctrl+A` then `D` to detach. The agent keeps running after you close the terminal.

### Step 8 — Auto-restart on Reboot (Recommended)

```bash
nano /etc/systemd/system/supplyn.service
```

Paste:
```ini
[Unit]
Description=Supplyn X Growth Agent
After=network.target

[Service]
WorkingDirectory=/root/supplyn-agent
ExecStart=/root/supplyn-agent/venv/bin/python main.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
systemctl enable supplyn
systemctl start supplyn
systemctl status supplyn
```

The agent now survives server reboots automatically.

### Useful Server Commands

```bash
# Check the agent is running
screen -ls

# Watch live output
screen -r supplyn

# Detach without stopping
Ctrl+A then D

# Run daily commands remotely from your Mac
ssh root@YOUR_SERVER_IP "cd /root/supplyn-agent && source venv/bin/activate && python main.py replies"

# Check agent logs (if using systemd)
journalctl -u supplyn -f
```

### Updating the Agent After Code Changes

```bash
# On your Mac — re-upload the changed files
scp -r /Users/mamount/Downloads/otmanechcherifelkettani-coder.github.io/x-growth-agent root@YOUR_SERVER_IP:/root/supplyn-agent

# On the server — restart
systemctl restart supplyn
```

---

## CLI Command Reference

```
python main.py [OPTIONS] COMMAND

Options:
  --dry-run / --no-dry-run    No X API writes (preview only)
  --timezone TEXT             Scheduler timezone (default: from .env)

Commands:
  run              Start the full scheduler (runs indefinitely)
  dry-run          Start scheduler in dry-run mode
  init             Initialise DB and verify all API connections
  report           Generate weekly analytics report
  trends           Scan and show trending supplement opportunities
  replies          Show reply drafts for VIP accounts (post manually)
  engagement       Show tweets worth liking or quote-tweeting
  follow-report    Show follow suggestions + unfollow candidates
  mentions         Show unreviewed @app_supplyn mentions by follower count
  post-thread      Generate and post a thread immediately
  post-tweet       Generate and post a single tweet immediately
  update-learnings Run analytics and update data/learnings.json
```

**Examples:**
```bash
# Post a thread on a specific topic
python main.py post-thread --topic "Why magnesium oxide is a waste of money"

# Generate a hot take (preview only)
python main.py --dry-run post-tweet --type hot_take

# Generate a conversion tweet (preview only)
python main.py --dry-run post-tweet --type conversion

# Check reply suggestions
python main.py replies

# See follow suggestions
python main.py follow-report

# Get this week's analytics
python main.py report
```

---

## Real Monthly Costs

| Service | Usage | Cost |
|---|---|---|
| **Anthropic API** | ~180 content generations/month | ~$0.30 |
| **X API (Pay Per Use)** | ~180 tweet writes/month | ~$0.04 |
| **Hetzner CX22** | 24/7 server | €3.79 |
| **Total** | | **~$4.50/month** |

> Use X API **Pay Per Use** — not the Basic plan ($100/month). At this posting volume, Pay Per Use costs $0.04/month vs $100/month. Basic only makes sense if you're running 50+ accounts.

---

## Follower Growth: What to Expect

| Week | Followers | What's driving it |
|---|---|---|
| 1–2 | +20–50 | First threads, initial niche visibility |
| 3–4 | +50–150 | Reply-guy strategy on Huberman/Attia threads starts paying off |
| 6–8 | +200–400 | One thread goes viral in the supplement niche |
| 10–12 | +500–800 | Consistent voice, algorithm starts recommending the account |
| 16+ | +1,000–2,000 | Compound growth from established niche authority |

**The #1 lever:** Reply manually to big accounts every day. One good reply on a Huberman thread (15M followers) can bring 200–500 followers overnight. The agent writes the replies — you post them.

---

## Scaling to Multiple Agents

One Hetzner CX22 can run 5–8 agents simultaneously. Each agent needs its own folder, `.env` file, and process.

```
/root/
  supplyn-agent/      ← @app_supplyn (current)
  client2-agent/      ← future account
  client3-agent/      ← future account
```

Each gets its own systemd service or screen session. Upgrade to CX32 (€6.49/mo) when running 8+ agents.

---

## Troubleshooting

**"Your credit balance is too low" (Anthropic)**
Add credits at [console.anthropic.com](https://console.anthropic.com) → Billing. $5 covers months of usage.

**"402 Payment Required" (X API)**
Add a payment method at [developer.x.com](https://developer.x.com) → Billing. Pay Per Use costs ~$0.04/month at this posting volume.

**"no such table" error**
Run `python main.py init` to create the database before running the agent.

**Tweets don't sound like the Supplyn voice**
Edit `persona.md`. Add more example tweets in the exact voice you want. The LLM learns from examples — the more specific, the better.

**Access Token shows "Read only"**
Go to developer.x.com → your App → User authentication settings → change to Read+Write → save → regenerate the Access Token. The old token won't work for posting.

**Scheduler running but nothing posts**
Check your `TIMEZONE` setting in `.env`. Jobs fire at scheduled UTC times by default. Set `TIMEZONE=Europe/London` if you're in the UK.

**Agent stopped after server reboot**
Set up the systemd service (Step 8 in the Hetzner section). This makes the agent restart automatically after any reboot.

**Thread CTA doesn't mention supplyn.app**
The thread prompt instructs Claude to always end with a supplyn.app CTA. If it's not happening, the LLM may have ignored the instruction — run `python main.py --dry-run post-thread` to preview and check.

---

## Project Structure

```
x-growth-agent/
├── main.py                  # CLI entry point (12 commands)
├── orchestrator.py          # APScheduler — registers all jobs
├── persona.md               # Voice, tone, examples — injected into every LLM call
├── agents/
│   ├── content_creator.py   # Thread + single tweet generation
│   ├── trend_hunter.py      # Scans X for trending supplement keywords
│   ├── reply_guy.py         # Drafts replies for VIP accounts
│   ├── engagement.py        # Surfaces tweets worth liking/QTing
│   ├── growth.py            # Follow/unfollow suggestions
│   ├── monitor.py           # Mention monitoring
│   └── analytics.py         # Performance tracking + learnings
├── tools/
│   ├── llm.py               # Anthropic API wrapper (Haiku + Sonnet)
│   ├── x_api.py             # Tweepy v2 wrapper
│   ├── memory.py            # SQLite wrapper (7 tables)
│   ├── cache.py             # Semantic LLM cache (sentence-transformers)
│   └── scorer.py            # Content quality scorer (hook/shareability/niche)
├── data/
│   ├── agent.db             # SQLite database
│   ├── learnings.json       # Weekly performance learnings (auto-updated)
│   └── vip_accounts.txt     # Accounts to monitor for reply-guy strategy
├── .env                     # Your API keys (never commit this)
├── .env.example             # Template
└── SETUP.md                 # Detailed first-time setup guide
```

---

## How the AI Works

```
persona.md (voice/rules)
       ↓
APScheduler fires a job
       ↓
Agent picks topic (avoids last 14 days of topics)
       ↓
Claude Sonnet generates 3 content variants
       ↓
Claude Haiku scores each variant (hook 40% + shareability 30% + niche relevance 30%)
       ↓
Best variant is posted via X API
       ↓
Performance tracked in SQLite
       ↓
Sunday: AnalyticsAgent reads metrics → updates learnings.json
       ↓
Next week: ContentCreatorAgent reads learnings.json before generating
```

The agent gets better every week as it learns what content formats perform best for @app_supplyn's specific audience.
