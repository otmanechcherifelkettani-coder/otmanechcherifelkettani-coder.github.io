# Sales pitch · back-office banking edition (CFG Bank) · 93 s, 1920×1080

Professional deck style: brochure palette, restrained motion (fades only), a header naming the proposal, and a footer that tracks the eight sections.
Voice: Luc (ElevenLabs engine), music: quiet 96 BPM bed, ducked 14 dB under the voice. All claims come from the brochure. The risk examples are illustrative.

| Time | Section | Voice | Slide |
|---|---|---|---|
| 0:00 | Title | (music) | Proposition de formation · Équipes back-office · CFG Bank, Shipping AI That Works: "Des agents IA utiles, et sous contrôle." |
| 0:04 | 01 Contexte | Les agents IA entrent dans les opérations bancaires. Ils ne se contentent plus de répondre : ils vérifient, rapprochent, saisissent et transmettent. | Headline + 4-row process table |
| 0:13 | 02 Enjeu | Pour un back-office, c’est une vraie opportunité : moins de tâches répétitives, des délais plus courts, et des équipes concentrées sur les cas complexes. / Mais un agent mal conçu se trompe aussi vite qu’il travaille : un virement traité deux fois, un dossier KYC validé à tort, une donnée personnelle exposée. | Opportunity card against risk card |
| 0:33 | 03 La question | La question n’est donc pas de savoir s’il faut utiliser des agents. C’est de savoir les concevoir, les évaluer, et décider quand ils sont prêts. | Full-bleed statement, three verbs underlined |
| 0:41 | 04 Solution | C’est l’objet de Shipping AI That Works, édition back-office : une méthode en six modules. / Identifier les bons cas d’usage… Et déployer par étapes. | Six module cards |
| 1:00 | 05 Livrable | Chaque participant repart avec une grille d’une page pour décider si un agent est prêt pour la production. | Valeur · Fiabilité · Sécurité · Évaluation · Opérations sheet |
| 1:06 | 06 Intervenant | La session est animée par Otman Kettani, qui pilote des agents IA en production dans cinquante et un pays et onze langues. | Photo, title, 51 / 11 / 10 ans, Centrale Paris, disclaimer |
| 1:15 | 07 Formats | Deux formats sont possibles : une conférence de quatre-vingt-dix minutes pour sensibiliser vos équipes, ou un atelier pratique pour construire et tester un agent. | Two format cards |
| 1:24 | 08 Prochaine étape | Prochaine étape : un échange de vingt minutes, pour définir le format adapté à vos équipes. | Ink slide + contact (name, LinkedIn, e-mail) |

Rebuild (in `../work`): `python3 music_pitch.py && python3 mix_pitch.py`, then
`W=1920 H=1080 DUR=93 PAGE=pitch.html OUT=pitch_noaudio.mp4 node render.js`.
