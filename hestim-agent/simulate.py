"""Pre-launch test harness: synthetic personas talk to the agent, a judge grades each run.

    python simulate.py                       # run all personas in personas.json
    python simulate.py --only bac-darija-fees
    python simulate.py --generate 50 --from-transcripts exports/   # build personas from real chats

Runs against an isolated DB (data/sim.db). Every run calls the Claude API: it costs money.
Re-run on every change to the prompt or knowledge base; regressions show up as failed checks.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import config

config.DB_PATH = os.getenv("SIM_DB_PATH", "data/sim.db")

import db  # noqa: E402
from agent import core  # noqa: E402

MAX_TURNS = 6
PERSONA_SYSTEM = """Tu joues un contact qui écrit à HESTIM sur WhatsApp. Profil : {profile}
Langue : {lang}. Écris comme un vrai utilisateur de messagerie : messages courts, fautes possibles,
une idée par message. Réagis à ce que l'assistante dit. Si ta demande est réglée ou si l'on te dit
qu'un humain va reprendre, réponds exactement FIN."""

JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "language_ok": {"type": "boolean"},
        "no_invented_facts": {"type": "boolean"},
        "tone_ok": {"type": "boolean"},
        "expectations_met": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["language_ok", "no_invented_facts", "tone_ok", "expectations_met", "issues"],
}


def persona_says(persona, transcript):
    msgs = [{"role": "user", "content": "[Début de la conversation]"}]
    msgs += [{"role": "user" if t["who"] == "agent" else "assistant", "content": t["text"]} for t in transcript]
    resp = core.client().messages.create(
        model=config.MODEL, max_tokens=1000, output_config={"effort": "low"},
        system=PERSONA_SYSTEM.format(profile=persona["profile"], lang=persona["lang"]),
        messages=msgs,
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def judge(persona, transcript, contact, conv, escalations):
    kb = (Path(__file__).parent / "knowledge" / "hestim_kb.md").read_text(encoding="utf-8")
    state = {"lead_status": contact["lead_status"], "kind": contact["kind"], "handler": conv["handler"],
             "subscribed": bool(contact["subscribed"]),
             "escalations": [{"category": e["category"], "summary": e["summary"]} for e in escalations]}
    prompt = (f"<base>{kb}</base>\n<attendu>{json.dumps(persona['expect'], ensure_ascii=False)}</attendu>\n"
              f"<etat_final>{json.dumps(state, ensure_ascii=False)}</etat_final>\n<conversation>\n"
              + "\n".join(f"{t['who']}: {t['text']}" for t in transcript) + "\n</conversation>")
    resp = core.client().messages.create(
        model=config.MODEL, max_tokens=2000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        system="Tu évalues un agent IA d'admissions. no_invented_facts=false si l'agent affirme un fait absent "
               "de la base ou marqué [À CONFIRMER]. expectations_met compare l'état final et la conversation à <attendu>.",
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def hard_checks(expect, contact, conv, escalations):
    fails = []
    if "lead_status" in expect and contact["lead_status"] != expect["lead_status"]:
        fails.append(f"lead_status {contact['lead_status']} != {expect['lead_status']}")
    if expect.get("handoff") and conv["handler"] != "human":
        fails.append("no handoff")
    if expect.get("escalate") and not escalations:
        fails.append("no escalation")
    if expect.get("category") and expect["category"] not in {e["category"] for e in escalations}:
        fails.append(f"missing escalation category {expect['category']}")
    if expect.get("unsubscribed") and contact["subscribed"]:
        fails.append("not unsubscribed")
    return fails


def run_persona(persona):
    _contact, conv = db.get_or_create_conversation("web", f"sim-{persona['id']}", None)
    transcript, text = [], persona["opening"]
    for _ in range(MAX_TURNS):
        transcript.append({"who": "contact", "text": text})
        db.add_message(conv["id"], "in", "contact", text)
        reply = core.run_turn(conv["id"], text)
        if not reply:
            break
        transcript.append({"who": "agent", "text": reply})
        if db.get_conversation(conv["id"])["handler"] != "ai":
            break
        text = persona_says(persona, transcript)
        if text.strip().upper().startswith("FIN"):
            break
    conv = db.get_conversation(conv["id"])
    contact = db.get_contact(conv["contact_id"])
    escalations = db.list_escalations(conv["id"], unresolved_only=False)
    hard = hard_checks(persona["expect"], contact, conv, escalations)
    soft = judge(persona, transcript, contact, conv, escalations)
    passed = not hard and all(soft[k] for k in ("language_ok", "no_invented_facts", "tone_ok", "expectations_met"))
    return {"id": persona["id"], "passed": passed, "hard_failures": hard, "judge": soft, "transcript": transcript}


def generate_personas(n, transcripts_dir):
    """Draft n personas from real exported conversations (one .txt per conversation)."""
    samples = []
    for p in sorted(Path(transcripts_dir).glob("*.txt"))[:200]:
        samples.append(p.read_text(encoding="utf-8")[:2000])
    schema = {"type": "object", "additionalProperties": False, "required": ["personas"],
              "properties": {"personas": {"type": "array", "items": {
                  "type": "object", "additionalProperties": False,
                  "required": ["id", "lang", "opening", "profile", "expect"],
                  "properties": {"id": {"type": "string"}, "lang": {"type": "string"}, "opening": {"type": "string"},
                                 "profile": {"type": "string"},
                                 "expect": {"type": "object", "additionalProperties": False,
                                            "required": ["lead_status", "escalate"],
                                            "properties": {"lead_status": {"type": "string", "enum": ["ready", "undecided", "general", "not_fit", "enrolled"]},
                                                           "escalate": {"type": "boolean"}}}}}}}}
    with core.client().messages.stream(
        model=config.MODEL, max_tokens=64000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content":
                   f"Voici des conversations réelles reçues par HESTIM. Crée {n} personas synthétiques variés "
                   "(langues, profils, intentions, cas difficiles) qui reflètent ce trafic réel, sans copier "
                   "de données personnelles.\n\n" + "\n\n---\n\n".join(samples)}],
    ) as stream:
        final = stream.get_final_message()
    return json.loads(next(b.text for b in final.content if b.type == "text"))["personas"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--generate", type=int)
    ap.add_argument("--from-transcripts")
    ap.add_argument("--personas", default="personas.json")
    args = ap.parse_args()

    if args.generate:
        if not args.from_transcripts:
            sys.exit("--generate needs --from-transcripts DIR")
        personas = generate_personas(args.generate, args.from_transcripts)
        Path("personas.generated.json").write_text(json.dumps(personas, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {len(personas)} personas to personas.generated.json — review them, then --personas personas.generated.json")
        return

    if os.path.exists(config.DB_PATH):
        os.remove(config.DB_PATH)
    personas = json.loads(Path(args.personas).read_text(encoding="utf-8"))
    if args.only:
        personas = [p for p in personas if p["id"] == args.only]
    results = []
    for p in personas:
        r = run_persona(p)
        results.append(r)
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"[{mark}] {p['id']}  {'; '.join(r['hard_failures'] + r['judge']['issues'])}")
    Path("data").mkdir(exist_ok=True)
    Path("data/sim_report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(r["passed"] for r in results)
    print(f"\n{n}/{len(results)} passed — full transcripts in data/sim_report.json")
    sys.exit(0 if n == len(results) else 1)


if __name__ == "__main__":
    main()
