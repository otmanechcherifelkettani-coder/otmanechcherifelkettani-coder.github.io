from __future__ import annotations

import os
from typing import Any

import requests
from rich.console import Console

console = Console()

TWEET_URL = "https://x.com/{username}/status/{tweet_id}"
PROFILE_URL = "https://x.com/{username}"


def _token() -> str | None:
    return os.getenv("TELEGRAM_BOT_TOKEN")


def _chat_id() -> str | None:
    return os.getenv("TELEGRAM_CHAT_ID")


def is_configured() -> bool:
    return bool(_token() and _chat_id())


def esc(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send(text: str) -> bool:
    """Send an HTML-formatted message. Chunks at 4000 chars if needed."""
    token = _token()
    chat_id = _chat_id()
    if not token or not chat_id:
        console.print("[dim]Telegram not configured — skipping notification.[/dim]")
        return False

    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    success = True
    for chunk in chunks:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if not resp.ok:
                console.print(f"[yellow]Telegram send failed: {resp.text[:200]}[/yellow]")
                success = False
        except Exception as e:
            console.print(f"[yellow]Telegram error: {e}[/yellow]")
            success = False
    return success


def send_morning_brief(
    date_str: str,
    post_schedule: str,
    reply_count: int,
    follow_count: int,
    trend_count: int,
) -> bool:
    msg = (
        f"🌅 <b>Morning Brief — {esc(date_str)}</b>\n\n"
        f"Here's what's ready for today:\n\n"
        f"📅 {esc(post_schedule)}\n"
        f"💬 Reply opportunities: <b>{reply_count}</b> new\n"
        f"👥 Follow suggestions: <b>{follow_count}</b> new\n"
        f"🔥 Trends spotted: <b>{trend_count}</b>\n\n"
        f"All content + links follow in the messages below 👇"
    )
    return send(msg)


def send_thread(topic: str, reason: str, tweets: list[str], post_time: str = "") -> bool:
    div = "━━━━━━━━━━━━━━━━━━━━"
    time_str = f" — post at <b>{esc(post_time)}</b>" if post_time else ""

    lines = [
        f"🧵 <b>THREAD RECOMMENDATION</b>{time_str}",
        f"",
        f"<b>Topic:</b> {esc(topic)}",
        f"<b>Why:</b> {esc(reason)}",
        f"",
        div,
    ]

    total = len(tweets)
    for i, tweet in enumerate(tweets, 1):
        if i == 1:
            label = f"TWEET 1/{total} — HOOK"
        elif i == total:
            label = f"TWEET {i}/{total} — CTA"
        else:
            label = f"TWEET {i}/{total}"
        lines.append(f"<b>{label}</b>")
        lines.append(f"<code>{esc(tweet)}</code>")
        lines.append("─ ─ ─ ─ ─ ─ ─ ─ ─ ─")

    lines.append(f"\n📌 Post as a thread on X — paste each tweet, reply to the previous one")
    return send("\n".join(lines))


def send_single_tweet(
    tweet_type: str,
    content: str,
    score: int,
    post_time: str = "",
) -> bool:
    type_labels = {
        "hot_take": "🔥 HOT TAKE",
        "question": "❓ QUESTION",
        "observation": "💡 OBSERVATION",
        "conversion": "🎯 CONVERSION TWEET",
        "meme": "😄 MEME",
        "auto": "📝 TWEET",
    }
    label = type_labels.get(tweet_type, "📝 TWEET")
    time_str = f" — post at <b>{esc(post_time)}</b>" if post_time else ""

    msg = (
        f"📝 <b>{label}</b>{time_str}\n"
        f"Score: {score}/100\n\n"
        f"<code>{esc(content)}</code>\n\n"
        f"📌 Copy → paste on X"
    )
    return send(msg)


def send_reply_opportunities(opportunities: list[dict[str, Any]]) -> bool:
    if not opportunities:
        return True

    lines = [f"💬 <b>REPLY OPPORTUNITIES — {len(opportunities)} new</b>\n"]

    for opp in opportunities:
        account = opp.get("account", "")
        tweet_id = opp.get("tweet_id", "")
        tweet_text = opp.get("tweet_text", "")
        reply = opp.get("suggested_reply", "")
        strategy = opp.get("strategy", "")
        like_count = opp.get("like_count", 0)

        link = TWEET_URL.format(username=account, tweet_id=tweet_id)

        lines.append(f"<b>@{esc(account)}</b> · {like_count:,} likes · [{esc(strategy)}]")
        lines.append(f'🔗 <a href="{link}">Open tweet →</a>')
        lines.append(f"<i>Their tweet: {esc(tweet_text[:140])}...</i>")
        lines.append(f"\n<b>Your reply:</b>")
        lines.append(f"<code>{esc(reply)}</code>")
        lines.append("━━━━━━━━━━━━━━━━━━━━\n")

    lines.append("📌 Tap link → open tweet → paste reply → post")
    return send("\n".join(lines))


def send_engagement_suggestions(suggestions: list[dict[str, Any]]) -> bool:
    if not suggestions:
        return True

    lines = [f"⚡ <b>ENGAGEMENT SUGGESTIONS — {len(suggestions)} new</b>\n"]

    for s in suggestions:
        account = s.get("account", "")
        tweet_id = s.get("tweet_id", "")
        content = s.get("content", "")
        stype = s.get("suggestion_type", "like")
        like_count = s.get("like_count", 0)

        link = TWEET_URL.format(username=account, tweet_id=tweet_id)
        action = "❤️ <b>LIKE</b>" if stype == "like" else "🔁 <b>QUOTE TWEET</b>"

        lines.append(f"{action} — @{esc(account)} · {like_count:,} likes")
        lines.append(f'🔗 <a href="{link}">Open tweet →</a>')

        if stype == "quote":
            # Extract quote content (stored as "[QUOTE]: ...\n\n[ORIGINAL]: ...")
            raw = content
            if "[QUOTE]:" in raw:
                quote_part = raw.split("[QUOTE]:")[1].split("[ORIGINAL]:")[0].strip()
                original_part = raw.split("[ORIGINAL]:")[1].strip() if "[ORIGINAL]:" in raw else ""
                lines.append(f"<i>Original: {esc(original_part[:100])}...</i>")
                lines.append(f"\n<b>Your quote tweet:</b>")
                lines.append(f"<code>{esc(quote_part)}</code>")
            else:
                lines.append(f"<i>{esc(content[:120])}...</i>")
        else:
            lines.append(f"<i>{esc(content[:120])}...</i>")

        lines.append("━━━━━━━━━━━━━━━━━━━━\n")

    lines.append("📌 Tap link → like or quote tweet on X")
    return send("\n".join(lines))


def send_follow_suggestions(candidates: list[dict[str, Any]]) -> bool:
    if not candidates:
        return True

    # Batch into groups of 10 to keep messages readable
    batch_size = 10
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        total = len(candidates)
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        header = f"👥 <b>FOLLOW SUGGESTIONS"
        if total_batches > 1:
            header += f" ({batch_num}/{total_batches})"
        header += f" — {total} accounts total</b>\n"

        lines = [header]
        for c in batch:
            username = c.get("username", "")
            follower_count = c.get("follower_count", 0)
            reason = c.get("reason", "")
            profile_link = PROFILE_URL.format(username=username)

            lines.append(f'<a href="{profile_link}">@{esc(username)}</a> — {follower_count:,} followers')
            lines.append(f"💡 {esc(reason)}\n")

        lines.append("📌 Tap each link → follow on X")
        send("\n".join(lines))

    return True


def send_trend_alert(
    keyword: str,
    velocity: float,
    sample_tweet: str,
    reactive_idea: str,
) -> bool:
    msg = (
        f"🔥 <b>TREND ALERT</b>\n\n"
        f"<b>Keyword:</b> {esc(keyword)}\n"
        f"<b>Velocity:</b> {velocity:.0f} likes/hr\n\n"
        f"<b>Sample viral tweet:</b>\n"
        f"<i>{esc(sample_tweet[:200])}</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Reactive content idea:</b>\n"
        f"<code>{esc(reactive_idea)}</code>\n\n"
        f"📌 Post now to ride the trend"
    )
    return send(msg)
