from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

from tools.llm import call_sonnet, generate_variants
from tools.scorer import pick_best_variant
from tools import memory as mem

console = Console()

LEARNINGS_PATH = Path(__file__).parent.parent / "data" / "learnings.json"
PERSONA_PATH = Path(__file__).parent.parent / "persona.md"
PEAK_HOURS = [8, 9, 12, 18, 19, 20]

# hot_take and observation go viral → builds audience
# conversion drives supplyn.app clicks → makes money
# meme removed from auto-rotation (too risky for low-follower stage)
TWEET_TYPE_WEIGHTS = [
    ("hot_take", 0.35),
    ("observation", 0.30),
    ("question", 0.20),
    ("conversion", 0.15),
]
TWEET_TYPES = [t for t, _ in TWEET_TYPE_WEIGHTS]

NICHE = "personalised supplements, health tech, AI-powered wellness, evidence-based nutrition"


def _load_persona_examples() -> str:
    """Load the 20 example tweets from persona.md to inject into prompts."""
    if not PERSONA_PATH.exists():
        return ""
    try:
        content = PERSONA_PATH.read_text()
        start = content.find("## 20 Example Tweets in Voice")
        end = content.find("## VIP Accounts to Monitor")
        if start != -1 and end != -1:
            return content[start:end].strip()
        return ""
    except Exception:
        return ""


def _weighted_tweet_type() -> str:
    """Pick a tweet type using defined weights."""
    types = [t for t, _ in TWEET_TYPE_WEIGHTS]
    weights = [w for _, w in TWEET_TYPE_WEIGHTS]
    return random.choices(types, weights=weights, k=1)[0]


def _load_learnings() -> dict[str, Any]:
    if LEARNINGS_PATH.exists():
        try:
            return json.loads(LEARNINGS_PATH.read_text())
        except Exception:
            pass
    return {}


class ContentCreatorAgent:
    """Generates and posts content (threads and single tweets)."""

    def __init__(
        self,
        dry_run: bool = False,
    ) -> None:
        self.dry_run = dry_run

    def generate_thread(self, topic: str | None = None) -> list[str]:
        """
        Generate a 10-tweet thread.

        Follows formula:
          Tweet 1: HOOK
          Tweet 2: SETUP
          Tweets 3-8: MEAT (one insight each)
          Tweet 9: SUMMARY
          Tweet 10: CTA

        Generates 3 hook variants, picks best.
        Checks recent_topics for 14-day dedup.
        """
        learnings = _load_learnings()
        recent_topics = mem.get_recent_topics(days=14)

        # Select or confirm topic
        if not topic:
            topic = self._pick_topic(recent_topics, learnings)

        # Check dedup
        if topic.lower() in [t.lower() for t in recent_topics]:
            console.print(
                f"[yellow]Topic '{topic}' posted recently. Picking alternate...[/yellow]"
            )
            topic = self._pick_topic(recent_topics, learnings, force_new=True)

        console.print(f"[blue]Generating thread on: {topic}[/blue]")

        examples = _load_persona_examples()

        # Generate 3 hook variants, pick best
        hook_prompt = f"""You are the founder of Supplyn.app writing a Twitter thread.

Write a killer opening tweet for a thread about: {topic}

{examples}

Draw inspiration from the examples above — match that voice exactly.

RULES:
- Stop-the-scroll opener: bold claim, surprising stat, or sharp industry exposé
- Under 280 characters
- No bullet points, max 1 emoji
- Never start with "I"
- Short punchy sentences (avg 6-8 words)
- End with a colon or ellipsis to signal thread follows
- UK English (personalise, optimise, fibre)
- Name the enemy: the supplement industry, influencer stacks, generic advice, bro-science
- Numbers beat vague claims: "£47/month" not "a lot of money"

Write ONLY the tweet text. Nothing else."""

        hook_variants = generate_variants(hook_prompt, n=3, use_sonnet=True)
        if not hook_variants:
            hook_variants = [f"Most people thinking about {topic} have it completely backwards.\n\nHere's what they're missing: 🧵"]

        best_hook, hook_scores = pick_best_variant(hook_variants, content_type="thread_hook")
        console.print(f"[green]Hook selected (score: {hook_scores['total']}/100)[/green]")

        # Generate full thread body
        thread_prompt = f"""You are the founder of Supplyn.app writing a Twitter thread.

Topic: {topic}

HOOK (Tweet 1) — use it EXACTLY as written:
---
{best_hook}
---

Write tweets 2-10:

Tweet 2 — SETUP: Why this matters RIGHT NOW for the reader. Make it personal and urgent. 1-3 sentences.

Tweets 3-8 — MEAT: One concrete, specific, evidence-backed insight per tweet. Short. Punchy. Each tweet must stand alone and be worth screenshotting. Use numbers, mechanisms, and named examples (AG1, Huberman, influencer stacks). No vague claims.

Tweet 9 — SUMMARY: "If you remember one thing from this thread:" — the single sharpest insight distilled. 1-2 sentences.

Tweet 10 — CTA (CRITICAL — this must drive supplyn.app visits):
Write something like one of these (use as templates, not copy-paste):
• "Stop guessing what you need. supplyn.app takes 60 seconds — quiz, personalised stack, no upsell. Free to try."
• "Built supplyn.app to solve exactly this problem. 60-second quiz → personalised stack → know what you actually need."
• "If you've been guessing: supplyn.app tells you what's actually missing from your stack. 60 seconds. Free."
Must include supplyn.app. Must feel like a real founder, not an ad. Direct and confident.

VOICE RULES (non-negotiable):
- No bullet points ever — line breaks only
- Short sentences (6-8 words average)
- Contractions always (don't, won't, it's, we've)
- Never start any tweet with "I"
- Max 1 emoji per tweet (0 is usually better)
- Under 280 characters per tweet
- UK English: personalise, optimise, fibre
- Name the enemy: influencer stacks, generic supplements, bro-science, the supplement industry
- Numbers over vague claims always

OUTPUT FORMAT: Each tweet separated by "---" on its own line.
Return ONLY the tweet texts. No labels, no numbering."""

        thread_response = call_sonnet(thread_prompt)

        # Parse tweets from response
        tweets = self._parse_thread_response(thread_response, best_hook)

        if not tweets:
            console.print("[red]Failed to generate thread. Using fallback.[/red]")
            tweets = self._fallback_thread(topic, best_hook)

        # Ensure exactly 10 tweets
        if len(tweets) < 10:
            while len(tweets) < 10:
                tweets.append("If you want to know what you actually need: supplyn.app builds your personalised stack in 60 seconds. Follow @app_supplyn for more evidence-based takes.")
        tweets = tweets[:10]

        # Record topic
        mem.insert_recent_topic(topic)

        console.print(
            Panel(
                f"Thread generated: {len(tweets)} tweets\nTopic: {topic}\nHook score: {hook_scores['total']}/100",
                title="Thread Ready",
                style="green",
            )
        )
        return tweets

    def _parse_thread_response(self, response: str, hook: str) -> list[str]:
        """Parse thread response into list of tweet texts."""
        tweets: list[str] = []

        # Split by separator
        parts = [p.strip() for p in response.split("---") if p.strip()]

        if parts:
            # First part is tweets 2-10; prepend hook as tweet 1
            if not parts[0].lower().startswith(hook[:30].lower()):
                tweets.append(hook)
            for part in parts:
                cleaned = part.strip()
                if cleaned and len(cleaned) > 5:
                    tweets.append(cleaned)
        else:
            # Try line-by-line fallback
            lines = [l.strip() for l in response.split("\n") if l.strip()]
            tweets = [hook] + lines[:9]

        return tweets

    def _fallback_thread(self, topic: str, hook: str) -> list[str]:
        """Minimal fallback thread if generation fails."""
        return [
            hook,
            f"Here's why {topic} matters more right now than most people realize.",
            "The conventional wisdom is outdated. The real picture is more interesting.",
            "First: the problem everyone sees but nobody talks about directly.",
            "Second: why the obvious solution doesn't actually work at scale.",
            "Third: what evidence-based practitioners do differently.",
            "Fourth: the counterintuitive part the supplement industry doesn't want you to know.",
            "Fifth: how to audit your own stack starting today.",
            "If you remember one thing from this thread: the supplement industry profits from confusion. Personalisation is the fix.",
            "Follow @app_supplyn for more evidence-based takes on supplements. And if you want to know what you actually need: supplyn.app",
        ]

    def _pick_topic(
        self,
        recent_topics: list[str],
        learnings: dict[str, Any],
        force_new: bool = False,  # noqa: ARG002 — reserved for future stricter dedup
    ) -> str:
        """Pick a topic avoiding recently used ones."""
        topic_pool = [
            # Education → builds followers, earns trust
            "The supplement industry makes more money when you're confused — here's the business model",
            "5 supplements most people take that they probably don't need (and what to take instead)",
            "73% of UK adults are vitamin D deficient in winter. It costs £8/month to fix. Why aren't people fixing it?",
            "Magnesium is not one thing: glycinate vs. malate vs. oxide vs. l-threonate — what each actually does",
            "Why influencer supplement stacks are a business model, not a health plan",
            "AG1 is £79/month. Here's what the research actually says about it.",
            "The gut health supplement market is mostly marketing — here's what actually has RCT backing",
            "Why supplement timing matters more than brand: the science behind when to take what",
            "Creatine is the most evidence-backed supplement most people dismiss — here's why",
            "The omega-3 dosing mistake 90% of people make (and the difference it makes)",
            "Generic multivitamins: almost always a waste of money. Here's why.",
            "The cognitive performance supplements that actually have RCT backing (and the ones that don't)",
            "Vitamin D without K2 is a half-measure — and most supplements don't include both",
            "The collagen supplement industry is worth billions. Here's what your gut actually does with it.",
            "How supplement brands use proprietary blends to hide underdosed ingredients",
            "BCAA supplements: who actually needs them and who's wasting £30/month",
            "The sleep supplement stack that actually has evidence behind it (it's not what influencers sell)",
            "How to read a supplement label and spot the 5 signs it's not worth buying",
            # Conversion → drives supplyn.app signups directly
            "Why personalised supplementation beats any generic stack — and how we built Supplyn to do it",
            "What 500 personalised supplement stacks taught us about what most people are missing",
            "The 60-second quiz that tells you what your supplement stack is actually missing",
            "Last year I spent £600 on supplements and had no idea if they were working — so we built Supplyn",
            "Why we made supplyn.app free to try — and what we found when people actually used it",
            "How AI changed personalised nutrition: what we built at Supplyn and why it works",
            "The problem with every supplement app before Supplyn — and what we did differently",
            "What blood work tells you about your supplement needs — and how Supplyn uses that logic",
        ]

        # Filter out recent topics
        recent_lower = [t.lower() for t in recent_topics]
        available = [t for t in topic_pool if t.lower() not in recent_lower]

        if not available:
            available = topic_pool  # Reset if all used

        # Check learnings for worst-performing topics to avoid
        worst = learnings.get("worst_performing_topics", [])
        if worst:
            available = [t for t in available if t not in worst] or available

        return random.choice(available)

    def generate_single_tweet(self, tweet_type: str = "auto") -> str:
        """
        Generate a single tweet.

        tweet_type: hot_take | question | observation | meme | auto
        Generates 3 variants, picks best.
        3% chance to inject minor typo in casual tweets.
        """
        if tweet_type == "auto":
            # Avoid repeating the same type as the last posted tweet
            last_type = mem.get_agent_state("last_tweet_type")
            tweet_type = _weighted_tweet_type()
            if tweet_type == last_type:
                tweet_type = _weighted_tweet_type()  # one re-roll

        console.print(f"[blue]Generating {tweet_type} tweet...[/blue]")

        examples = _load_persona_examples()

        # Load recent posts to avoid repetition
        recent_tweets = mem.get_tweets_last_n_days(days=7)
        recent_content = "\n---\n".join(
            t["content"][:200] for t in recent_tweets[:5] if t.get("content")
        )
        recent_block = (
            f"\n\nRECENT POSTS TO AVOID REPEATING (different angle, different structure, different opening):\n{recent_content}\n"
            if recent_content else ""
        )

        type_instructions = {
            "hot_take": (
                "Write a hot take / controversial opinion tweet about the supplement industry, "
                "personalised nutrition, or health tech. "
                "Must be genuinely provocative, specific, evidence-backed, and defensible. "
                "Name the enemy directly: influencer stacks, AG1, generic multivitamins, bro-science. "
                "Should make people want to argue or share. "
                "End with a sharp provocation or question."
            ),
            "question": (
                "Write a thought-provoking question that reveals a hidden assumption most people have about supplements or nutrition. "
                "The question should make people reflect on their own behaviour. "
                "Make them want to answer from personal experience. "
                "End with the question itself — nothing after it."
            ),
            "observation": (
                "Write a sharp, specific insight about supplements, personalised nutrition, or building Supplyn.app. "
                "Use a real mechanism, a surprising number, or a named industry example. "
                "Something people in the health world will screenshot and share. "
                "Tie it back to personalisation or supplyn.app if natural. "
                "End with 'That's why we built Supplyn.' or 'Check your stack.' or a question."
            ),
            "meme": (
                "Write a self-aware, slightly ironic tweet about the supplement or biohacking world. "
                "Inside joke energy — the absurdity of influencer stacks, bro-science, or the founder grind. "
                "Light dry wit. Not try-hard. Should make health-conscious people laugh and tag a friend."
            ),
            "conversion": (
                "Write a direct tweet that drives people to supplyn.app. "
                "Start from a real, relatable problem (wasted money, guesswork, no results, supplement confusion). "
                "Build to Supplyn as the natural solution. "
                "Must mention supplyn.app. Must feel like a real founder — not an ad. "
                "Specific benefit: 60-second quiz, personalised stack, free to try, evidence-based. "
                "Urgency without desperation. End with a clear next action."
            ),
        }

        instruction = type_instructions.get(tweet_type, type_instructions["observation"])

        prompt = f"""You are the founder of Supplyn.app — an AI-powered personalised supplement stack builder.

{instruction}

{examples}

Match the voice from the examples above exactly. That's what good looks like.
{recent_block}
HARD RULES:
- Under 280 characters total
- No bullet points — line breaks only
- Max 1 emoji (0 is usually better)
- Never start with "I"
- Contractions always (don't, it's, we've)
- Short punchy sentences (6-8 words avg)
- UK English: personalise, optimise, fibre
- Numbers beat vague claims: "£47/month" not "a lot of money"
- Never generic wellness content — always specific, named, concrete
- Avoid: "amazing", "incredible", "game-changing", "unlock your potential"
- NEVER use the same opening word, structure, or angle as the recent posts above

Write ONLY the tweet text. Nothing else."""

        variants = generate_variants(prompt, n=5, use_sonnet=True)
        if not variants:
            variants = [self._fallback_single_tweet(tweet_type)]

        best, scores = pick_best_variant(variants, content_type=tweet_type)

        # Ensure ending hook
        best = self._ensure_ending_hook(best, tweet_type)
        mem.set_agent_state("last_tweet_type", tweet_type)

        # 3% chance of minor typo in casual tweets (not hot_takes or observations)
        if tweet_type in ("meme", "question") and random.random() < 0.03:
            best = self._inject_typo(best)

        console.print(
            f"[green]Tweet generated (score: {scores['total']}/100, type: {tweet_type})[/green]"
        )
        return best

    def _ensure_ending_hook(self, tweet: str, tweet_type: str = "single") -> str:  # noqa: ARG002
        """Add question or opinion hook if not already present and tweet stays under 280 chars."""
        tweet = tweet.strip()
        if tweet.endswith("?"):
            return tweet
        if tweet.endswith((".", "!", "…", "...")):
            # Check if last sentence is already opinionated/hook-like
            last_sentence = tweet.split("\n")[-1].strip()
            if any(
                kw in last_sentence.lower()
                for kw in ["what do you", "agree?", "disagree?", "change my mind", "your take", "thoughts?", "am i wrong", "anyone else"]
            ):
                return tweet
        # Add hook only if result stays under 280 chars
        hooks = [
            "\n\nWhat's your take?",
            "\n\nAnyone else seeing this?",
            "\n\nChange my mind.",
            "\n\nAm I wrong here?",
        ]
        random.shuffle(hooks)
        for hook in hooks:
            if len(tweet + hook) <= 280:
                return tweet + hook
        return tweet

    def _inject_typo(self, text: str) -> str:
        """Inject a single minor, realistic typo."""
        typos = {
            "the": "teh",
            "and": "adn",
            "that": "taht",
            "with": "wiht",
            "this": "htis",
            "have": "ahve",
        }
        words = text.split()
        for i, word in enumerate(words):
            clean = word.lower().strip(".,!?")
            if clean in typos and random.random() < 0.3:
                words[i] = word.replace(clean, typos[clean], 1)
                break
        return " ".join(words)

    def _fallback_single_tweet(self, tweet_type: str) -> str:
        fallbacks = {
            "hot_take": "Most supplement brands don't want you to know what's actually in your stack.\n\nNot because they're evil.\n\nBecause confusion sells more products than clarity.\n\nPersonalisation fixes this. That's why we built Supplyn.",
            "question": "Do you actually know why you're taking each supplement in your stack?\n\nNot 'I heard it's good for you.'\n\nThe mechanism. The dose. The timing.\n\nMost people don't. And the industry depends on it.",
            "observation": "The UK supplement market is worth £500m a year.\n\nMost of it is wasted on products people don't need, at doses that don't work, taken at the wrong time.\n\nPersonalisation isn't a feature. It's the entire missing piece.",
            "meme": "Me before Supplyn: buys 8 supplements, takes them all at 9am with coffee, wonders why nothing works\n\nMe after: 3 things, timed properly, actually feel different\n\nAnyone else been here?",
            "conversion": "Spent £400 on supplements last year.\n\nDidn't know if any of them were working.\n\nBuilt supplyn.app to fix that.\n\n60-second quiz. Personalised stack. Free to try.\n\nIf you're guessing — you don't have to be.",
        }
        return fallbacks.get(tweet_type, fallbacks["observation"])

    def generate_quote_tweet(self, original_tweet: str, author: str) -> str:
        """Generate opinionated quote-tweet content."""
        prompt = f"""Write a strong, opinionated quote-tweet response to this tweet by @{author}:

ORIGINAL TWEET:
---
{original_tweet}
---

RULES:
- Add genuine insight, not just agreement
- Under 200 characters ideal (leaves room for the quoted tweet)
- Direct opinion or extension of the idea
- Never sycophantic ("great point!" is banned)
- Can disagree, agree with nuance, or add a dimension they missed
- No bullet points, contractions always, never start with "I"

Write ONLY the quote-tweet text. Nothing else."""

        response = call_sonnet(prompt)
        return response.strip() if response else f"This cuts to something important about {author}'s broader argument."

    def post_thread(self, topic: str | None = None) -> bool:
        """Generate and post (or dry-run) a thread."""
        if self._should_skip():
            console.print("[yellow]Skipping this post (random human skip).[/yellow]")
            return False

        if not self._check_peak_hours():
            console.print("[yellow]Not in peak hours. Posting anyway (manual trigger).[/yellow]")

        self._random_jitter()

        tweets = self.generate_thread(topic)
        if not tweets:
            return False

        if self.dry_run:
            console.print(Panel("\n\n---\n\n".join(tweets), title="[DRY RUN] Thread Preview", style="cyan"))
            for tweet in tweets:
                mem.insert_tweet(
                    content=tweet,
                    tweet_type="thread",
                    topic=topic or "auto",
                    hook_style="thread",
                )
            return True

        from tools import telegram
        telegram_mode = os.getenv("TELEGRAM_MODE", "false").lower() == "true"

        if telegram_mode and telegram.is_configured():
            reason = "High-value educational content — builds trust and followers"
            telegram.send_thread(
                topic=topic or "auto",
                reason=reason,
                tweets=tweets,
            )
            for tweet in tweets:
                mem.insert_tweet(
                    content=tweet,
                    tweet_type="thread",
                    topic=topic or "auto",
                    hook_style="thread",
                )
            console.print("[green]Thread sent to Telegram.[/green]")
            return True

        from tools.x_api import XAPIClient
        x = XAPIClient(dry_run=self.dry_run)
        results = x.post_thread(tweets)
        if results:
            for tweet, result in zip(tweets, results):
                tweet_id = result.get("id") if result else None
                mem.insert_tweet(
                    content=tweet,
                    tweet_id=tweet_id,
                    tweet_type="thread",
                    topic=topic or "auto",
                    hook_style="thread",
                )
            console.print(f"[green]Thread posted: {len(results)} tweets[/green]")
            return True
        return False

    def post_single_tweet(self, tweet_type: str = "auto") -> bool:
        """Generate and post (or dry-run) a single tweet."""
        if self._should_skip():
            console.print("[yellow]Skipping this post (random human skip).[/yellow]")
            return False

        self._random_jitter()

        tweet = self.generate_single_tweet(tweet_type)
        if not tweet:
            return False

        if self.dry_run:
            console.print(Panel(tweet, title=f"[DRY RUN] Single Tweet ({tweet_type})", style="cyan"))
            mem.insert_tweet(
                content=tweet,
                tweet_type="single",
                content_type=tweet_type,
                hook_style=tweet_type,
            )
            return True

        from tools import telegram
        telegram_mode = os.getenv("TELEGRAM_MODE", "false").lower() == "true"

        if telegram_mode and telegram.is_configured():
            telegram.send_single_tweet(
                tweet_type=tweet_type,
                content=tweet,
                score=0,
            )
            mem.insert_tweet(
                content=tweet,
                tweet_type="single",
                content_type=tweet_type,
                hook_style=tweet_type,
            )
            console.print(f"[green]Tweet sent to Telegram ({tweet_type}).[/green]")
            return True

        from tools.x_api import XAPIClient
        x = XAPIClient(dry_run=self.dry_run)
        result = x.post_tweet(tweet)
        if result:
            tweet_id = result.get("id")
            mem.insert_tweet(
                content=tweet,
                tweet_id=tweet_id,
                tweet_type="single",
                content_type=tweet_type,
                hook_style=tweet_type,
            )
            console.print(f"[green]Tweet posted: {tweet_id}[/green]")
            return True
        return False

    def _check_peak_hours(self) -> bool:
        """Return True if current UTC hour is in peak posting hours."""
        current_hour = datetime.now(timezone.utc).hour
        return current_hour in PEAK_HOURS

    def _random_jitter(self) -> None:
        """Sleep random 90-300 seconds to avoid robotic timing."""
        if self.dry_run:
            return
        delay = random.uniform(90, 300)
        console.print(f"[dim]Jitter delay: {delay:.0f}s...[/dim]")
        time.sleep(delay)

    def _should_skip(self) -> bool:
        """Return True 10% of the time (random human skip behavior)."""
        return random.random() < 0.10
