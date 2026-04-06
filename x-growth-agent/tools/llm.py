from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()

# Model constants
HAIKU_MODEL = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-5"

# Load persona once at module init
_PERSONA_PATH = Path(__file__).parent.parent / "persona.md"
_PERSONA_TEXT: str = ""

def _load_persona() -> str:
    global _PERSONA_TEXT
    if _PERSONA_TEXT:
        return _PERSONA_TEXT
    if _PERSONA_PATH.exists():
        _PERSONA_TEXT = _PERSONA_PATH.read_text(encoding="utf-8")
    else:
        console.print(f"[yellow]Warning: persona.md not found at {_PERSONA_PATH}[/yellow]")
        _PERSONA_TEXT = (
            "You are the founder of Supplyn (supplyn.app), building an AI-powered personalised "
            "supplement stack builder. Your X account (@app_supplyn) is your build-in-public voice. "
            "Write direct, evidence-based, slightly fed-up-with-the-supplement-industry content. "
            "UK English. Short sentences. Founder voice. No corporate speak."
        )
    return _PERSONA_TEXT


_load_persona()

_anthropic_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment.")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def _call_with_retry(
    model: str,
    prompt: str,
    system_extra: str = "",
    max_retries: int = 4,
    max_tokens: int = 2048,
) -> str:
    """Core LLM call with exponential backoff on errors."""
    client = _get_client()
    persona = _load_persona()

    system_prompt = persona
    if system_extra:
        system_prompt = f"{persona}\n\n---\n\n{system_extra}"

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            usage = response.usage
            console.print(
                f"[dim]LLM call | model={model} | "
                f"input={usage.input_tokens} | output={usage.output_tokens} tokens[/dim]"
            )

            content = response.content
            if content and len(content) > 0:
                return content[0].text  # type: ignore[attr-defined]
            return ""

        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                console.print(f"[red]Rate limit exceeded after {max_retries} retries.[/red]")
                raise
            delay = 2.0 * (2 ** attempt)
            console.print(f"[yellow]Rate limit hit. Retrying in {delay:.1f}s...[/yellow]")
            time.sleep(delay)

        except anthropic.APIStatusError as e:
            if attempt == max_retries - 1:
                console.print(f"[red]Anthropic API error: {e}[/red]")
                raise
            delay = 1.5 * (2 ** attempt)
            console.print(f"[yellow]API error ({e.status_code}). Retrying in {delay:.1f}s...[/yellow]")
            time.sleep(delay)

        except anthropic.APIConnectionError:
            if attempt == max_retries - 1:
                console.print("[red]Anthropic API connection failed.[/red]")
                raise
            delay = 2.0 * (2 ** attempt)
            console.print(f"[yellow]Connection error. Retrying in {delay:.1f}s...[/yellow]")
            time.sleep(delay)

    return ""


def call_haiku(prompt: str, system_extra: str = "") -> str:
    """Call Claude Haiku. Used for utility tasks: scoring, analytics, trend summaries."""
    return _call_with_retry(
        model=HAIKU_MODEL,
        prompt=prompt,
        system_extra=system_extra,
        max_tokens=1024,
    )


def call_sonnet(prompt: str, system_extra: str = "") -> str:
    """Call Claude Sonnet. Used for content generation: threads, hooks, single tweets."""
    return _call_with_retry(
        model=SONNET_MODEL,
        prompt=prompt,
        system_extra=system_extra,
        max_tokens=2048,
    )


def generate_variants(
    prompt: str,
    n: int = 3,
    use_sonnet: bool = True,
) -> list[str]:
    """Call LLM n times and return list of unique responses."""
    caller = call_sonnet if use_sonnet else call_haiku
    results: list[str] = []
    for i in range(n):
        # Add variation instruction for subsequent calls
        variation_suffix = ""
        if i > 0:
            variation_suffix = (
                f"\n\nIMPORTANT: This is variant #{i + 1}. "
                "Write a meaningfully different version — different angle, "
                "different opening, different phrasing. Don't repeat previous variants."
            )
        try:
            result = caller(prompt + variation_suffix)
            if result and result.strip():
                results.append(result.strip())
        except Exception as e:
            console.print(f"[yellow]Variant {i + 1} failed: {e}[/yellow]")
    return results
