from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from tools import memory as mem
from tools.llm import call_haiku
from tools.x_api import XAPIClient

console = Console()

NICHE_KEYWORDS = [
    "supplement stack",
    "personalised nutrition",
    "vitamin D deficiency",
]

# Daily caps
MAX_LIKE_SUGGESTIONS_PER_DAY = 30
MAX_QUOTE_SUGGESTIONS_PER_DAY = 5

# Follower range for engagement targets
MIN_FOLLOWERS = 1_000
MAX_FOLLOWERS = 500_000


class EngagementAgent:
    """
    Suggestion-mode agent: surfaces high-momentum content to like or quote-tweet.
    NEVER auto-likes or auto-retweets. All output saved to DB for manual action.
    """

    def __init__(self, x_api: XAPIClient) -> None:
        self.x_api = x_api

    def find_engagement_opportunities(self) -> list[dict[str, Any]]:
        """
        Search niche keywords for tweets <1hr old with momentum.

        Filters:
          - Author followers: 5K–500K
          - Not already in engagement_suggestions today
          - Max 30 like + 5 quote suggestions per day

        Returns list of opportunity dicts.
        """
        console.print("[blue]Finding engagement opportunities...[/blue]")

        like_count_today = mem.count_engagement_suggestions_today("like")
        quote_count_today = mem.count_engagement_suggestions_today("quote")

        if like_count_today >= MAX_LIKE_SUGGESTIONS_PER_DAY and quote_count_today >= MAX_QUOTE_SUGGESTIONS_PER_DAY:
            console.print(
                f"[yellow]Daily engagement caps reached "
                f"(likes: {like_count_today}/{MAX_LIKE_SUGGESTIONS_PER_DAY}, "
                f"quotes: {quote_count_today}/{MAX_QUOTE_SUGGESTIONS_PER_DAY}).[/yellow]"
            )
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
        opportunities: list[dict[str, Any]] = []
        seen_tweet_ids: set[str] = set()

        for keyword in NICHE_KEYWORDS:
            if (like_count_today + len([o for o in opportunities if o["suggestion_type"] == "like"])) >= MAX_LIKE_SUGGESTIONS_PER_DAY:
                break

            try:
                query = f"{keyword} lang:en -is:retweet"
                tweets = self.x_api.search_recent_tweets(query=query, max_results=10)
                if not tweets:
                    continue

                for tweet in tweets:
                    tweet_id = tweet.get("id", "")
                    if tweet_id in seen_tweet_ids:
                        continue

                    # Filter by follower count
                    follower_count = tweet.get("follower_count", 0)
                    if not (MIN_FOLLOWERS <= follower_count <= MAX_FOLLOWERS):
                        continue

                    # Filter by recency
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

                    like_c = tweet.get("like_count", 0)
                    rt_c = tweet.get("retweet_count", 0)

                    # Determine suggestion type
                    # Suggest quote if high engagement and within quote budget
                    suggestion_type = "like"
                    existing_quotes = len([o for o in opportunities if o["suggestion_type"] == "quote"])
                    if (
                        like_c >= 50
                        and rt_c >= 10
                        and (quote_count_today + existing_quotes) < MAX_QUOTE_SUGGESTIONS_PER_DAY
                    ):
                        suggestion_type = "quote"

                    seen_tweet_ids.add(tweet_id)
                    opp: dict[str, Any] = {
                        "tweet_id": tweet_id,
                        "account": tweet.get("username", ""),
                        "content": tweet.get("text", ""),
                        "follower_count": follower_count,
                        "like_count": like_c,
                        "retweet_count": rt_c,
                        "suggestion_type": suggestion_type,
                        "keyword": keyword,
                    }

                    # For quote tweets, draft the content
                    if suggestion_type == "quote":
                        opp["quote_content"] = self.draft_quote_tweet(opp)

                    opportunities.append(opp)

            except Exception as e:
                console.print(f"[yellow]Engagement scan error for '{keyword}': {e}[/yellow]")
                continue

        console.print(f"[green]Found {len(opportunities)} engagement opportunities.[/green]")
        return opportunities

    def draft_quote_tweet(self, tweet: dict[str, Any]) -> str:
        """
        Generate strong opinionated quote-tweet content for a tweet.

        Uses haiku for speed. Returns the quote-tweet text.
        """
        account = tweet.get("account", "someone")
        content = tweet.get("content", "")

        prompt = f"""Write a strong, opinionated quote-tweet for this tweet by @{account}:

"{content}"

RULES:
- Under 200 characters (room for quoted tweet)
- Add genuine value — an insight, pushback, or sharp extension
- Never sycophantic
- No bullet points, contractions always, never start with "I"
- Direct and confident

Write ONLY the quote-tweet text."""

        response = call_haiku(prompt)
        return response.strip() if response else "Worth reading — this connects to something bigger."

    def generate_engagement_queue(self) -> None:
        """Find opportunities and save them to the engagement_suggestions table."""
        opportunities = self.find_engagement_opportunities()
        if not opportunities:
            return

        saved = 0
        telegram_items: list[dict] = []

        for opp in opportunities:
            content = opp.get("content", "")
            if opp["suggestion_type"] == "quote" and opp.get("quote_content"):
                content = f"[QUOTE]: {opp['quote_content']}\n\n[ORIGINAL]: {content}"

            mem.insert_engagement_suggestion(
                tweet_id=opp["tweet_id"],
                account=opp["account"],
                content=content,
                suggestion_type=opp["suggestion_type"],
            )
            telegram_items.append({
                "tweet_id": opp["tweet_id"],
                "account": opp["account"],
                "content": content,
                "suggestion_type": opp["suggestion_type"],
                "like_count": opp.get("like_count", 0),
                "quote_content": opp.get("quote_content", ""),
            })
            saved += 1

        if telegram_items:
            from tools import telegram
            telegram.send_engagement_suggestions(telegram_items)

        console.print(f"[green]{saved} engagement suggestions saved to queue.[/green]")

    def print_engagement_queue(self) -> None:
        """Pretty-print engagement suggestions with rich table."""
        suggestions = mem.get_engagement_suggestions(status="pending", limit=30)

        if not suggestions:
            console.print(
                Panel(
                    "No pending engagement suggestions.\nRun [bold]generate_engagement_queue()[/bold] first.",
                    title="Engagement Queue",
                    style="yellow",
                )
            )
            return

        table = Table(
            title=f"Engagement Queue ({len(suggestions)} pending)",
            show_lines=True,
            expand=True,
        )
        table.add_column("ID", style="dim", width=4)
        table.add_column("Type", style="magenta", width=8)
        table.add_column("Account", style="cyan", width=20)
        table.add_column("Content / Action", overflow="fold", max_width=80)
        table.add_column("Created", width=12)

        for s in suggestions:
            created = s.get("created_at", "")[:16] if s.get("created_at") else ""
            content = s.get("content", "")
            action_label = (
                "[bold yellow]LIKE →[/bold yellow]"
                if s.get("suggestion_type") == "like"
                else "[bold green]QUOTE →[/bold green]"
            )
            table.add_row(
                str(s["id"]),
                s.get("suggestion_type", ""),
                f"@{s.get('account', '')}",
                f"{action_label} {content[:120]}..." if len(content) > 120 else f"{action_label} {content}",
                created,
            )

        console.print(table)
        console.print(
            "\n[dim]Act on these manually on X. Update status via SQL or CLI.[/dim]"
        )
