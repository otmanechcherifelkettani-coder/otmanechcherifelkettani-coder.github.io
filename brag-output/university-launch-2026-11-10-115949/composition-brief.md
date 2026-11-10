# Hyperframes Composition Brief: Shipping AI That Works (University Edition)

## Objective
A 60 s premium SaaS-style launch film that persuades university decision-makers to bring the workshop to their university.

## Output
- Composition: `composition/` (index.html plus six scene files in `compositions/`)
- Render: `brag.mp4`, 1920x1080, 30 fps, 60 s

## Source material
- The uploaded brief (six scenes, voiceover, on-screen text, constraints). Everything on screen comes from it, apart from small UI labels that illustrate the fictional case.
- Copy that must appear verbatim, in caps: AI IS CHANGING HOW THE WORLD WORKS / DON'T JUST TEACH AI. TEACH STUDENTS TO BUILD IT. / SHIPPING AI THAT WORKS. 2 DAYS. HANDS-ON. INDUSTRY-LED. / IDENTIFY. DESIGN. BUILD. TEST. EVALUATE. / NOT JUST THEORY. REAL OUTPUTS. / STUDENT EMPLOYABILITY. CURRICULUM INNOVATION. UNIVERSITY POSITIONING. / SHIPPING AI THAT WORKS. FROM LEARNING AI TO BUILDING AI. BRING THE WORKSHOP TO YOUR UNIVERSITY.
- End card: "Shipping AI That Works", alone.

## Creative direction
See `brag-plan.md`. Tone: app-store / polished premium SaaS launch film.
Avoid: any academy, employer or company name or logo, placeholder text, contact lines, claims that the workshop has already run, and real brands in the fictional cases.

## Audio
- `assets/vo/voiceover.wav`: the full 60 s voice track, lines pre-placed.
- `assets/music/score.wav`: the original ambient-electronic bed, pre-ducked.
- SFX in `assets/sfx/`: soft impacts, clicks, a switch, a card slide and a bell, each on its own track.
- Audio-reactive: the score's RMS drives the background glow intensity.

## Hyperframes notes
GSAP is vendored at `assets/vendor/gsap.min.js`, because the CDN is blocked in this environment. `npx hyperframes check` is the gate before render.
