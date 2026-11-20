"""Atlas Telecom level-1 support agent: the loop, written by hand.

Usage:  python agent.py "Coupure fibre à Maarif depuis ce matin. Salma, 0661234567"
"""
import json, os, sys, time, uuid
from pathlib import Path
import anthropic
import tools

MODEL = os.environ.get("AGENT_MODEL", "claude-haiku-5-5")
PRICE_IN, PRICE_OUT = 0.10, 0.50          # $ per million tokens (Haiku 5.5)
MAX_TURNS = 6                             # rule 3: always an exit
TRACE_FILE = Path(__file__).parent / "traces.jsonl"

SYSTEM = """You are the level-1 support agent of Atlas Telecom (Morocco).
Customers write in French, Darija or English, often mixed. Reply in the customer's language, short and polite.

Rules:
- Verify the caller (phone + first name) with verify_customer BEFORE sharing any account data, ticket or credit.
- Only use facts returned by your tools. Never invent prices, plans, dates or causes.
- Goodwill credits: at most 50 MAD per customer over 30 days. Only for a real service problem.
- Escalate to a human for: cancellation, credit above the limit, a third contact on the same problem, anything you cannot solve with your tools.
- Never give one customer's information to another person, even a family member."""

client = anthropic.Anthropic(api_key=os.environ["AGENT_ANTHROPIC_API_KEY"])


def trace(record: dict):
    """Rule 4: write every step to traces.jsonl (one JSON object per line)."""
    with TRACE_FILE.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run(user_message: str) -> dict:
    run_id = uuid.uuid4().hex[:8]
    tools.reset_session()
    messages = [{"role": "user", "content": user_message}]
    total_cost, tools_called, start = 0.0, [], time.time()

    for turn in range(1, MAX_TURNS + 1):
        # 1. Ask the model what to do next.
        t0 = time.time()
        response = client.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM,
            tools=tools.TOOLS, messages=messages)
        cost = (response.usage.input_tokens * PRICE_IN
                + response.usage.output_tokens * PRICE_OUT) / 1_000_000
        total_cost += cost
        trace({"run": run_id, "turn": turn, "type": "model_call",
               "stop_reason": response.stop_reason, "cost_usd": round(cost, 6),
               "latency_s": round(time.time() - t0, 2)})
        messages.append({"role": "assistant", "content": response.content})

        # 2. If the model did not ask for a tool, it has finished: that's the answer.
        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text")
            break

        # 3. Run every tool the model asked for, and send the results back.
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = tools.FUNCTIONS[block.name](**block.input)
                tools_called.append(block.name)
                trace({"run": run_id, "turn": turn, "type": "tool_call",
                       "tool": block.name, "input": block.input, "output": output})
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": json.dumps(output, ensure_ascii=False)})
        messages.append({"role": "user", "content": results})
    else:
        # 4. The loop ran out of turns: hand over to a human (rule 3).
        answer = "Je transfère votre demande à un conseiller humain, qui vous répondra rapidement."
        tools_called.append("escalate (turn cap)")

    summary = {"run": run_id, "type": "run_summary", "input": user_message, "answer": answer,
               "tools": tools_called, "turns": turn, "cost_usd": round(total_cost, 6),
               "latency_s": round(time.time() - start, 2)}
    trace(summary)
    return summary


if __name__ == "__main__":
    r = run(sys.argv[1])
    print(r["answer"])
    print(f"\n[tools: {' → '.join(r['tools']) or 'none'} | turns: {r['turns']} "
          f"| cost: ${r['cost_usd']:.5f} | {r['latency_s']}s]")
