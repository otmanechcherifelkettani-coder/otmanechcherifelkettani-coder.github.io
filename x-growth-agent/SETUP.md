# Supplyn X Growth Agent — Setup Guide

---

## Before You Start: Configuration Checklist

You need two things before running anything:
1. **X (Twitter) API keys** — from the X Developer Portal
2. **Anthropic API key** — from the Anthropic Console

---

## Part 1 — Get Your X API Keys

1. Go to **https://developer.twitter.com** and sign in with **@app_supplyn**
2. Click **"Sign up for Free Account"**
3. When asked to describe your use case, write: *"Scheduling and analysing my own tweets to grow my health tech startup account"*
4. Once approved, go to **Dashboard → Projects & Apps → Create App**
5. Name your app anything (e.g. "supplyn-agent")
6. Go to the **"Keys and Tokens"** tab inside your app
7. Copy and save these 5 values somewhere safe:
   - **API Key**
   - **API Key Secret**
   - **Access Token** *(click "Generate" if not shown)*
   - **Access Token Secret**
   - **Bearer Token**
8. Go to **"Settings" → "User authentication settings"**
9. Enable **OAuth 1.0a** and set permissions to **"Read and Write"**
10. Save the settings

> **Important:** The Free tier allows posting, reading mentions, and searching tweets.
> That is all this agent needs.

---

## Part 2 — Get Your Anthropic API Key

1. Go to **https://console.anthropic.com**
2. Sign in or create an account
3. Go to **API Keys → Create Key**
4. Name it "supplyn-agent"
5. Copy the key immediately — **you only see it once**

> **Cost estimate:** Using claude-sonnet-4-5 for content and claude-haiku-4-5 for
> utility tasks, expect **$3–8/month** for a full posting schedule.

---

## Part 3 — Install Python and Dependencies

Open your terminal (Mac: press `Cmd+Space`, type "Terminal"):

```bash
# 1. Check you have Python 3.11 or newer
python3 --version
# If below 3.11, download from https://python.org

# 2. Navigate to the project folder
cd /otmanechcherifelkettani-coder.github.io/x-growth-agent

# 3. Create a virtual environment (keeps dependencies isolated)
python3 -m venv venv

# 4. Activate the virtual environment
source venv/bin/activate
# You should see (venv) appear at the start of your terminal prompt

# 5. Install all dependencies
pip install -r requirements.txt
# This takes 2–5 minutes the first time
```

---

## Part 4 — Add Your API Keys

```bash
# Still inside the x-growth-agent folder:
cp .env.example .env
```

Now open the `.env` file in any text editor and replace every `your_*_here` value:

```
X_API_KEY=paste_your_api_key_here
X_API_SECRET=paste_your_api_secret_here
X_ACCESS_TOKEN=paste_your_access_token_here
X_ACCESS_TOKEN_SECRET=paste_your_access_token_secret_here
X_BEARER_TOKEN=paste_your_bearer_token_here

ANTHROPIC_API_KEY=paste_your_anthropic_key_here

DRY_RUN=false
TIMEZONE=Europe/London
NICHE=personalised supplements, health tech, AI wellness
X_USERNAME=app_supplyn
```

Save the file. **Never share or commit this file** — it contains your private keys.

---

## Part 5 — Customise Your Persona (Optional but Recommended)

Open `persona.md` and review it. It's already set up for @app_supplyn and Supplyn.app.

Things you may want to tweak:
- **Example tweets** (lines starting with `` ``` ``) — replace any that don't sound like you
- **Topics to own** — add or remove based on what you actually want to talk about
- **Signature phrases** — add your own recurring openers and closers
- **VIP accounts** — open `data/vip_accounts.txt` and add/remove accounts you want to reply-guy

The persona file is injected into every single LLM call. Getting it right makes a
noticeable difference in output quality.

---

## Part 6 — Test First (No API Writes)

```bash
# Make sure venv is still active (you see (venv) in your prompt)
# If not: source venv/bin/activate

python main.py dry-run
```

This runs a full simulated 7-day cycle without posting anything. It generates a file
called `dry_run_report.md` in the project folder. **Open it and read through it.**

Check:
- Does the content sound like you?
- Are the threads on the right topics for Supplyn?
- Do the reply suggestions feel natural?

If anything feels off, edit `persona.md` and run dry-run again until you're happy.

---

## Part 7 — Initialise the Database

```bash
python main.py init
```

This creates the SQLite database (`data/agent.db`) and verifies that all API
connections are working. You should see green confirmation messages for:
- X API connection
- Anthropic API connection
- Database created

---

## Part 8 — Go Live

```bash
python main.py run
```

Leave this terminal window open. The agent will now:

| Time (London) | Automatic action |
|---|---|
| 8:30 AM Mon/Wed/Fri | Post a thread |
| 8:30 AM Tue/Thu/Sat | Post a single tweet |
| 12:15 PM daily | Post a single tweet |
| 6:45 PM daily | Post a single tweet or thread |
| Every 2 hours | Scan supplement trends |
| Every 15 minutes | Check your mentions |
| Every hour | Build reply suggestion queue |
| Every hour | Build engagement suggestion queue |
| Every 6 hours | Build follow suggestion list |
| Sunday 9 PM | Generate weekly report + update learnings |
| 1 AM – 7 AM | No activity (blackout window) |

---

## Daily Routine (5–10 minutes each morning)

Open a new terminal tab and activate the environment:

```bash
cd /Users/mamount/Downloads/otmanechcherifelkettani-coder.github.io/x-growth-agent
source venv/bin/activate
```

Then run these three commands:

### 1. Reply queue — your most important growth action
```bash
python main.py replies
```
Shows a table of drafted replies to Huberman, Attia, and other VIP accounts.
Copy the ones you like and **post them manually on X**. Aim for 5–10 per day.
This is the single highest-leverage thing you can do for follower growth.

### 2. Check mentions
```bash
python main.py mentions
```
Shows everyone who tagged @app_supplyn, sorted by their follower count.
**Reply manually** to anyone with over 1,000 followers.

### 3. Follow suggestions
```bash
python main.py follow-report
```
Shows 25–30 health/biohacking/supplement accounts worth following.
**Go follow 10–15 of them on X.** Many follow back within 48 hours.

### 4. Engagement queue (optional)
```bash
python main.py engagement
```
Shows tweets worth liking or quote-tweeting.
Do 5–10 likes and 1–2 quote-tweets if any look good.

---

## Weekly Routine (10 minutes, Sunday evening)

```bash
python main.py report
```

Generates a markdown report with:
- Top 3 performing tweets of the week
- Average engagement rate
- Best content types and posting hours
- Recommendations for next week

The agent also auto-updates `data/learnings.json` — this is the feedback loop that
makes content quality improve over time.

---

## Keeping It Running 24/7

If you want the agent running while your laptop is closed, move it to a cheap VPS
(DigitalOcean Droplet, Hetzner CX11 — about £4–5/month).

Once you SSH into your server:

```bash
# Install dependencies same as above, then:

# Run agent in background (survives closing the terminal)
nohup python main.py run > agent.log 2>&1 &

# Check it's working
tail -f agent.log

# Stop it if needed
pkill -f "python main.py run"
```

Alternatively, on your Mac you can keep it running with:
```bash
python main.py run
```
Just don't close that terminal tab.

---

## Manual Commands Reference

```bash
python main.py run              # Start the full scheduler
python main.py dry-run          # Simulate 7 days, no API writes
python main.py init             # Setup DB + test API connections
python main.py report           # Generate weekly analytics report
python main.py trends           # Show current trend opportunities
python main.py replies          # Show pending reply suggestions
python main.py engagement       # Show engagement suggestion queue
python main.py follow-report    # Show follow suggestions
python main.py mentions         # Show unreviewed mentions
python main.py post-thread      # Manually trigger a thread now
python main.py post-tweet       # Manually trigger a single tweet now
python main.py update-learnings # Re-run analytics + update learnings.json
```

---

## What the Agent Does vs What You Do

| Task | Agent | You |
|---|---|---|
| Write & post threads 3x/week | Fully automated | Review dry-run first |
| Write & post single tweets | Fully automated | — |
| Scan supplement/health trends | Fully automated | — |
| Draft replies to Huberman/Attia/etc | Agent drafts them | Post best ones manually (5 min/day) |
| Monitor your mentions | Agent flags them | Reply to high-value ones |
| Identify accounts to follow | Agent finds them | Click follow (2 min/day) |
| Likes & quote-tweets | Agent surfaces them | Act on the good ones |
| Weekly analytics report | Fully automated | Read it on Sundays |
| Content self-improvement loop | Fully automated | — |

---

## Troubleshooting

**"API key not found" error**
→ Check your `.env` file has no spaces around the `=` sign and no quotes around values.

**"Rate limit" error on X API**
→ Normal. The agent backs off and retries automatically. Free tier has limits.

**Content doesn't sound like me**
→ Edit `persona.md` — specifically the example tweets section. Run dry-run again.

**Agent posted something I don't like**
→ Delete it manually on X. Then add that topic to the "Topics to Avoid" section in
  `persona.md` so it doesn't happen again.

**Can't see (venv) in terminal**
→ Run: `source venv/bin/activate` from inside the x-growth-agent folder.

**Scheduler stopped / terminal closed**
→ Just run `python main.py run` again. The SQLite database persists all state,
  so nothing is lost between restarts.
