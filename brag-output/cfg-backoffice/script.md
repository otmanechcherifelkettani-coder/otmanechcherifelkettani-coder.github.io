# Back-office banking edition (CFG Bank) · voice-over script (FR) · 41.3 s, 1080×1920

Same voice as the final LinkedIn cut (Luc, ElevenLabs engine). The "Votre formateur" line is reused from that cut.
CFG Bank appears only as text ("Pour les équipes back-office de CFG Bank"), on the opening and closing screens: no logo, no brand colors, no facts about the bank. The transfer example is labelled "Exemple fictif".

| Time | Beat | Voice | On screen |
|---|---|---|---|
| 0.25 | Hook | Les agents IA arrivent dans les back-offices bancaires. | Audience label + headline; banking tool calls drift past |
| 3.5 | What they do | Ils vérifient des KYC, rapprochent des relevés, traitent des virements, trient des réclamations. | Each task lands on its words, with its tool call |
| 8.75 | Stakes | Mais en banque, une erreur d’agent, c’est un virement exécuté deux fois. | Fictional 25 000 MAD transfer → 50 000 MAD executed, ×2 |
| 13.35 | The gap | Tout le monde utilisera ces agents. Peu sauront les comprendre, et les piloter. | 60 lit dots → 3 stay lit |
| 18.0 | The method | C’est ce que vous apprenez : choisir le bon cas, concevoir avec des garde-fous, tester, déployer. | 4 steps (human validation, loi 09-08) tick on each word |
| 24.0 | Their role | L’agent prépare. Vous gardez la main, et vous devenez le référent IA de votre équipe. | Spot use cases · scope and evaluate an agent · become the team's AI reference |
| 29.15 | The sell | Votre formateur : Otman Kettani. Il pilote des agents IA dans cinquante et un pays, en onze langues. | Photo, title, 51 / 11 / 10 ans, Centrale Paris, disclaimer |
| 35.45 | Close | Shipping AI That Works, édition back-office. Organisons une session pour vos équipes. | Mint end card, "Organiser une session →", LinkedIn |

To remove the bank's name: edit the two "CFG Bank" strings in `../work/video-cfg.html`, then re-render:
`W=1080 H=1920 DUR=41.3 PAGE=video-cfg.html OUT=cfg_noaudio.mp4 node render.js` (audio: `python3 music_cfg.py && python3 mix_cfg.py`).
