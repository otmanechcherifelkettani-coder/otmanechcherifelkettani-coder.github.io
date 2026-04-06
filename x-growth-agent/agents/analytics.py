from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tools import memory as mem
from tools.llm import call_haiku
from tools.x_api import XAPIClient

console = Console()

LEARNINGS_PATH = Path(__file__).parent.parent / "data" / "learnings.json"


def _load_learnings() -> dict[str, Any]:
    if LEARNINGS_PATH.exists():
        try:
            return json.loads(LEARNINGS_PATH.read_text())
        except Exception:
            pass
    return {
        "version": 1,
        "last_updated": None,
        "top_hook_styles": [],
        "top_content_types": [],
        "best_posting_hours": [8, 9, 12, 18, 19, 20],
        "worst_performing_topics": [],
        "avg_engagement_rate": 0.0,
        "style_weights": {
            "numbered_list": 1.0,
            "hot_take": 1.0,
            "story_format": 1.0,
            "question": 1.0,
            "counterintuitive": 1.0,
            "thread": 1.0,
        },
        "high_performing_patterns": [],
        "weekly_summaries": [],
    }


def _save_learnings(data: dict[str, Any]) -> None:
    LEARNINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEARNINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class AnalyticsAgent:
    """Analyzes tweet performance and updates learnings.json."""

    def __init__(self, x_api: XAPIClient) -> None:
        self.x_api = x_api

    def refresh_tweet_metrics(self) -> None:
        """
        Fetch metrics for all tweets posted in the last 7 days.
        Updates tweets table with impressions, likes, retweets, replies, bookmarks.
        Calculates engagement_rate.
        """
        console.print("[blue]Refreshing tweet metrics for last 7 days...[/blue]")
        tweets = mem.get_tweets_last_n_days(days=7)

        if not tweets:
            console.print("[yellow]No tweets found in last 7 days.[/yellow]")
            return

        updated = 0
        for tweet in tweets:
            tweet_id = tweet.get("tweet_id")
            if not tweet_id or tweet_id.startswith("dry_run"):
                continue

            metrics = self.x_api.get_tweet_metrics(tweet_id)
            if metrics:
                mem.update_tweet_metrics(
                    tweet_id=tweet_id,
                    impressions=metrics.get("impressions", 0),
                    likes=metrics.get("likes", 0),
                    retweets=metrics.get("retweets", 0),
                    replies=metrics.get("replies", 0),
                    bookmarks=metrics.get("bookmarks", 0),
                )
                updated += 1

        console.print(f"[green]Updated metrics for {updated}/{len(tweets)} tweets.[/green]")

    def get_engagement_stats(self) -> dict[str, Any]:
        """Return summary engagement statistics for the last 7 days."""
        tweets = mem.get_tweets_last_n_days(days=7)

        if not tweets:
            return {
                "total_tweets": 0,
                "avg_engagement_rate": 0.0,
                "total_likes": 0,
                "total_retweets": 0,
                "total_replies": 0,
                "total_impressions": 0,
                "best_tweet": None,
                "best_hour": None,
            }

        total_likes = sum(t.get("likes", 0) for t in tweets)
        total_rts = sum(t.get("retweets", 0) for t in tweets)
        total_replies = sum(t.get("replies", 0) for t in tweets)
        total_impressions = sum(t.get("impressions", 0) for t in tweets)
        engagement_rates = [t.get("engagement_rate", 0.0) for t in tweets]
        avg_er = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0.0

        best_tweet = max(tweets, key=lambda x: x.get("engagement_rate", 0.0), default=None)

        # Best posting hour
        hour_buckets: dict[int, list[float]] = defaultdict(list)
        for t in tweets:
            posted_at = t.get("posted_at", "")
            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at.replace(" ", "T"))
                    hour_buckets[dt.hour].append(t.get("engagement_rate", 0.0))
                except (ValueError, TypeError):
                    pass

        best_hour = None
        if hour_buckets:
            best_hour = max(
                hour_buckets.keys(),
                key=lambda h: sum(hour_buckets[h]) / len(hour_buckets[h]),
            )

        return {
            "total_tweets": len(tweets),
            "avg_engagement_rate": round(avg_er, 4),
            "total_likes": total_likes,
            "total_retweets": total_rts,
            "total_replies": total_replies,
            "total_impressions": total_impressions,
            "best_tweet": best_tweet,
            "best_hour": best_hour,
        }

    def generate_weekly_report(self) -> str:
        """
        Generate a markdown analytics report for the last 7 days.

        Includes:
        - Top 3 tweets by engagement
        - Average engagement rate
        - Best posting hours
        - Best content types
        - Reply suggestion stats
        - Trend usage stats
        """
        self.refresh_tweet_metrics()
        stats = self.get_engagement_stats()
        tweets = mem.get_tweets_last_n_days(days=7)
        reply_stats = mem.get_reply_stats()

        # Top 3 tweets
        sorted_tweets = sorted(tweets, key=lambda x: x.get("engagement_rate", 0.0), reverse=True)
        top_3 = sorted_tweets[:3]

        # Best content types
        type_performance: dict[str, list[float]] = defaultdict(list)
        for t in tweets:
            ct = t.get("content_type") or t.get("type") or "single"
            er = t.get("engagement_rate", 0.0)
            type_performance[ct].append(er)

        type_avgs = {
            ct: sum(ers) / len(ers)
            for ct, ers in type_performance.items()
            if ers
        }
        best_types = sorted(type_avgs.items(), key=lambda x: x[1], reverse=True)

        # Best posting hours
        hour_performance: dict[int, list[float]] = defaultdict(list)
        for t in tweets:
            posted_at = t.get("posted_at", "")
            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at.replace(" ", "T"))
                    hour_performance[dt.hour].append(t.get("engagement_rate", 0.0))
                except (ValueError, TypeError):
                    pass

        best_hours = sorted(
            [(h, sum(ers) / len(ers)) for h, ers in hour_performance.items() if ers],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines: list[str] = [
            f"# Weekly Analytics Report — {now}",
            "",
            "## Overview",
            f"- **Total tweets this week:** {stats['total_tweets']}",
            f"- **Avg engagement rate:** {stats['avg_engagement_rate']:.2%}",
            f"- **Total impressions:** {stats['total_impressions']:,}",
            f"- **Total likes:** {stats['total_likes']:,}",
            f"- **Total retweets:** {stats['total_retweets']:,}",
            f"- **Total replies:** {stats['total_replies']:,}",
            "",
            "> **Note:** Follower count change requires manual input "
            "(X API v2 free tier doesn't provide follower history).",
            "",
            "## Top 3 Tweets by Engagement Rate",
        ]

        for i, t in enumerate(top_3, 1):
            er = t.get("engagement_rate", 0.0)
            content = t.get("content", "")[:120]
            tweet_type = t.get("type", "single")
            likes = t.get("likes", 0)
            rts = t.get("retweets", 0)
            lines.append(
                f"\n### #{i} — {tweet_type.upper()} | ER: {er:.2%} | "
                f"{likes} likes, {rts} RTs"
            )
            lines.append(f'> "{content}..."')

        lines += [
            "",
            "## Best Content Types",
        ]
        for ct, avg_er in best_types:
            lines.append(f"- **{ct}**: avg ER {avg_er:.2%}")

        lines += [
            "",
            "## Best Posting Hours (UTC)",
        ]
        for hour, avg_er in best_hours:
            lines.append(f"- **{hour:02d}:00**: avg ER {avg_er:.2%}")

        lines += [
            "",
            "## Reply Suggestions",
            f"- **Posted:** {reply_stats.get('posted', 0)}",
            f"- **Skipped:** {reply_stats.get('skipped', 0)}",
            f"- **Still pending:** {reply_stats.get('pending', 0)}",
            "",
            "## Actions",
            "- Run `update-learnings` to update learnings.json with this week's patterns.",
            "- Review reply queue and act on high-value pending replies.",
        ]

        report = "\n".join(lines)
        console.print(Panel(report, title="Weekly Analytics Report", style="green"))
        return report

    def ab_test_report(self) -> str:
        """Compare performance by hook_style, content_type, and posting_hour."""
        tweets = mem.get_tweets_last_n_days(days=7)
        if not tweets:
            return "## A/B Test Report\n\nNo data available yet."

        hook_perf: dict[str, list[float]] = defaultdict(list)
        type_perf: dict[str, list[float]] = defaultdict(list)
        hour_perf: dict[str, list[float]] = defaultdict(list)

        for t in tweets:
            er = t.get("engagement_rate", 0.0)
            hs = t.get("hook_style") or "unknown"
            ct = t.get("content_type") or t.get("type") or "unknown"
            hook_perf[hs].append(er)
            type_perf[ct].append(er)

            posted_at = t.get("posted_at", "")
            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at.replace(" ", "T"))
                    bucket = f"{dt.hour:02d}:00"
                    hour_perf[bucket].append(er)
                except (ValueError, TypeError):
                    pass

        def _avg_table(data: dict[str, list[float]], title: str) -> list[str]:
            rows = sorted(
                [(k, sum(v) / len(v), len(v)) for k, v in data.items() if v],
                key=lambda x: x[1],
                reverse=True,
            )
            lines = [f"### {title}", "| Category | Avg ER | Tweet Count |", "|---|---|---|"]
            for cat, avg_er, cnt in rows:
                lines.append(f"| {cat} | {avg_er:.2%} | {cnt} |")
            return lines

        sections = ["## A/B Test Report", ""]
        sections += _avg_table(hook_perf, "By Hook Style")
        sections += [""]
        sections += _avg_table(type_perf, "By Content Type")
        sections += [""]
        sections += _avg_table(hour_perf, "By Posting Hour (UTC)")

        return "\n".join(sections)

    def update_learnings(self) -> None:
        """
        Analyze last 7 days of tweets and update learnings.json.

        Updates:
        - top_hook_styles
        - style_weights (boost performers)
        - best_posting_hours
        - high_performing_patterns
        - avg_engagement_rate
        - weekly_summaries (appended)
        """
        console.print("[blue]Updating learnings.json...[/blue]")
        tweets = mem.get_tweets_last_n_days(days=7)
        learnings = _load_learnings()

        if not tweets:
            console.print("[yellow]No tweet data to learn from yet.[/yellow]")
            return

        # --- Engagement rate ---
        ers = [t.get("engagement_rate", 0.0) for t in tweets]
        avg_er = sum(ers) / len(ers) if ers else 0.0
        learnings["avg_engagement_rate"] = round(avg_er, 4)

        # --- Top hook styles ---
        hook_perf: dict[str, list[float]] = defaultdict(list)
        for t in tweets:
            hs = t.get("hook_style") or "unknown"
            hook_perf[hs].append(t.get("engagement_rate", 0.0))

        top_hooks = sorted(
            [(k, sum(v) / len(v)) for k, v in hook_perf.items() if v],
            key=lambda x: x[1],
            reverse=True,
        )
        learnings["top_hook_styles"] = [k for k, _ in top_hooks[:5]]

        # --- Top content types ---
        type_perf: dict[str, list[float]] = defaultdict(list)
        for t in tweets:
            ct = t.get("content_type") or t.get("type") or "single"
            type_perf[ct].append(t.get("engagement_rate", 0.0))

        top_types = sorted(
            [(k, sum(v) / len(v)) for k, v in type_perf.items() if v],
            key=lambda x: x[1],
            reverse=True,
        )
        learnings["top_content_types"] = [k for k, _ in top_types[:5]]

        # --- Best posting hours ---
        hour_perf: dict[int, list[float]] = defaultdict(list)
        for t in tweets:
            posted_at = t.get("posted_at", "")
            if posted_at:
                try:
                    dt = datetime.fromisoformat(posted_at.replace(" ", "T"))
                    hour_perf[dt.hour].append(t.get("engagement_rate", 0.0))
                except (ValueError, TypeError):
                    pass

        if hour_perf:
            best_hours = sorted(
                hour_perf.keys(),
                key=lambda h: sum(hour_perf[h]) / len(hour_perf[h]),
                reverse=True,
            )[:6]
            learnings["best_posting_hours"] = sorted(best_hours)

        # --- Style weights (normalize + boost performers) ---
        existing_weights: dict[str, float] = learnings.get("style_weights", {})
        if top_hooks:
            max_er = max(er for _, er in top_hooks) if top_hooks else 1.0
            for style, er in top_hooks:
                if style in existing_weights:
                    boost = 1.0 + (er / max(max_er, 0.001)) * 0.5
                    existing_weights[style] = round(
                        min(2.0, existing_weights[style] * 0.7 + boost * 0.3), 3
                    )
        learnings["style_weights"] = existing_weights

        # --- High performing patterns (hook text snippets from top tweets) ---
        top_performers = sorted(tweets, key=lambda x: x.get("engagement_rate", 0.0), reverse=True)[:10]
        patterns: list[str] = []
        for t in top_performers:
            content = t.get("content", "")
            # Extract first line as hook pattern
            first_line = content.strip().split("\n")[0][:100]
            if first_line and first_line not in patterns:
                patterns.append(first_line)

        learnings["high_performing_patterns"] = (
            patterns + learnings.get("high_performing_patterns", [])
        )[:20]  # Keep last 20

        # --- Worst performing topics ---
        topic_perf: dict[str, list[float]] = defaultdict(list)
        for t in tweets:
            topic = t.get("topic") or "unknown"
            topic_perf[topic].append(t.get("engagement_rate", 0.0))

        worst_topics = sorted(
            [(k, sum(v) / len(v)) for k, v in topic_perf.items() if v],
            key=lambda x: x[1],
        )[:5]
        learnings["worst_performing_topics"] = [k for k, _ in worst_topics]

        # --- LLM-generated weekly summary ---
        summary_prompt = f"""Summarize this week's Twitter content performance for @app_supplyn — a founder building Supplyn.app, an AI-powered personalised supplement stack builder.

Key stats:
- Tweets posted: {len(tweets)}
- Avg engagement rate: {avg_er:.2%}
- Top hook styles: {learnings['top_hook_styles'][:3]}
- Best posting hours: {learnings['best_posting_hours'][:3]}

Write 2-3 sentences summarizing what worked, what didn't, and one specific recommendation for next week.
Be concrete and actionable. No fluff."""

        try:
            summary_text = call_haiku(summary_prompt)
        except Exception:
            summary_text = f"Week of {datetime.now(timezone.utc).strftime('%Y-%m-%d')}: {len(tweets)} tweets, avg ER {avg_er:.2%}."

        # --- Append weekly summary ---
        weekly_entry = {
            "week_ending": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "tweet_count": len(tweets),
            "avg_engagement_rate": round(avg_er, 4),
            "top_hooks": learnings["top_hook_styles"][:3],
            "best_hours": learnings["best_posting_hours"][:3],
            "summary": summary_text,
        }
        summaries = learnings.get("weekly_summaries", [])
        summaries.append(weekly_entry)
        learnings["weekly_summaries"] = summaries[-12:]  # Keep last 12 weeks

        learnings["last_updated"] = datetime.now(timezone.utc).isoformat()

        _save_learnings(learnings)
        console.print(
            Panel(
                f"learnings.json updated.\n"
                f"Avg ER: {avg_er:.2%} | Top hooks: {learnings['top_hook_styles'][:3]} | "
                f"Best hours: {learnings['best_posting_hours'][:3]}",
                title="Learnings Updated",
                style="green",
            )
        )
