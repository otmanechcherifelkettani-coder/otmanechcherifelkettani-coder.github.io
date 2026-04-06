from __future__ import annotations

"""
Simulates a full 7-day cycle of the X Growth Agent.
No API writes (dry_run=True throughout).
Uses mock data where X API would return results.
Generates dry_run_report.md with detailed output.
"""

import json
import os
import sys
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

console = Console()

REPORT_PATH = Path(__file__).parent / "dry_run_report.md"


# ─────────────────────────────────────────────────────────────────────────────
# Mock Data Generators
# ─────────────────────────────────────────────────────────────────────────────

MOCK_VIP_TWEETS = [
    {
        "id": "mock_tweet_001",
        "text": "Your supplement stack should be built around your bloodwork, not an influencer's affiliate code. Stop guessing.",
        "username": "hubermanlab",
        "follower_count": 4200000,
        "like_count": 8921,
        "retweet_count": 1023,
        "reply_count": 412,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    },
    {
        "id": "mock_tweet_002",
        "text": "Spent £200 on supplements last month. Had bloodwork done. Turns out I only actually needed 2 of the 7 things I was taking. The system is broken.",
        "username": "peterattiamd",
        "follower_count": 920000,
        "like_count": 3412,
        "retweet_count": 287,
        "reply_count": 198,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)).isoformat(),
    },
    {
        "id": "mock_tweet_003",
        "text": "Unpopular opinion: most people would get better results from fixing sleep and diet than adding more supplements to their stack.",
        "username": "garybrecka",
        "follower_count": 680000,
        "like_count": 2891,
        "retweet_count": 341,
        "reply_count": 267,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(),
    },
    {
        "id": "mock_tweet_004",
        "text": "The magnesium form you're taking matters more than the brand. Oxide = mostly useless. Glycinate = sleep. Malate = energy. Most people are wasting money.",
        "username": "foundmyfitness",
        "follower_count": 310000,
        "like_count": 1876,
        "retweet_count": 456,
        "reply_count": 134,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    },
    {
        "id": "mock_tweet_005",
        "text": "Building a health tech startup in 2025: the personalisation gap is massive. Nobody has solved supplement stacks at a consumer level. Huge opportunity.",
        "username": "samcorcos",
        "follower_count": 45000,
        "like_count": 892,
        "retweet_count": 67,
        "reply_count": 43,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
    },
]

MOCK_TRENDING_TWEETS = [
    {
        "id": "trend_001",
        "text": "Andrew Huberman's supplement protocol is getting called out for having almost no RCT evidence. The biohacking world is having a moment of reckoning.",
        "username": "healthjournalist",
        "follower_count": 78000,
        "like_count": 5241,
        "retweet_count": 1203,
        "reply_count": 891,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    },
    {
        "id": "trend_002",
        "text": "73% of UK adults are vitamin D deficient in winter. It's £8/month to fix. But the NHS still doesn't recommend it proactively. Wild.",
        "username": "ukdoctor_tweets",
        "follower_count": 34000,
        "like_count": 2134,
        "retweet_count": 567,
        "reply_count": 234,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    },
    {
        "id": "trend_003",
        "text": "AG1 just raised another $50m. Their CAC is insane. They're a marketing company that sells supplements, not a supplement company. The margins tell you everything.",
        "username": "healthtechvc",
        "follower_count": 52000,
        "like_count": 3421,
        "retweet_count": 789,
        "reply_count": 312,
        "created_at": (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat(),
    },
]

MOCK_MENTIONS = [
    {
        "id": "mention_001",
        "text": "@app_supplyn this thread on supplement personalisation is exactly what I've been looking for. Just tried supplyn.app — really impressive.",
        "username": "healthbiohacker_uk",
        "follower_count": 8400,
        "like_count": 34,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
    },
    {
        "id": "mention_002",
        "text": "@app_supplyn disagree on the AG1 point — their convenience factor is real, even if the price is high",
        "username": "wellnessfounder",
        "follower_count": 12000,
        "like_count": 12,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    },
    {
        "id": "mention_003",
        "text": "@app_supplyn great point about magnesium forms. I switched to glycinate last month and sleep improved noticeably.",
        "username": "healthcurious",
        "follower_count": 560,
        "like_count": 5,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
    },
]

MOCK_FOLLOW_CANDIDATES = [
    {"username": "supplement_science", "follower_count": 18400, "like_count": 892},
    {"username": "biohacking_uk", "follower_count": 9200, "like_count": 445},
    {"username": "health_tech_founder", "follower_count": 6700, "like_count": 234},
    {"username": "longevity_daily", "follower_count": 34000, "like_count": 1876},
    {"username": "evidencebased_health", "follower_count": 22000, "like_count": 1034},
    {"username": "nutritionfacts_uk", "follower_count": 11000, "like_count": 567},
    {"username": "gut_health_founder", "follower_count": 7800, "like_count": 312},
    {"username": "personalised_nutrition", "follower_count": 15300, "like_count": 789},
]


def _mock_x_api() -> MagicMock:
    """Create a mock XAPIClient that returns realistic data."""
    mock = MagicMock()
    mock.dry_run = True

    def mock_post_tweet(text: str, reply_to_id: str | None = None) -> dict[str, Any]:
        tid = f"dry_{random.randint(100000, 999999)}"
        return {"id": tid, "text": text}

    def mock_post_thread(tweets: list[str]) -> list[dict[str, Any]]:
        return [{"id": f"dry_{random.randint(100000, 999999)}", "text": t} for t in tweets]

    def mock_search_recent(query: str, max_results: int = 10) -> list[dict[str, Any]]:
        return MOCK_TRENDING_TWEETS[:max_results]

    def mock_get_mentions(since_id: str | None = None) -> list[dict[str, Any]]:
        return MOCK_MENTIONS

    def mock_get_tweet_metrics(tweet_id: str) -> dict[str, Any]:
        return {
            "impressions": random.randint(500, 15000),
            "likes": random.randint(5, 500),
            "retweets": random.randint(0, 80),
            "replies": random.randint(0, 40),
            "bookmarks": random.randint(0, 60),
        }

    def mock_get_user_timeline(username: str, max_results: int = 5) -> list[dict[str, Any]]:
        matching = [t for t in MOCK_VIP_TWEETS if t["username"] == username]
        return matching if matching else [random.choice(MOCK_VIP_TWEETS)]

    def mock_get_user_info(username: str) -> dict[str, Any]:
        return {
            "id": f"user_{hash(username) % 1000000}",
            "username": username,
            "name": username.replace("_", " ").title(),
            "follower_count": random.choice([5000, 25000, 100000, 500000]),
            "following_count": random.randint(200, 2000),
            "tweet_count": random.randint(1000, 50000),
        }

    mock.post_tweet.side_effect = mock_post_tweet
    mock.post_thread.side_effect = mock_post_thread
    mock.search_recent_tweets.side_effect = mock_search_recent
    mock.get_mentions.side_effect = mock_get_mentions
    mock.get_tweet_metrics.side_effect = mock_get_tweet_metrics
    mock.get_user_timeline.side_effect = mock_get_user_timeline
    mock.get_user_info.side_effect = mock_get_user_info

    return mock


# ─────────────────────────────────────────────────────────────────────────────
# Day Simulation
# ─────────────────────────────────────────────────────────────────────────────

class DayLog:
    """Accumulates log entries for a single simulated day."""

    def __init__(self, day_num: int, date: datetime) -> None:
        self.day_num = day_num
        self.date = date
        self.threads: list[list[str]] = []
        self.single_tweets: list[dict[str, Any]] = []
        self.reply_suggestions: list[dict[str, Any]] = []
        self.engagement_suggestions: list[dict[str, Any]] = []
        self.follow_suggestions: list[dict[str, Any]] = []
        self.trends: list[dict[str, Any]] = []
        self.mentions: list[dict[str, Any]] = []
        self.actions: list[str] = []

    def log(self, msg: str) -> None:
        self.actions.append(msg)
        console.print(f"  [dim]{msg}[/dim]")


def run_day(
    day_num: int,
    date: datetime,
    content_agent: Any,
    trend_agent: Any,
    reply_agent: Any,
    engagement_agent: Any,
    growth_agent: Any,
    monitor_agent: Any,
) -> DayLog:
    """Simulate a full day of agent activity."""
    log = DayLog(day_num, date)
    weekday = date.weekday()  # 0=Mon

    console.print(f"\n[bold blue]Day {day_num}: {date.strftime('%A, %B %d')}[/bold blue]")

    # Morning post (8:30 AM)
    if weekday in (0, 2, 4):  # Mon/Wed/Fri → thread
        log.log("8:30 AM: Generating thread...")
        tweets = content_agent.generate_thread()
        if tweets:
            log.threads.append(tweets)
            log.log(f"8:30 AM: Thread generated ({len(tweets)} tweets)")
            for i, t in enumerate(tweets):
                log.log(f"  [Thread T{i+1}] {t[:80]}...")
    else:  # Tue/Thu/Sat → single tweet
        log.log("8:30 AM: Generating single tweet...")
        tweet_text = content_agent.generate_single_tweet(tweet_type="hot_take")
        if tweet_text:
            log.single_tweets.append({"time": "08:30", "type": "hot_take", "text": tweet_text})
            log.log(f"8:30 AM: Tweet generated: {tweet_text[:80]}...")

    # Trend scan
    log.log("Scanning trends...")
    trend_results = trend_agent.scan_trends()
    log.trends.extend(trend_results)
    log.log(f"Trends found: {len(trend_results)}")

    # Noon tweet
    log.log("12:15 PM: Generating noon tweet...")
    noon_tweet = content_agent.generate_single_tweet(tweet_type="question")
    if noon_tweet:
        log.single_tweets.append({"time": "12:15", "type": "question", "text": noon_tweet})
        log.log(f"12:15 PM: {noon_tweet[:80]}...")

    from tools import memory as _mem

    # Reply queue
    log.log("Scanning VIP accounts for reply opportunities...")
    reply_count = reply_agent.generate_reply_queue()
    log.log(f"Reply suggestions generated: {reply_count}")
    pending_replies = _mem.get_pending_replies(limit=5)
    log.reply_suggestions.extend(pending_replies)

    # Engagement
    log.log("Generating engagement suggestions...")
    engagement_agent.generate_engagement_queue()
    engagement_sug = _mem.get_engagement_suggestions(status="pending", limit=5)
    log.engagement_suggestions.extend(engagement_sug)
    log.log(f"Engagement suggestions queued: {len(log.engagement_suggestions)}")

    # Follow suggestions
    log.log("Finding follow candidates...")
    growth_agent.generate_follow_suggestions()
    follow_sug = _mem.get_follow_suggestions(status="pending", limit=5)
    log.follow_suggestions.extend(follow_sug)
    log.log(f"Follow suggestions: {len(log.follow_suggestions)}")

    # Check mentions
    log.log("Checking mentions...")
    high_value = monitor_agent.check_mentions()
    log.mentions.extend(high_value)
    log.log(f"High-value mentions: {len(high_value)}")

    # Evening post (6:45 PM)
    log.log("6:45 PM: Evening post...")
    evening_tweet = content_agent.generate_single_tweet(tweet_type="observation")
    if evening_tweet:
        log.single_tweets.append({"time": "18:45", "type": "observation", "text": evening_tweet})
        log.log(f"6:45 PM: {evening_tweet[:80]}...")

    return log


# ─────────────────────────────────────────────────────────────────────────────
# Report Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_report(day_logs: list[DayLog], learnings_after: dict[str, Any]) -> str:
    """Build the full dry_run_report.md content."""
    lines: list[str] = []

    lines += [
        "# X Growth Agent — 7-Day Dry Run Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "> All content was generated by the LLM agents. No API writes were made.",
        "> This report shows exactly what the agent would have done over 7 days.",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    total_threads = sum(len(d.threads) for d in day_logs)
    total_singles = sum(len(d.single_tweets) for d in day_logs)
    total_replies = sum(len(d.reply_suggestions) for d in day_logs)
    total_engagement = sum(len(d.engagement_suggestions) for d in day_logs)
    total_follows = sum(len(d.follow_suggestions) for d in day_logs)
    total_trends = sum(len(d.trends) for d in day_logs)

    lines += [
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Threads generated | {total_threads} |",
        f"| Single tweets generated | {total_singles} |",
        f"| Reply suggestions drafted | {total_replies} |",
        f"| Engagement suggestions | {total_engagement} |",
        f"| Follow suggestions | {total_follows} |",
        f"| Trend opportunities detected | {total_trends} |",
        "",
        "---",
        "",
    ]

    # Day-by-day log
    lines += ["## Day-by-Day Action Log", ""]

    for day in day_logs:
        lines.append(f"### Day {day.day_num} — {day.date.strftime('%A, %B %d, %Y')}")
        lines.append("")
        for action in day.actions:
            lines.append(f"- {action}")
        lines.append("")

    lines += ["---", "", "## Generated Threads (Full Text)", ""]

    thread_num = 1
    for day in day_logs:
        for thread in day.threads:
            lines.append(f"### Thread {thread_num} (Day {day.day_num} — {day.date.strftime('%A')})")
            lines.append("")
            for i, tweet in enumerate(thread, 1):
                lines.append(f"**Tweet {i}/{len(thread)}:**")
                lines.append(f"> {tweet}")
                lines.append("")
            thread_num += 1

    lines += ["---", "", "## Generated Single Tweets", ""]

    for day in day_logs:
        if day.single_tweets:
            lines.append(f"### Day {day.day_num} — {day.date.strftime('%A')}")
            lines.append("")
            for t in day.single_tweets:
                lines.append(f"**{t['time']} UTC ({t['type']}):**")
                lines.append(f"> {t['text']}")
                lines.append("")

    lines += ["---", "", "## Reply Suggestions (Drafted, Not Posted)", ""]

    all_replies: list[dict[str, Any]] = []
    for day in day_logs:
        all_replies.extend(day.reply_suggestions)

    if all_replies:
        lines.append("| Account | Strategy | Their Tweet (snippet) | Suggested Reply |")
        lines.append("|---------|----------|----------------------|-----------------|")
        seen_ids: set[int] = set()
        for r in all_replies:
            rid = r.get("id", 0)
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            account = r.get("vip_account", "")
            strategy = r.get("strategy", "")
            vip_snippet = (r.get("vip_tweet_content") or "")[:60]
            reply = (r.get("suggested_reply") or "")[:80]
            lines.append(f"| @{account} | {strategy} | {vip_snippet}... | {reply}... |")
        lines.append("")
    else:
        lines.append("_No reply suggestions generated (VIP account data requires live API)._")
        lines.append("")

    lines += ["---", "", "## Engagement Suggestions", ""]

    all_engagement: list[dict[str, Any]] = []
    for day in day_logs:
        all_engagement.extend(day.engagement_suggestions)

    if all_engagement:
        lines.append("| Type | Account | Content Snippet |")
        lines.append("|------|---------|-----------------|")
        seen_ids_e: set[int] = set()
        for e in all_engagement:
            eid = e.get("id", 0)
            if eid in seen_ids_e:
                continue
            seen_ids_e.add(eid)
            s_type = e.get("suggestion_type", "like")
            account = e.get("account", "")
            content = (e.get("content") or "")[:80]
            lines.append(f"| {s_type} | @{account} | {content}... |")
        lines.append("")
    else:
        lines.append("_No engagement suggestions (requires live API data)._")
        lines.append("")

    lines += ["---", "", "## Follow Suggestions", ""]

    all_follows: list[dict[str, Any]] = []
    for day in day_logs:
        all_follows.extend(day.follow_suggestions)

    if all_follows:
        lines.append("| Username | Followers | Reason |")
        lines.append("|----------|-----------|--------|")
        seen_users: set[str] = set()
        for f in all_follows:
            uname = f.get("username", "")
            if uname in seen_users:
                continue
            seen_users.add(uname)
            followers = f.get("follower_count", 0)
            reason = (f.get("reason") or "")[:80]
            lines.append(f"| @{uname} | {followers:,} | {reason} |")
        lines.append("")
    else:
        lines.append("_No follow suggestions generated (requires live API data)._")
        lines.append("")

    lines += ["---", "", "## Simulated Analytics After 7 Days", ""]

    from tools import memory as mem
    from tools.x_api import XAPIClient
    from agents.analytics import AnalyticsAgent

    try:
        mock_x = _mock_x_api()
        analytics = AnalyticsAgent(x_api=mock_x)
        stats = analytics.get_engagement_stats()
        lines += [
            f"- **Tweets in DB:** {stats['total_tweets']}",
            f"- **Avg engagement rate:** {stats['avg_engagement_rate']:.2%}",
            f"- **Total impressions (simulated):** {stats['total_impressions']:,}",
            f"- **Total likes:** {stats['total_likes']:,}",
            f"- **Total retweets:** {stats['total_retweets']:,}",
            "",
        ]
    except Exception as e:
        lines.append(f"_Analytics simulation error: {e}_")
        lines.append("")

    lines += ["---", "", "## What learnings.json Would Look Like After Week 1", ""]
    lines.append("```json")
    lines.append(json.dumps(learnings_after, indent=2))
    lines.append("```")
    lines.append("")

    lines += [
        "---",
        "",
        "## Notes",
        "",
        "- All tweet content above was generated by the LLM (Claude Sonnet/Haiku) in real-time.",
        "- Reply, engagement, and follow suggestions require live X API data to be populated.",
        "- In production, the scheduler runs continuously with randomized jitter to avoid patterns.",
        "- The agent never auto-posts replies, likes, or follows — those are always manual.",
        "",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    console.print(
        Panel(
            "X Growth Agent — 7-Day Dry Run Simulation\n"
            "No API writes. Generating realistic content via LLM.",
            title="Dry Run",
            style="bold cyan",
        )
    )

    # Initialize DB
    from tools.memory import init_db
    init_db()

    # Create mock X API
    mock_x = _mock_x_api()

    # Initialize agents with mock X API + dry_run=True
    from agents.content_creator import ContentCreatorAgent
    from agents.trend_hunter import TrendHunterAgent
    from agents.reply_guy import ReplyGuyAgent
    from agents.engagement import EngagementAgent
    from agents.growth import GrowthAgent
    from agents.monitor import MonitorAgent
    from agents.analytics import AnalyticsAgent

    content_agent = ContentCreatorAgent(dry_run=True)
    trend_agent = TrendHunterAgent(x_api=mock_x)
    reply_agent = ReplyGuyAgent(x_api=mock_x)
    engagement_agent = EngagementAgent(x_api=mock_x)
    growth_agent = GrowthAgent(x_api=mock_x)
    monitor_agent = MonitorAgent(x_api=mock_x)
    analytics_agent = AnalyticsAgent(x_api=mock_x)

    # Simulate 7 days
    day_logs: list[DayLog] = []
    start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    for day_num in range(1, 8):
        date = start_date + timedelta(days=day_num - 1)
        day_log = run_day(
            day_num=day_num,
            date=date,
            content_agent=content_agent,
            trend_agent=trend_agent,
            reply_agent=reply_agent,
            engagement_agent=engagement_agent,
            growth_agent=growth_agent,
            monitor_agent=monitor_agent,
        )
        day_logs.append(day_log)

    console.print("\n[bold green]7-day simulation complete.[/bold green]")

    # Run analytics
    console.print("\n[blue]Running end-of-week analytics...[/blue]")
    try:
        analytics_agent.refresh_tweet_metrics()
        analytics_agent.update_learnings()
    except Exception as e:
        console.print(f"[yellow]Analytics: {e}[/yellow]")

    # Load updated learnings
    from pathlib import Path as _Path
    import json as _json
    learnings_path = _Path(__file__).parent / "data" / "learnings.json"
    learnings_after: dict[str, Any] = {}
    if learnings_path.exists():
        try:
            learnings_after = _json.loads(learnings_path.read_text())
        except Exception:
            learnings_after = {"error": "Could not load learnings.json"}

    # Build and write report
    console.print("\n[blue]Building report...[/blue]")
    report = build_report(day_logs, learnings_after)

    REPORT_PATH.write_text(report, encoding="utf-8")
    console.print(
        Panel(
            f"Report written to:\n{REPORT_PATH}\n\n"
            f"Days simulated: 7\n"
            f"Threads generated: {sum(len(d.threads) for d in day_logs)}\n"
            f"Single tweets: {sum(len(d.single_tweets) for d in day_logs)}\n"
            f"Reply suggestions: {sum(len(d.reply_suggestions) for d in day_logs)}\n"
            f"Follow suggestions: {sum(len(d.follow_suggestions) for d in day_logs)}",
            title="Dry Run Complete",
            style="bold green",
        )
    )


if __name__ == "__main__":
    main()
