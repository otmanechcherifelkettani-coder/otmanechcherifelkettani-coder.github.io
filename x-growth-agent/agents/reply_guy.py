from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tools import memory as mem
from tools.llm import call_haiku
from tools.x_api import XAPIClient

console = Console()

VIP_ACCOUNTS_PATH = Path(__file__).parent.parent / "data" / "vip_accounts.txt"

STRATEGY_WEIGHTS = {
    "insight": 0.40,
    "disagree": 0.30,
    "question": 0.20,
    "humor": 0.10,
}

STRATEGY_INSTRUCTIONS = {
    "insight": (
        "Add a concrete, specific insight that extends or deepens their point. "
        "Teach the reader something they didn't know. Be precise — not vague."
    ),
    "disagree": (
        "Respectfully but clearly disagree with one specific part of their claim. "
        "Explain why you think they're wrong or missing something important. "
        "Back it up with reasoning, not just assertion."
    ),
    "question": (
        "Ask a genuinely curious, non-obvious follow-up question that reveals "
        "you've thought deeply about their point. Should make them want to engage."
    ),
    "humor": (
        "A light, self-aware, slightly dry take that riffs on their point. "
        "Insider humor the niche will appreciate. Not a joke — more of a wry observation."
    ),
}


def _load_vip_accounts() -> list[str]:
    """Load VIP accounts from file, stripping comments and blank lines."""
    if not VIP_ACCOUNTS_PATH.exists():
        console.print(f"[yellow]VIP accounts file not found: {VIP_ACCOUNTS_PATH}[/yellow]")
        return []
    accounts: list[str] = []
    for line in VIP_ACCOUNTS_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            accounts.append(line)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = []
    for a in accounts:
        a_lower = a.lower()
        if a_lower not in seen:
            seen.add(a_lower)
            unique.append(a)
    return unique


def _weighted_strategy() -> str:
    """Pick a reply strategy using defined weights."""
    strategies = list(STRATEGY_WEIGHTS.keys())
    weights = [STRATEGY_WEIGHTS[s] for s in strategies]
    return random.choices(strategies, weights=weights, k=1)[0]


class ReplyGuyAgent:
    """
    Suggestion-mode agent: drafts reply suggestions for VIP accounts.
    NEVER auto-posts. All output saved to DB for manual review.
    """

    def __init__(self, x_api: XAPIClient) -> None:
        self.x_api = x_api

    def scan_vip_accounts(self) -> list[dict[str, Any]]:
        """
        Fetch recent tweets from VIP accounts.

        Filters:
          - Tweets posted in the last 2 hours
          - Not already saved in reply_suggestions table

        Returns list of new tweet opportunities.
        """
        vip_accounts = _load_vip_accounts()
        if not vip_accounts:
            console.print("[yellow]No VIP accounts loaded.[/yellow]")
            return []

        console.print(f"[blue]Scanning {len(vip_accounts)} VIP accounts...[/blue]")
        opportunities: list[dict[str, Any]] = []

        for account in vip_accounts:
            try:
                tweets = self.x_api.get_user_timeline(account, max_results=5)
                if not tweets:
                    continue

                for tweet in tweets:
                    tweet_id = tweet.get("id", "")
                    if not tweet_id:
                        continue

                    # Skip if already saved — this is the only dedup needed
                    if mem.vip_tweet_already_saved(tweet_id):
                        continue

                    created_str = tweet.get("created_at", "")
                    opportunities.append(
                        {
                            "account": account,
                            "tweet_id": tweet_id,
                            "tweet_text": tweet.get("text", ""),
                            "like_count": tweet.get("like_count", 0),
                            "follower_count": tweet.get("follower_count", 0),
                            "created_at": created_str,
                        }
                    )
                    break  # Only take the most recent unseen tweet per VIP

            except Exception as e:
                console.print(f"[yellow]Error scanning @{account}: {e}[/yellow]")
                continue

        console.print(f"[green]Found {len(opportunities)} new VIP tweet opportunities.[/green]")
        return opportunities

    def draft_reply(self, tweet: dict[str, Any], strategy: str = "auto") -> str:
        """
        Draft a reply to a VIP tweet.

        strategy: insight | disagree | question | humor | auto
        auto uses weighted random selection.
        Aims for under 200 characters.
        """
        if strategy == "auto":
            strategy = _weighted_strategy()

        account = tweet.get("account", "unknown")
        tweet_text = tweet.get("tweet_text", "")
        instruction = STRATEGY_INSTRUCTIONS.get(strategy, STRATEGY_INSTRUCTIONS["insight"])

        prompt = f"""You are the founder of Supplyn.app replying to a tweet by @{account} from within the supplements/health niche.

THEIR TWEET:
"{tweet_text}"

REPLY STRATEGY: {strategy.upper()}
{instruction}

CONTEXT: You're building Supplyn.app — an AI-powered personalised supplement stack builder. Your replies should position you as the sharp, evidence-based voice in this space. You're not here to sell — you're here to be the smartest person in the thread. If your reply naturally connects to personalisation, supplement confusion, or the broken supplement industry, tie it in. If it doesn't fit naturally, don't force it.

RULES:
- Under 200 characters (leaves room for the quoted tweet)
- Never sycophantic — no "great point!", "love this!", "so true!"
- Add a specific fact, a number, a mechanism, or a direct challenge — not a vague opinion
- No bullet points, contractions always, never start with "I"
- Sound like a founder who knows this space deeply, not a fan or a marketer
- If you mention Supplyn, it must feel earned and natural — never an ad

Write ONLY the reply text. Nothing else."""

        response = call_haiku(prompt)
        return response.strip() if response else f"Interesting framing — the part about X is worth pushing on."

    def generate_reply_queue(self) -> int:
        """
        Scan VIP accounts, draft replies, save to reply_suggestions table.

        Returns count of new suggestions generated.
        """
        opportunities = self.scan_vip_accounts()
        if not opportunities:
            console.print("[yellow]No new VIP tweets to reply to.[/yellow]")
            return 0

        count = 0
        telegram_items: list[dict] = []

        for opp in opportunities:
            strategy = _weighted_strategy()
            reply = self.draft_reply(opp, strategy=strategy)
            if reply:
                mem.insert_reply_suggestion(
                    vip_account=opp["account"],
                    vip_tweet_id=opp["tweet_id"],
                    vip_tweet_content=opp["tweet_text"],
                    suggested_reply=reply,
                    strategy=strategy,
                )
                telegram_items.append({
                    "account": opp["account"],
                    "tweet_id": opp["tweet_id"],
                    "tweet_text": opp["tweet_text"],
                    "suggested_reply": reply,
                    "strategy": strategy,
                    "like_count": opp.get("like_count", 0),
                })
                count += 1
                console.print(
                    f"[dim]  Drafted reply for @{opp['account']} ({strategy})[/dim]"
                )

        if telegram_items:
            from tools import telegram
            telegram.send_reply_opportunities(telegram_items)

        console.print(
            f"[green]Reply queue: {count} new suggestions added.[/green]"
        )
        return count

    def print_reply_queue(self) -> None:
        """Pretty-print pending reply suggestions using a rich table."""
        suggestions = mem.get_pending_replies(limit=30)

        if not suggestions:
            console.print(
                Panel(
                    "No pending reply suggestions.\nRun [bold]generate_reply_queue()[/bold] first.",
                    title="Reply Queue",
                    style="yellow",
                )
            )
            return

        table = Table(
            title=f"Pending Reply Suggestions ({len(suggestions)})",
            show_lines=True,
            expand=True,
        )
        table.add_column("ID", style="dim", width=4)
        table.add_column("Account", style="cyan", width=15)
        table.add_column("Strategy", style="magenta", width=10)
        table.add_column("Their Tweet", max_width=50, overflow="fold")
        table.add_column("Suggested Reply", max_width=60, overflow="fold", style="green")
        table.add_column("Created", width=12)

        for s in suggestions:
            created = s.get("created_at", "")[:16] if s.get("created_at") else ""
            vip_content = s.get("vip_tweet_content", "")
            snippet = vip_content[:100] + "..." if len(vip_content) > 100 else vip_content
            table.add_row(
                str(s["id"]),
                f"@{s['vip_account']}",
                s.get("strategy", ""),
                snippet,
                s.get("suggested_reply", ""),
                created,
            )

        console.print(table)
        console.print(
            "\n[dim]To post: copy reply text and paste on X. "
            "Then run [bold]mark_posted(id)[/bold] or [bold]mark_skipped(id)[/bold].[/dim]"
        )

    def mark_posted(self, suggestion_id: int) -> None:
        """Mark a reply suggestion as posted."""
        now = datetime.now(timezone.utc).isoformat()
        mem.update_reply_status(suggestion_id, status="posted", posted_at=now)
        console.print(f"[green]Reply {suggestion_id} marked as posted.[/green]")

    def mark_skipped(self, suggestion_id: int) -> None:
        """Mark a reply suggestion as skipped."""
        mem.update_reply_status(suggestion_id, status="skipped")
        console.print(f"[yellow]Reply {suggestion_id} marked as skipped.[/yellow]")
