"""One place for every model call: model choice, cost, latency and a trace line per call.

Ship-gate rule taught in the course: if a call is not in traces/traces.jsonl, it did not happen.
"""
import json
import os
import pathlib
import time

import anthropic

MODEL = os.getenv("AGENT_MODEL", "claude-haiku-5-5")  # cheapest current model; compare once on a bigger one
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-sonnet-5-5")
EFFORT = os.getenv("AGENT_EFFORT", "medium")  # low | medium | high — tune it against your eval, not by feel

# USD per million tokens (input, output). Cache reads are ignored here to keep the maths readable.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}

TRACE_FILE = pathlib.Path(__file__).parent / "traces" / "traces.jsonl"
client = anthropic.Anthropic()


def cost_usd(model: str, usage) -> float:
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    return (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000


def log_trace(record: dict) -> None:
    TRACE_FILE.parent.mkdir(exist_ok=True)
    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def create(*, run_id: str, step: int, model: str = MODEL, **kwargs):
    """messages.create with tracing. Server-side refusal fallback is on for models that support it."""
    extra = {}
    if model != "claude-haiku-5-5":  # Haiku 5.5 has no server-side fallback
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    started = time.time()
    response = client.beta.messages.create(
        model=model, output_config={"effort": EFFORT}, **extra, **kwargs
    )
    latency = time.time() - started
    log_trace({
        "run_id": run_id,
        "step": step,
        "ts": started,
        "model": response.model,
        "stop_reason": response.stop_reason,
        "latency_s": round(latency, 3),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cost_usd": round(cost_usd(model, response.usage), 6),
        "request_messages": kwargs.get("messages"),
        "response": [b.model_dump() for b in response.content],
    })
    return response, latency
