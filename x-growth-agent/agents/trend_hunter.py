from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from tools import memory as mem
from tools.llm import call_haiku
from tools.x_api import XAPIClient

console = Console()

NICHE_KEYWORDS = [
    "supplement stack",
    "vitamin D deficiency",
    "AG1 greens",
    "Andrew Huberman supplements",
    "personalised nutrition",
    "gut health supplements",
    "creatine benefits",
    "biohacking supplements",
]

# Minimum likes to surface a tweet as an opportunity
MIN_LIKES = 5


class TrendHunterAgent:
    """Scans for trending topics in the niche and surfaces opportunity windows."""

    def __init__(self, x_api: XAPIClient) -> None:
        self.x_api = x_api

    def scan_trends(self) -> list[dict[str, Any]]:
        """
        Search each niche keyword for tweets gaining velocity.

        Criteria: >50 likes in <4 hours.
        Deduplicates by keyword, stores in trends table.
        Returns top 5 opportunities sorted by tweet_count.
        """
        console.print("[blue]Scanning for niche trends...[/blue]")
        found: list[dict[str, Any]] = []
        seen_tweet_ids: set[str] = set()

        for keyword in NICHE_KEYWORDS:
            try:
                # Build query: keyword, English, no retweets, recent
                query = f"{keyword} lang:en -is:retweet"
                tweets = self.x_api.search_recent_tweets(query=query, max_results=10)

                if not tweets:
                    continue

                for tweet in tweets:
                    tweet_id = tweet.get("id", "")
                    if tweet_id in seen_tweet_ids:
                        continue

                    created_str = tweet.get("created_at", "")
                    like_count = tweet.get("like_count", 0)

                    if like_count >= MIN_LIKES:
                        seen_tweet_ids.add(tweet_id)
                        found.append(
                            {
                                "keyword": keyword,
                                "tweet_id": tweet_id,
                                "tweet_text": tweet.get("text", ""),
                                "like_count": like_count,
                                "velocity": like_count,
                                "username": tweet.get("username", ""),
                                "created_at": created_str,
                            }
                        )

            except Exception as e:
                console.print(f"[yellow]Trend scan error for '{keyword}': {e}[/yellow]")
                continue

        # Deduplicate by keyword — keep highest velocity per keyword
        best_by_keyword: dict[str, dict[str, Any]] = {}
        for item in found:
            kw = item["keyword"]
            if kw not in best_by_keyword or item["velocity"] > best_by_keyword[kw]["velocity"]:
                best_by_keyword[kw] = item

        top_trends = sorted(
            best_by_keyword.values(),
            key=lambda x: x["velocity"],
            reverse=True,
        )[:5]

        # Save to DB and send alerts to Telegram
        from tools import telegram
        for trend in top_trends:
            mem.insert_trend(
                keyword=trend["keyword"],
                tweet_count=trend["like_count"],
                sample_tweet=trend["tweet_text"][:500],
            )
            reactive = self.suggest_reactive_content(trend)
            telegram.send_trend_alert(
                keyword=trend["keyword"],
                velocity=trend["velocity"],
                sample_tweet=trend["tweet_text"],
                reactive_idea=reactive,
            )

        if top_trends:
            table = Table(title="Top Trend Opportunities", show_lines=True)
            table.add_column("Keyword", style="cyan")
            table.add_column("Likes", justify="right")
            table.add_column("Velocity (likes/hr)", justify="right")
            table.add_column("Sample", max_width=60)
            for t in top_trends:
                table.add_row(
                    t["keyword"],
                    str(t["like_count"]),
                    str(t["velocity"]),
                    t["tweet_text"][:60] + "..." if len(t["tweet_text"]) > 60 else t["tweet_text"],
                )
            console.print(table)
        else:
            console.print("[yellow]No trending opportunities found this scan.[/yellow]")

        return top_trends

    def get_opportunity_windows(self) -> list[dict[str, Any]]:
        """Return trends from the last 4 hours that haven't been acted on."""
        trends = mem.get_trends_last_n_hours(hours=4)
        console.print(
            f"[blue]{len(trends)} unacted trend opportunity windows available.[/blue]"
        )
        return trends

    def suggest_reactive_content(self, trend: dict[str, Any]) -> str:
        """
        Draft a reactive tweet or thread idea for a given trend.

        Uses haiku for speed. Returns a content suggestion string.
        """
        keyword = trend.get("keyword", "AI")
        sample = trend.get("sample_tweet", "")
        like_count = trend.get("tweet_count", 0)

        prompt = f"""A tweet about "{keyword}" is going viral right now ({like_count} likes in <4 hours).

Sample viral tweet:
"{sample}"

Draft a reactive content idea for @app_supplyn — a founder building Supplyn.app, an AI-powered personalised supplement stack builder.

Voice: direct, evidence-based, slightly fed-up with industry nonsense, UK English, founder perspective.

Options:
1. A single tweet that adds a contrarian or complementary angle — tie it back to personalisation or the broken supplement industry
2. A thread opener that rides the trend but adds original Supplyn-relevant insight

RULES:
- Never just agree — add something new or challenge an assumption
- Specific and concrete — numbers and mechanisms over vague claims
- Under 280 chars for single tweet; just the hook line for thread option
- No bullet points, contractions always, never start with "I"
- UK English (personalise, optimise, fibre)
- Label your suggestion: [SINGLE TWEET] or [THREAD OPENER]

Write the content suggestion only. No preamble."""

        response = call_haiku(prompt)
        return response.strip() if response else f"Hot take on the {keyword} conversation going around right now."
