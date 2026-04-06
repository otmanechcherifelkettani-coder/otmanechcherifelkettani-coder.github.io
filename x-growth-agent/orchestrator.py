from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

console = Console()

# Blackout hours (UTC) — no jobs fire during these hours
BLACKOUT_START = 1
BLACKOUT_END = 7


def _in_blackout() -> bool:
    """Return True if current UTC hour is in blackout window (1 AM–7 AM)."""
    hour = datetime.now(timezone.utc).hour
    return BLACKOUT_START <= hour < BLACKOUT_END


def _safe_run(name: str, fn: Any, *args: Any, **kwargs: Any) -> None:
    """Run a scheduled function with blackout check and error handling."""
    if _in_blackout():
        console.print(f"[dim]Blackout window — skipping {name}.[/dim]")
        return
    console.print(f"[blue]Running scheduled task: {name}[/blue]")
    try:
        fn(*args, **kwargs)
    except Exception as e:
        console.print(f"[red]Error in {name}: {e}[/red]")


class Orchestrator:
    """
    Central scheduler that initializes all agents and manages their schedules.

    Suggestion mode (never auto-post):
      - ReplyGuyAgent: drafts replies to VIP accounts for manual posting
      - GrowthAgent: surfaces follow candidates for manual action

    Fully automated:
      - ContentCreatorAgent: posts threads and single tweets on schedule
      - AnalyticsAgent: weekly learnings update
      - MonitorAgent: weekly mention review
    """

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.timezone_str = os.getenv("TIMEZONE", "UTC")
        self._init_agents()
        self._scheduler = BlockingScheduler(timezone=self.timezone_str)
        self._register_jobs()

    def _init_agents(self) -> None:
        """Initialize all agents."""
        from tools.x_api import XAPIClient
        from agents.content_creator import ContentCreatorAgent
        from agents.reply_guy import ReplyGuyAgent
        from agents.growth import GrowthAgent
        from agents.monitor import MonitorAgent
        from agents.analytics import AnalyticsAgent

        self.x_api = XAPIClient(dry_run=self.dry_run)
        self.content = ContentCreatorAgent(dry_run=self.dry_run)
        self.reply_guy = ReplyGuyAgent(x_api=self.x_api)
        self.growth = GrowthAgent(x_api=self.x_api)
        self.monitor = MonitorAgent(x_api=self.x_api)
        self.analytics = AnalyticsAgent(x_api=self.x_api)

        console.print(
            Panel(
                f"All agents initialized.\ndry_run={self.dry_run} | timezone={self.timezone_str}",
                title="Orchestrator",
                style="green",
            )
        )

    def _register_jobs(self) -> None:
        """Register all scheduled jobs with APScheduler."""
        s = self._scheduler
        tz = self.timezone_str

        # ─── Morning brief — 7:55 AM daily (before jobs fire) ───────────────────
        s.add_job(
            lambda: _safe_run("Telegram.morning_brief", self._morning_brief),
            CronTrigger(hour=7, minute=55, timezone=tz),
            id="morning_brief",
            replace_existing=True,
        )

        # ─── Mention monitoring — once per week (Sunday 3 PM) ───────────────────
        s.add_job(
            lambda: _safe_run("Monitor.check_mentions", self.monitor.check_mentions),
            CronTrigger(hour=15, minute=0, day_of_week="sun", timezone=tz),
            id="monitor_mentions",
            replace_existing=True,
        )

        # ─── Thread post — 8:30 AM Mon/Wed/Fri ──────────────────────────────────
        s.add_job(
            lambda: _safe_run("Content.post_thread", self.content.post_thread),
            CronTrigger(hour=8, minute=30, day_of_week="mon,wed,fri", timezone=tz),
            id="thread_mwf",
            replace_existing=True,
        )

        # ─── Single tweet — 8:30 AM Tue/Thu/Sat ─────────────────────────────────
        # Tue/Thu = hot_take or question (growth), Sat = conversion (sales)
        s.add_job(
            lambda: _safe_run("Content.post_single_tweet [morning]", self.content.post_single_tweet),
            CronTrigger(hour=8, minute=30, day_of_week="tue,thu", timezone=tz),
            id="single_tue_thu_morning",
            replace_existing=True,
        )
        s.add_job(
            lambda: _safe_run("Content.post_conversion [saturday]",
                              lambda: self.content.post_single_tweet(tweet_type="conversion")),
            CronTrigger(hour=9, minute=0, day_of_week="sat", timezone=tz),
            id="single_sat_conversion",
            replace_existing=True,
        )

        # ─── Single tweet — 12:15 PM daily (education/growth content) ───────────
        s.add_job(
            lambda: _safe_run("Content.post_single_tweet [noon]", self.content.post_single_tweet),
            CronTrigger(hour=12, minute=15, timezone=tz),
            id="single_noon",
            replace_existing=True,
        )

        # ─── Conversion tweet — 7:30 PM Wed/Sun ─────────────────────────────────
        # Peak engagement window, lower competition than morning, drives evening signups
        s.add_job(
            lambda: _safe_run("Content.post_conversion [evening]",
                              lambda: self.content.post_single_tweet(tweet_type="conversion")),
            CronTrigger(hour=19, minute=30, day_of_week="wed,sun", timezone=tz),
            id="conversion_wed_sun",
            replace_existing=True,
        )

        # ─── Evening content — 6:45 PM daily ────────────────────────────────────
        # Alternates thread (Mon/Wed/Fri) vs single tweet (other days)
        s.add_job(
            lambda: _safe_run(
                "Content.evening_post",
                self._evening_post,
            ),
            CronTrigger(hour=18, minute=45, timezone=tz),
            id="evening_post",
            replace_existing=True,
        )

        # ─── Reply queue generation — twice per day ─────────────────────────────
        # Morning catches VIP tweets from early posts, afternoon catches lunch posts
        s.add_job(
            lambda: _safe_run(
                "ReplyGuy.generate_reply_queue",
                self.reply_guy.generate_reply_queue,
            ),
            CronTrigger(hour="8,13", minute=5, timezone=tz),
            id="reply_queue",
            replace_existing=True,
        )

        # ─── Follow suggestions — every 2 days ──────────────────────────────────
        s.add_job(
            lambda: _safe_run(
                "Growth.generate_follow_suggestions",
                self.growth.generate_follow_suggestions,
            ),
            CronTrigger(hour=10, minute=10, day="*/2", timezone=tz),
            id="follow_suggestions",
            replace_existing=True,
        )

        # ─── Weekly learnings update — 9 PM Sunday ──────────────────────────────
        s.add_job(
            lambda: _safe_run(
                "Analytics.weekly_update",
                self._weekly_update,
            ),
            CronTrigger(hour=21, minute=0, day_of_week="sun", timezone=tz),
            id="weekly_update",
            replace_existing=True,
        )

        console.print(f"[green]Registered {len(s.get_jobs())} scheduled jobs.[/green]")

    def _evening_post(self) -> None:
        """Evening post: thread on Mon/Wed/Fri, single tweet otherwise."""
        weekday = datetime.now(timezone.utc).weekday()  # 0=Mon, 2=Wed, 4=Fri
        if weekday in (0, 2, 4):
            self.content.post_thread()
        else:
            self.content.post_single_tweet()

    def _morning_brief(self) -> None:
        """Send a morning summary to Telegram before the day's jobs fire."""
        from tools import telegram, memory as mem

        if not telegram.is_configured():
            return

        weekday = datetime.now(timezone.utc).weekday()  # 0=Mon
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day = day_names[weekday]
        date_str = datetime.now(timezone.utc).strftime(f"{day} %d %b")

        if weekday in (0, 2, 4):
            post_schedule = "8:30 AM thread + 12:15 PM tweet + 6:45 PM thread"
        elif weekday == 5:
            post_schedule = "9:00 AM conversion tweet + 12:15 PM tweet + 6:45 PM tweet"
        elif weekday == 6:
            post_schedule = "12:15 PM tweet + 6:45 PM tweet + 7:30 PM conversion tweet"
        else:
            post_schedule = "8:30 AM tweet + 12:15 PM tweet + 6:45 PM tweet"

        reply_count = len(mem.get_pending_replies(limit=1000))
        follow_count = len(mem.get_follow_suggestions(status="pending", limit=1000))
        trend_count = len(mem.get_trends_last_n_hours(hours=24))

        telegram.send_morning_brief(
            date_str=date_str,
            post_schedule=post_schedule,
            reply_count=reply_count,
            follow_count=follow_count,
            trend_count=trend_count,
        )

    def _weekly_update(self) -> None:
        """Run analytics update and generate weekly report."""
        report = self.analytics.generate_weekly_report()
        self.analytics.update_learnings()
        console.print(
            Panel(report[:2000] + "..." if len(report) > 2000 else report,
                  title="Weekly Report",
                  style="blue")
        )

    def run(self) -> None:
        """Start the scheduler. Blocks until interrupted."""
        console.print(
            Panel(
                "X Growth Agent scheduler starting.\n"
                f"Timezone: {self.timezone_str}\n"
                f"Dry run: {self.dry_run}\n"
                "Press Ctrl+C to stop.",
                title="Starting",
                style="bold green",
            )
        )
        try:
            self._scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            console.print("\n[yellow]Scheduler stopped.[/yellow]")

    def run_once(self, task: str) -> None:
        """Manually trigger a specific task by name."""
        task_map: dict[str, Any] = {
            "check_mentions": self.monitor.check_mentions,
            "post_thread": self.content.post_thread,
            "post_single_tweet": self.content.post_single_tweet,
            "reply_queue": self.reply_guy.generate_reply_queue,
            "follow_suggestions": self.growth.generate_follow_suggestions,
            "weekly_update": self._weekly_update,
            "refresh_metrics": self.analytics.refresh_tweet_metrics,
            "update_learnings": self.analytics.update_learnings,
        }

        if task not in task_map:
            console.print(
                f"[red]Unknown task: {task}\n"
                f"Available: {', '.join(task_map.keys())}[/red]"
            )
            return

        console.print(f"[blue]Running task: {task}[/blue]")
        try:
            task_map[task]()
        except Exception as e:
            console.print(f"[red]Task {task} failed: {e}[/red]")

    def daily_report(self) -> str:
        """Generate a summary of today's actions and queue sizes."""
        from tools import memory as mem

        pending_replies = len(mem.get_pending_replies(limit=1000))
        pending_engagement = len(mem.get_engagement_suggestions(status="pending", limit=1000))
        pending_follows = len(mem.get_follow_suggestions(status="pending", limit=1000))
        high_value_mentions = len(mem.get_high_value_mentions())
        recent_trends = len(mem.get_trends_last_n_hours(hours=24))

        table = Table(title="Daily Agent Report", show_lines=True)
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("Action Needed", style="yellow")

        table.add_row("Pending reply suggestions", str(pending_replies), "Review & post manually")
        table.add_row("Engagement suggestions", str(pending_engagement), "Like/quote manually")
        table.add_row("Follow suggestions", str(pending_follows), "Follow manually on X")
        table.add_row("High-value unread mentions", str(high_value_mentions), "Respond personally")
        table.add_row("Trends (last 24h)", str(recent_trends), "Consider reactive content")

        console.print(table)

        summary = (
            f"Daily Report ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}):\n"
            f"  Reply queue: {pending_replies} pending\n"
            f"  Engagement queue: {pending_engagement} pending\n"
            f"  Follow suggestions: {pending_follows} pending\n"
            f"  High-value mentions: {high_value_mentions} unread\n"
            f"  Trends detected: {recent_trends}\n"
        )
        return summary
