# Brag Plan: HESTIM Agent ("Nora")

Invocation (as interpreted): `/brag --voice --tone app-store --duration ~40 --format landscape`, French, helpdesk (Zendesk-style) look.
Duration is explicit because this is a sales demo for HESTIM's director, not a social clip: the flow needs ~40 s to land. The final number follows the generated narration.

## What is this app?
An AI agent that answers every WhatsApp and Instagram message HESTIM receives, in French, Arabic, Darija or English, qualifies prospects, sends ready ones to a counselor and routes student requests to the right team, with a shared inbox where staff take over at any time.

## The angle
The message that arrives when nobody is at the office. A real prospect writes on a Saturday night in Darija; instead of waiting until Monday, the conversation is answered, qualified and on a counselor's desk before they put the phone down. The video is that one night, seen from the HESTIM team's inbox.

## Hook (first 2-3 seconds)
A dark frame, the time "Samedi · 23:14", and a WhatsApp-style message bubble dropping in: "salam, chhal les frais dyal l'ingénierie ?". The narration says nobody is at the office.

## Key moments (the middle)
- The message lands in the helpdesk workspace as a new conversation tagged "IA", and Nora's reply appears in Darija within the same minute.
- The customer panel fills itself field by field: type Prospect, Bac 2027 Sciences Maths, Génie Industriel, Casablanca, status "Prêt", then the internal note "Appel conseiller demandé".
- A second conversation (a student's missing receipt) shows the routing note "Transférée de Admissions vers Finance par IA" and the team badge switches to Finance.
- A counselor clicks "Prendre le contrôle" and replies under their own name.

## Outro / punchline
"Chaque message a une réponse. Vos conseillers parlent aux bons candidats." then "HESTIM · Agent IA admissions" and "Pilote de 7 semaines".

## User flow worth showing
1. Entry: a prospect writes on WhatsApp outside office hours.
2. Key action: the agent answers in the prospect's language, records the profile, marks the lead ready and requests a counselor call; a student request is routed to Finance.
3. Result: the counselor sees a qualified conversation in the inbox and takes over.

## Tone
- Preset: app-store
- Creative direction: calm product demo for a school director, one night in the admissions inbox
- Interpretation: clean feature reveals inside one real interface rather than separate cards; smooth slides; no jokes, no hype words; the voice carries the story, the UI proves it.

## Format: landscape — 1920x1080
## Duration: ~40 s (scene lengths follow the narration)

## Visual identity
The product's own inbox is WhatsApp-styled; HESTIM asked for a helpdesk (Zendesk-like) look for this demo, so the composition recreates an agent-workspace layout in that spirit with HESTIM branding only (no third-party logo or product name).
- Rail and header: deep teal #03363D, rail icons #C2C8CC
- Workspace ground: #F8F9F9, panels #FFFFFF, hairlines #D8DCDE
- Text: #2F3941 primary, #68737D secondary
- Accent (AI / links / primary buttons): #1F73B7
- Success / "Prêt": #038153 on #EDF8F4; Finance team badge: #AD5918 on #FFF0E1
- Agent bubble (Nora): #EDF7FF; contact bubble: #FFFFFF; internal note: #FFF7ED with #AD5918 rule
- Display and body font: Inter (bundled)
- Strongest visual element: the three-column workspace (ticket list, conversation, customer context) filling itself in real time

## Share copy (draft)
Samedi, 23 h 14 : un futur étudiant écrit à HESTIM. Nora répond en darija, qualifie sa demande et réserve un appel avec un conseiller pour lundi matin.

## Audio direction
- Role: voice-led, warm low bed under it
- Music: happy-beats-business-moves-vol-12 (steady, clean)
- Music treatment: ducked to ~0.13 under the narration for the whole film, short lift on the outro, fade out over the last 2 s
- Music cue guidance: bundled preset `happy-beats-business-moves-vol-12-by-ende-dot-app.music-cues.json` (≈110 BPM). Strong cues in window: 8.74, 17.47, 22.93 s; beat grid every ~0.545 s. Use at most 1-2 locks (the workspace reveal near 8.74 s if the narration allows); readability and narration come first.
- Audio-reactive treatment: none — narration-led and polished; documented as a choice.
- SFX posture: sparse (3-4): soft drop when the WhatsApp message lands, a light tick when the "Prêt" status lands, a mouse click on "Prendre le contrôle", one soft bell on the outro.
- Audio-coupled moments: message landing, status chip, takeover click, outro logo.
- Restraint rule: nothing loud under the voice; no typing clatter.

## Voiceover script (French, Kokoro ff_siwis)
1. Samedi soir, vingt-trois heures. Un futur étudiant écrit à HESTIM sur WhatsApp. Personne n'est au bureau.
2. Nora, l'assistante IA de HESTIM, lui répond tout de suite, dans sa langue. Même en darija.
3. Elle comprend son profil : son bac, le programme qui l'intéresse, sa ville. Il est prêt : elle demande un appel avec un conseiller.
4. Une question de paiement d'un étudiant ? La conversation part directement à l'équipe finance.
5. Et à tout moment, un conseiller reprend la main.
6. Chaque message a une réponse. Vos conseillers parlent aux bons candidats.

## Storyboard

### Scene 1 — Hook — ~5 s
Dark teal ground. "Samedi · 23:14" in small caps, then a phone-style message bubble drops in with the Darija line. A quiet line: "Le bureau est fermé."
Sequential/interaction: yes — bubble drops in after the time.
Audio intent: hush, then the notification.
Audio-coupled idea: soft drop SFX on the bubble.
Music: bed starts low.
Transition mood: smooth → the bubble flies into the workspace.

### Scene 2 — Workspace + reply — ~6 s
The helpdesk workspace: rail, views list (Admissions, Finance, Scolarité), ticket list with "Salma I. · WhatsApp · IA". The conversation opens: the contact bubble, then Nora's reply in Darija ("Mrehba Salma ! Les frais dépendent du programme. Chnou l-bac dyalek ?") with "Nora · IA · 23:14".
Sequential/interaction: yes — ticket row arrives, conversation opens, reply appears.
Audio-coupled idea: none beyond the voice.
Transition mood: clean, same stage.

### Scene 3 — Qualification — ~9 s
Two more exchanges arrive (prospect: "Bac 2027 sciences maths, Casa. Bghit génie industriel"). The right panel fills field by field: Type Prospect → Niveau Bac 2027 SM → Programme Génie Industriel → Ville Casablanca → Statut "Prêt" (green chip). An internal note card appears: "Appel conseiller demandé · lundi après 18 h".
Sequential/interaction: yes — 5 fields, each held; status chip is the accent.
Audio-coupled idea: light tick on "Prêt".
Transition mood: slide to the next ticket.

### Scene 4 — Routing — ~6 s
Second ticket "Youssef A. · Instagram". Message: "je n'ai pas reçu mon reçu du trimestre". System note: "Transférée de Admissions vers Finance par IA"; team badge switches Admissions → Finance.
Sequential/interaction: yes — badge switch.
Transition mood: clean.

### Scene 5 — Takeover — ~5 s
Back on Salma's ticket on Monday. Cursor clicks "Prendre le contrôle"; the badge changes from "IA" to "Karim"; Karim's reply appears: "Bonjour Salma, c'est Karim des admissions. Je vous appelle à 18 h ?"
Sequential/interaction: yes — simulated click.
Audio-coupled idea: mouse click.
Transition mood: soft → outro.

### Scene 6 — Outro — ~5 s
Teal ground. "Chaque message a une réponse." then "Vos conseillers parlent aux bons candidats." then "HESTIM · Agent IA admissions — Pilote de 7 semaines".
Audio-coupled idea: one soft bell when the last line lands; music lifts and fades.

**Music mood for this video:** steady, warm, understated
**Audio summary:** a low bed under a calm French narration, four small UI sounds, a soft lift and fade on the last line.

All names and messages are fictional placeholders; no real contact data is shown.
