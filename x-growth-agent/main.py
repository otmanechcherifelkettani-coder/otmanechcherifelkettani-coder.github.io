from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Ensure project root is on path when running as script
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

console = Console()


def _make_orchestrator(dry_run: bool, timezone: str) -> "Orchestrator":  # type: ignore[name-defined]
    """Import and create orchestrator (deferred to avoid slow startup on --help)."""
    os.environ.setdefault("TIMEZONE", timezone)
    from orchestrator import Orchestrator
    return Orchestrator(dry_run=dry_run)


@click.group()
@click.option("--dry-run/--no-dry-run", default=False, envvar="DRY_RUN",
              help="If set, no writes are made to the X API.")
@click.option("--timezone", default="UTC", envvar="TIMEZONE",
              help="Timezone for scheduler (e.g. America/New_York).")
@click.pass_context
def cli(ctx: click.Context, dry_run: bool, timezone: str) -> None:
    """X Growth Agent — automated X (Twitter) growth system."""
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    ctx.obj["timezone"] = timezone


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Start the full agent scheduler (runs indefinitely)."""
    dry_run = ctx.obj["dry_run"]
    timezone = ctx.obj["timezone"]
    console.print(
        Panel(
            f"Starting X Growth Agent\ndry_run={dry_run} | timezone={timezone}",
            style="bold green",
        )
    )
    orch = _make_orchestrator(dry_run=dry_run, timezone=timezone)
    orch.run()


@cli.command(name="dry-run")
@click.pass_context
def dry_run_cmd(ctx: click.Context) -> None:
    """Run in dry-run mode — no API writes, all actions logged only."""
    ctx.obj["dry_run"] = True
    console.print(Panel("DRY RUN MODE — no API writes will occur.", style="cyan"))
    orch = _make_orchestrator(dry_run=True, timezone=ctx.obj["timezone"])
    orch.run()


@cli.command()
@click.pass_context
def report(ctx: click.Context) -> None:
    """Generate and print the weekly analytics report."""
    from tools.x_api import XAPIClient
    from agents.analytics import AnalyticsAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = AnalyticsAgent(x_api=x)
    agent.generate_weekly_report()
    ab = agent.ab_test_report()
    console.print(ab)


@cli.command()
@click.pass_context
def trends(ctx: click.Context) -> None:
    """Show current trend opportunities (and scan for new ones)."""
    from tools.x_api import XAPIClient
    from agents.trend_hunter import TrendHunterAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = TrendHunterAgent(x_api=x)
    agent.scan_trends()
    opportunities = agent.get_opportunity_windows()
    if opportunities:
        for opp in opportunities:
            suggestion = agent.suggest_reactive_content(opp)
            console.print(
                Panel(
                    f"[bold]{opp.get('keyword')}[/bold]\n\n"
                    f"Sample: {opp.get('sample_tweet', '')[:120]}\n\n"
                    f"[green]Reactive idea:[/green]\n{suggestion}",
                    title="Trend Opportunity",
                )
            )


@cli.command()
@click.pass_context
def replies(ctx: click.Context) -> None:
    """Show pending reply suggestions (suggestion mode — never auto-posts)."""
    from tools.x_api import XAPIClient
    from agents.reply_guy import ReplyGuyAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = ReplyGuyAgent(x_api=x)
    agent.print_reply_queue()


@cli.command()
@click.pass_context
def engagement(ctx: click.Context) -> None:
    """Show engagement suggestion queue (suggestion mode — never auto-likes)."""
    from tools.x_api import XAPIClient
    from agents.engagement import EngagementAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = EngagementAgent(x_api=x)
    agent.print_engagement_queue()


@cli.command(name="follow-report")
@click.pass_context
def follow_report(ctx: click.Context) -> None:
    """Show follow suggestions and potential unfollow candidates (never auto-follows)."""
    from tools.x_api import XAPIClient
    from agents.growth import GrowthAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = GrowthAgent(x_api=x)
    agent.print_follow_report()


@cli.command()
@click.pass_context
def mentions(ctx: click.Context) -> None:
    """Show unreviewed mentions, sorted by sender follower count."""
    from tools.x_api import XAPIClient
    from agents.monitor import MonitorAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = MonitorAgent(x_api=x)
    agent.check_mentions()
    agent.print_mentions_report()


@cli.command(name="export-replies")
@click.option("--output", default="replies.csv", help="Output CSV filename.")
@click.pass_context
def export_replies(ctx: click.Context, output: str) -> None:
    """Export pending reply suggestions to a CSV file (open in Excel or Google Sheets)."""
    import csv
    from tools import memory as mem

    suggestions = mem.get_pending_replies(limit=500)
    if not suggestions:
        console.print("[yellow]No pending reply suggestions to export.[/yellow]")
        return

    output_path = Path(output)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "account", "strategy", "their_tweet", "suggested_reply", "created_at"
        ])
        writer.writeheader()
        for s in suggestions:
            writer.writerow({
                "id": s.get("id", ""),
                "account": f"@{s.get('vip_account', '')}",
                "strategy": s.get("strategy", ""),
                "their_tweet": s.get("vip_tweet_content", ""),
                "suggested_reply": s.get("suggested_reply", ""),
                "created_at": s.get("created_at", "")[:16] if s.get("created_at") else "",
            })

    console.print(f"[green]Exported {len(suggestions)} reply suggestions to {output_path}[/green]")
    console.print("[dim]Open the CSV in Excel or Google Sheets to review and copy replies.[/dim]")


@cli.command(name="post-thread")
@click.option("--topic", default=None, help="Optional topic override for the thread.")
@click.pass_context
def post_thread(ctx: click.Context, topic: str | None) -> None:
    """Manually trigger thread generation and post (or dry-run preview)."""
    from agents.content_creator import ContentCreatorAgent

    dry_run = ctx.obj["dry_run"]
    agent = ContentCreatorAgent(dry_run=dry_run)
    success = agent.post_thread(topic=topic)
    if success:
        console.print("[green]Thread posted successfully.[/green]")
    else:
        console.print("[yellow]Thread post skipped or failed.[/yellow]")


@cli.command(name="post-tweet")
@click.option(
    "--type",
    "tweet_type",
    default="auto",
    type=click.Choice(["auto", "hot_take", "question", "observation", "meme"]),
    help="Type of tweet to generate.",
)
@click.pass_context
def post_tweet(ctx: click.Context, tweet_type: str) -> None:
    """Manually trigger single tweet generation and post (or dry-run preview)."""
    from agents.content_creator import ContentCreatorAgent

    dry_run = ctx.obj["dry_run"]
    agent = ContentCreatorAgent(dry_run=dry_run)
    success = agent.post_single_tweet(tweet_type=tweet_type)
    if success:
        console.print("[green]Tweet posted successfully.[/green]")
    else:
        console.print("[yellow]Tweet post skipped or failed.[/yellow]")


@cli.command(name="update-learnings")
@click.pass_context
def update_learnings(ctx: click.Context) -> None:
    """Run analytics and update data/learnings.json with this week's patterns."""
    from tools.x_api import XAPIClient
    from agents.analytics import AnalyticsAgent

    dry_run = ctx.obj["dry_run"]
    x = XAPIClient(dry_run=dry_run)
    agent = AnalyticsAgent(x_api=x)
    agent.refresh_tweet_metrics()
    agent.update_learnings()
    console.print("[green]learnings.json updated.[/green]")


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the database and verify API connections."""
    from tools.memory import init_db

    console.print("[blue]Initializing database...[/blue]")
    init_db()

    # Check Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        console.print("[green]ANTHROPIC_API_KEY: set[/green]")
    else:
        console.print("[red]ANTHROPIC_API_KEY: NOT SET — set this in .env[/red]")

    # Check X API
    x_keys = [
        "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET", "X_BEARER_TOKEN",
    ]
    all_x_set = True
    for key in x_keys:
        val = os.getenv(key)
        if val:
            console.print(f"[green]{key}: set[/green]")
        else:
            console.print(f"[red]{key}: NOT SET[/red]")
            all_x_set = False

    if all_x_set:
        from tools.x_api import XAPIClient
        x = XAPIClient(dry_run=ctx.obj["dry_run"])
        console.print("[green]X API client initialized successfully.[/green]")
    else:
        console.print("[yellow]X API credentials incomplete — API calls will fail.[/yellow]")

    console.print(
        Panel(
            "Initialization complete.\n"
            "Next steps:\n"
            "  1. Copy .env.example → .env and fill in credentials\n"
            "  2. Edit persona.md with your voice\n"
            "  3. Run: python main.py run\n"
            "  4. Or test: python main.py --dry-run run",
            title="Setup Complete",
            style="green",
        )
    )


@cli.command(name="telegram-setup")
@click.pass_context
def telegram_setup(ctx: click.Context) -> None:
    """Get your Telegram chat ID and verify the bot is working."""
    import time
    import requests as req

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        console.print("[red]TELEGRAM_BOT_TOKEN not set in .env[/red]")
        console.print("[dim]Add it to .env: TELEGRAM_BOT_TOKEN=your_token[/dim]")
        return

    console.print("[blue]Send any message to your Telegram bot now...[/blue]")
    console.print("[dim]Waiting up to 60 seconds...[/dim]")

    for attempt in range(60):
        try:
            resp = req.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                timeout=5,
            )
            if resp.ok:
                updates = resp.json().get("result", [])
                if updates:
                    msg = updates[-1].get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    username = msg.get("chat", {}).get("username", "")
                    if chat_id:
                        console.print(
                            Panel(
                                f"Chat ID found: [bold green]{chat_id}[/bold green]\n"
                                f"Username: @{username}\n\n"
                                f"Add to your .env on the server:\n"
                                f"[bold]TELEGRAM_CHAT_ID={chat_id}[/bold]",
                                title="Telegram Setup Complete",
                                style="green",
                            )
                        )
                        # Send a test message
                        from tools.telegram import send
                        send(
                            "✅ <b>Supplyn agent connected!</b>\n\n"
                            "You'll receive daily briefs, content recommendations, "
                            "reply opportunities, and follow suggestions here.\n\n"
                            "Welcome to your X assistant 🚀"
                        )
                        return
        except Exception as e:
            console.print(f"[dim]Waiting... ({e})[/dim]")
        time.sleep(1)

    console.print("[yellow]No message received in 60s. Make sure you sent a message to your bot.[/yellow]")


if __name__ == "__main__":
    cli(obj={})
