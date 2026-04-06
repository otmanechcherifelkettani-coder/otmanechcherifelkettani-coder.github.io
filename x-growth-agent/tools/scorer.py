from __future__ import annotations

import json
import re
from typing import Any

from rich.console import Console

from tools.llm import call_haiku

console = Console()


def score_content(text: str, content_type: str = "single") -> dict[str, Any]:
    """
    Score content on hook strength, shareability, and niche relevance.

    Returns dict with keys:
        hook_strength (0-100), shareability (0-100), niche_relevance (0-100),
        total (0-100 weighted), reasoning (str)
    """
    prompt = f"""You are a ruthless Twitter content quality judge for the health tech / personalised supplements niche (@app_supplyn — Supplyn.app).

Score this {content_type} tweet/thread content on three dimensions (0-100 each):

1. HOOK STRENGTH (weight: 40%) — Does the opening grab attention immediately? Is it bold, specific, surprising, or emotionally resonant? Would a busy person stop scrolling?

2. SHAREABILITY (weight: 30%) — Would people RT or quote-tweet this? Does it make the reader look smart or interesting if they share it? Is it genuinely useful or insightful?

3. NICHE RELEVANCE (weight: 30%) — Is this on-topic for personalised supplements, evidence-based nutrition, health tech, biohacking, or building Supplyn.app (AI wellness)? Is it written for health-conscious people, not outsiders?

CONTENT TO SCORE:
---
{text}
---

Respond in valid JSON ONLY. No prose before or after. Format:
{{
  "hook_strength": <0-100>,
  "shareability": <0-100>,
  "niche_relevance": <0-100>,
  "reasoning": "<1-2 sentence explanation of main strengths and weaknesses>"
}}"""

    response = call_haiku(prompt)

    # Parse JSON from response
    try:
        # Find JSON block
        json_match = re.search(r"\{[^{}]+\}", response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(response)

        hook = int(data.get("hook_strength", 50))
        share = int(data.get("shareability", 50))
        relevance = int(data.get("niche_relevance", 50))
        reasoning = str(data.get("reasoning", ""))

        # Weighted total: hook(40%) + shareability(30%) + relevance(30%)
        total = round(hook * 0.40 + share * 0.30 + relevance * 0.30)

        return {
            "hook_strength": hook,
            "shareability": share,
            "niche_relevance": relevance,
            "total": total,
            "reasoning": reasoning,
        }

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        console.print(f"[yellow]Score parsing failed: {e}. Using defaults.[/yellow]")
        return {
            "hook_strength": 50,
            "shareability": 50,
            "niche_relevance": 50,
            "total": 50,
            "reasoning": "Could not parse LLM scoring response.",
        }


def pick_best_variant(
    variants: list[str],
    content_type: str = "single",
) -> tuple[str, dict[str, Any]]:
    """
    Score all variants and return the best one with its scores.

    Returns (best_text, scores_dict).
    Falls back to first variant if all scoring fails.
    """
    if not variants:
        return ("", {"hook_strength": 0, "shareability": 0, "niche_relevance": 0, "total": 0, "reasoning": "No variants"})

    if len(variants) == 1:
        scores = score_content(variants[0], content_type)
        return (variants[0], scores)

    best_text = variants[0]
    best_scores: dict[str, Any] = {"total": -1}

    for i, variant in enumerate(variants):
        scores = score_content(variant, content_type)
        console.print(
            f"[dim]Variant {i + 1} score: {scores['total']}/100 "
            f"(hook={scores['hook_strength']}, share={scores['shareability']}, "
            f"relevance={scores['niche_relevance']})[/dim]"
        )
        if scores["total"] > best_scores["total"]:
            best_scores = scores
            best_text = variant

    console.print(
        f"[green]Best variant selected (score: {best_scores['total']}/100): "
        f"{best_text[:80]}...[/green]" if len(best_text) > 80 else
        f"[green]Best variant selected (score: {best_scores['total']}/100): {best_text}[/green]"
    )
    return (best_text, best_scores)


def score_hook(hook_text: str) -> int:
    """
    Quick 0-100 hook strength score for a single line of hook text.

    Uses haiku for speed. Returns integer score.
    """
    prompt = f"""Rate the hook strength of this tweet opening line on a scale of 0-100.

A strong hook (80-100): Bold claim, surprising stat, pattern interrupt, or story that makes you NEED to read more.
A weak hook (0-40): Generic, vague, starts with "I", no tension, no surprise.

HOOK TEXT:
"{hook_text}"

Respond with a single integer (0-100). Nothing else."""

    response = call_haiku(prompt)

    # Extract integer from response
    numbers = re.findall(r"\b(\d{1,3})\b", response.strip())
    if numbers:
        score = int(numbers[0])
        return min(100, max(0, score))

    console.print(f"[yellow]Could not parse hook score from: {response}[/yellow]")
    return 50
