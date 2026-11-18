# Hyperframes Composition Brief: HESTIM Agent ("Nora")

## Objective
A ~36 s French product demo of the HESTIM admissions agent, for HESTIM's director, in a helpdesk agent-workspace look.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080, 30 fps
- Duration: 36 s (explicit: demo, narration-led; scene lengths follow the generated narration)

## Source Material
- Project root: `hestim-agent/`
- Primary files read: README.md, agent/prompt.py, agent/tools.py, config.py (teams, escalation routing), static/inbox.html, knowledge/hestim_kb.md, the pilot proposal
- Product name: Nora, agent IA des admissions HESTIM
- Strongest claim (grounded): answers every WhatsApp/Instagram message in the contact's language (fr, ar, darija, en), qualifies the lead, requests a counselor call, routes finance requests to the Finance team, staff take over at any time
- Copy that must appear verbatim (from the product UI/code):
  - "Prendre le contrôle"
  - "Transférée de Admissions vers Finance par IA"
  - "Nora · IA"
  - statuses "Prêt", team names Admissions / Finance / Scolarité / Vie étudiante

## Creative Direction
- Tone preset: app-store; direction: calm product demo, one night in the admissions inbox
- Hook: "Samedi · 23:14" and a Darija WhatsApp message arriving while the office is closed
- Outro: "Chaque message a une réponse." / "Vos conseillers parlent aux bons candidats." / "HESTIM · Agent IA admissions — Pilote de 7 semaines"
- Avoid: generic SaaS language, abstract filler, any third-party logo or product name (the helpdesk look is a layout and palette only)

## Visual Identity
- Rail/header #03363D, workspace #F8F9F9, panels #FFFFFF, hairlines #D8DCDE
- Text #2F3941 / #68737D, accent #1F73B7, success #038153 on #EDF8F4, Finance #AD5918 on #FFF0E1
- Font: Inter (bundled), weights 400 and 700 only (no network font fetch in this sandbox)

## Storyboard
1. hook — 0–7 s — time, Darija message bubble, "Le bureau est fermé."
2. workspace — 7–30 s — reply in Darija; profile fields fill; "Prêt"; counselor-call note; Youssef's receipt routed to Finance; Monday takeover by Karim
3. outro — 30–36 s — two lines and the pilot footer

## Audio
- Voice: six Kokoro clips (ff_siwis, fr-fr) in `assets/vo/`, on their own lane, starting 0.5, 7.3, 13.0, 20.9, 26.5, 30.6 s
- Music: vol-12 at 0.15 for the whole film (ducked under the voice), fade in 1 s, fade out 2.5 s
- Cue guidance: preset `happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json`; the "Prêt" chip is beat-locked to the 17.47 s strong cue
- Audio-reactive: none (narration-led, polished restraint) — documented choice
- SFX: drop_001 on the message landing, rollover2 on "Prêt", mouseclick1 on the takeover click, impactBell_heavy_000 on the outro footer

All contact names and messages are fictional placeholders.
