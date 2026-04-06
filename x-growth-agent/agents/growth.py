from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tools import memory as mem
from tools.x_api import XAPIClient

console = Console()

NICHE_KEYWORDS = [
    # People actively seeking supplement advice → potential Supplyn customers
    "recommend supplements",
    "what supplements should",
    # People with proven interest in personalisation and evidence-based health
    "personalised nutrition",
    "blood work supplements",
    # Engaged biohackers — most likely to try supplyn.app
    "biohacking stack",
]

# Follower range for follow candidates
# Min raised to 500 — filters out bots and inactive accounts
MIN_FOLLOWERS = 500
MAX_FOLLOWERS = 200_000

# Daily target
DAILY_SUGGESTION_TARGET = 28  # Aim for 25-30


class GrowthAgent:
    """
    Suggestion-mode agent: identifies follow candidates.
    NEVER auto-follows. All output saved to DB for manual action.
    """

    def __init__(self, x_api: XAPIClient) -> None:
        self.x_api = x_api

    def find_follow_candidates(self) -> list[dict[str, Any]]:
        """
        Search niche keywords for active accounts worth following.

        Filters:
          - 100 < followers < 500K
          - Active in last 7 days (tweet recency proxy)
          - NOT already in follow_suggestions table (pending)
          - Stop at DAILY_SUGGESTION_TARGET per day

        Returns list of candidate dicts.
        """
        console.print("[blue]Finding follow candidates...[/blue]")

        count_today = mem.count_follow_suggestions_today()
        if count_today >= DAILY_SUGGESTION_TARGET:
            console.print(
                f"[yellow]Daily follow suggestion target reached ({count_today}).[/yellow]"
            )
            return []

        remaining = DAILY_SUGGESTION_TARGET - count_today
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        candidates: list[dict[str, Any]] = []
        seen_usernames: set[str] = set()

        # Get existing pending suggestions to avoid duplicates
        existing = mem.get_follow_suggestions(status="pending", limit=500)
        existing_usernames = {s["username"].lower() for s in existing}

        for keyword in NICHE_KEYWORDS:
            if len(candidates) >= remaining:
                break

            try:
                query = f"{keyword} lang:en -is:retweet"
                tweets = self.x_api.search_recent_tweets(query=query, max_results=10)
                if not tweets:
                    continue

                for tweet in tweets:
                    if len(candidates) >= remaining:
                        break

                    username = tweet.get("username", "")
                    if not username:
                        continue

                    username_lower = username.lower()
                    if username_lower in seen_usernames:
                        continue
                    if username_lower in existing_usernames:
                        continue

                    follower_count = tweet.get("follower_count", 0)
                    if not (MIN_FOLLOWERS < follower_count < MAX_FOLLOWERS):
                        continue

                    # Check activity recency via tweet timestamp
                    created_str = tweet.get("created_at", "")
                    if created_str:
                        try:
                            cleaned = created_str.replace(" ", "T")
                            if not cleaned.endswith("+00:00"):
                                cleaned += "+00:00"
                            tweet_time = datetime.fromisoformat(cleaned)
                            if tweet_time < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass

                    seen_usernames.add(username_lower)
                    like_count = tweet.get("like_count", 0)
                    rt_count = tweet.get("retweet_count", 0)

                    # Build reason
                    reason = self._build_reason(
                        keyword=keyword,
                        follower_count=follower_count,
                        like_count=like_count,
                        tweet_text=tweet.get("text", ""),
                    )

                    candidates.append(
                        {
                            "username": username,
                            "follower_count": follower_count,
                            "reason": reason,
                            "keyword": keyword,
                            "like_count": like_count,
                            "rt_count": rt_count,
                            "sample_tweet": tweet.get("text", "")[:200],
                        }
                    )

            except Exception as e:
                console.print(f"[yellow]Growth scan error for '{keyword}': {e}[/yellow]")
                continue

        # Sort by engagement proxy: like_count descending
        candidates.sort(key=lambda x: x.get("like_count", 0), reverse=True)
        console.print(f"[green]Found {len(candidates)} follow candidates.[/green]")
        return candidates

    def _build_reason(
        self,
        keyword: str,
        follower_count: int,
        like_count: int,
        tweet_text: str,
    ) -> str:
        """Build a human-readable reason for the follow suggestion."""
        parts = [f"Active in '{keyword}' conversation"]
        if follower_count > 50_000:
            parts.append(f"large audience ({follower_count:,} followers)")
        elif follower_count > 10_000:
            parts.append(f"mid-size audience ({follower_count:,} followers)")
        else:
            parts.append(f"niche builder ({follower_count:,} followers)")
        if like_count > 100:
            parts.append(f"high engagement ({like_count} likes on recent tweet)")
        return ". ".join(parts) + "."

    def generate_follow_suggestions(self) -> None:
        """Find candidates and save to follow_suggestions table."""
        candidates = self.find_follow_candidates()
        if not candidates:
            console.print("[yellow]No new follow candidates found.[/yellow]")
            return

        saved = 0
        for c in candidates:
            mem.insert_follow_suggestion(
                username=c["username"],
                follower_count=c["follower_count"],
                reason=c["reason"],
            )
            saved += 1

        if candidates:
            from tools import telegram
            telegram.send_follow_suggestions(candidates)

        console.print(f"[green]{saved} follow suggestions saved.[/green]")

    def print_follow_report(self) -> None:
        """
        Print follow suggestions and accounts that may need unfollowing.

        Follow-back status is marked 'verify manually' — the agent can't
        check this without additional API calls.
        """
        suggestions = mem.get_follow_suggestions(status="pending", limit=50)

        # --- Follow Suggestions Table ---
        if suggestions:
            follow_table = Table(
                title=f"Follow Suggestions ({len(suggestions)} pending)",
                show_lines=True,
                expand=True,
            )
            follow_table.add_column("ID", style="dim", width=4)
            follow_table.add_column("Username", style="cyan", width=20)
            follow_table.add_column("Followers", justify="right", width=10)
            follow_table.add_column("Reason", overflow="fold", max_width=60)
            follow_table.add_column("Added", width=12)

            for s in suggestions:
                created = s.get("created_at", "")[:10] if s.get("created_at") else ""
                follow_table.add_row(
                    str(s["id"]),
                    f"@{s['username']}",
                    f"{s.get('follower_count', 0):,}",
                    s.get("reason", ""),
                    created,
                )
            console.print(follow_table)
        else:
            console.print(
                Panel(
                    "No pending follow suggestions.\nRun [bold]generate_follow_suggestions()[/bold] first.",
                    title="Follow Suggestions",
                    style="yellow",
                )
            )

        # --- Followed >5 days ago (potential unfollow candidates) ---
        followed = mem.get_follow_suggestions(status="followed", limit=100)
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        stale = []
        for s in followed:
            created_str = s.get("created_at", "")
            if created_str:
                try:
                    cleaned = created_str.replace(" ", "T")
                    if not cleaned.endswith("+00:00"):
                        cleaned += "+00:00"
                    followed_time = datetime.fromisoformat(cleaned)
                    if followed_time < cutoff:
                        stale.append(s)
                except (ValueError, TypeError):
                    stale.append(s)

        if stale:
            unfollow_table = Table(
                title=f"Potential Unfollow Candidates ({len(stale)}) — Followed >5 days ago",
                show_lines=True,
                expand=True,
            )
            unfollow_table.add_column("Username", style="yellow", width=20)
            unfollow_table.add_column("Followers", justify="right", width=10)
            unfollow_table.add_column("Followed On", width=12)
            unfollow_table.add_column("Follow-Back Status", style="red", width=25)

            for s in stale:
                followed_on = s.get("created_at", "")[:10] if s.get("created_at") else ""
                unfollow_table.add_row(
                    f"@{s['username']}",
                    f"{s.get('follower_count', 0):,}",
                    followed_on,
                    "verify manually",
                )
            console.print(unfollow_table)
            console.print(
                "[dim]Note: Follow-back status requires manual verification on X. "
                "Agent cannot check this without additional API calls.[/dim]"
            )
        else:
            console.print("[dim]No stale followed accounts to review.[/dim]")
