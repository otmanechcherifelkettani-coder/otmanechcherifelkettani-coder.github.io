from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tools import memory as mem
from tools.x_api import XAPIClient

console = Console()

HIGH_VALUE_FOLLOWER_THRESHOLD = 1_000
STATE_KEY_LAST_MENTION_ID = "last_mention_id"


class MonitorAgent:
    """Monitors mentions and flags high-value interactions."""

    def __init__(self, x_api: XAPIClient) -> None:
        self.x_api = x_api

    def check_mentions(self) -> list[dict[str, Any]]:
        """
        Fetch mentions since the last stored mention ID.

        - Flags as high-value if sender has >1K followers.
        - Saves all mentions to the mentions table.
        - Persists the latest mention ID for next run.

        Returns list of high-value mentions.
        """
        last_id = mem.get_agent_state(STATE_KEY_LAST_MENTION_ID)
        console.print(
            f"[blue]Checking mentions (since_id={last_id or 'beginning'})...[/blue]"
        )

        mentions = self.x_api.get_mentions(since_id=last_id)
        if not mentions:
            console.print("[dim]No new mentions.[/dim]")
            return []

        newest_id: str | None = None
        high_value: list[dict[str, Any]] = []

        for mention in mentions:
            tweet_id = mention.get("id", "")
            from_user = mention.get("username", "")
            follower_count = mention.get("follower_count", 0)
            content = mention.get("text", "")
            is_high_value = follower_count >= HIGH_VALUE_FOLLOWER_THRESHOLD

            mem.insert_mention(
                tweet_id=tweet_id,
                from_user=from_user,
                follower_count=follower_count,
                content=content,
                flagged_high_value=is_high_value,
            )

            if is_high_value:
                high_value.append(mention)

            # Track newest mention ID (they arrive newest-first from API)
            if newest_id is None:
                newest_id = tweet_id

        # Persist the latest mention ID
        if newest_id:
            mem.set_agent_state(STATE_KEY_LAST_MENTION_ID, newest_id)

        console.print(
            f"[green]{len(mentions)} mentions saved. "
            f"{len(high_value)} high-value (>{HIGH_VALUE_FOLLOWER_THRESHOLD:,} followers).[/green]"
        )

        if high_value:
            console.print("[bold yellow]High-value mentions:[/bold yellow]")
            for m in high_value:
                console.print(
                    f"  [@{m.get('username', '?')} | "
                    f"{m.get('follower_count', 0):,} followers] "
                    f"{m.get('text', '')[:80]}"
                )

        return high_value

    def print_mentions_report(self) -> None:
        """Print all unreviewed mentions sorted by sender follower count."""
        mentions = mem.get_all_unreviewed_mentions()

        if not mentions:
            console.print(
                Panel(
                    "No unreviewed mentions.\nRun [bold]check_mentions()[/bold] first.",
                    title="Mentions Report",
                    style="yellow",
                )
            )
            return

        table = Table(
            title=f"Unreviewed Mentions ({len(mentions)})",
            show_lines=True,
            expand=True,
        )
        table.add_column("ID", style="dim", width=4)
        table.add_column("From", style="cyan", width=20)
        table.add_column("Followers", justify="right", width=10)
        table.add_column("High Value", justify="center", width=10)
        table.add_column("Content", overflow="fold", max_width=70)
        table.add_column("Received", width=12)

        for m in mentions:
            is_hv = bool(m.get("flagged_high_value", 0))
            hv_label = "[bold green]YES[/bold green]" if is_hv else "[dim]no[/dim]"
            created = m.get("created_at", "")[:16] if m.get("created_at") else ""
            content = m.get("content", "")
            table.add_row(
                str(m["id"]),
                f"@{m.get('from_user', '')}",
                f"{m.get('follower_count', 0):,}",
                hv_label,
                content[:150] + "..." if len(content) > 150 else content,
                created,
            )

        console.print(table)
        console.print(
            "\n[dim]High-value mentions deserve a personal reply. "
            "Mark reviewed by updating 'reviewed=1' in the mentions table.[/dim]"
        )

    def get_high_value_mentions(self) -> list[dict[str, Any]]:
        """Return mentions from accounts with >1K followers that haven't been actioned."""
        mentions = mem.get_high_value_mentions(min_followers=HIGH_VALUE_FOLLOWER_THRESHOLD)
        console.print(f"[blue]{len(mentions)} high-value unreviewed mentions.[/blue]")
        return mentions
