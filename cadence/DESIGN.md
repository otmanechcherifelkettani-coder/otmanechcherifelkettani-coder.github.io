# Cadence — Design System

**One-line character:** an audit report you actually want to read. Print-adjacent, hairline-ruled, zero decoration. The design argues the same thing the copy does: this is an advisor's document, not an agency's pitch.

**Audience pressure it must survive:** owner-operators who are skeptical of consultants. Anything that looks like a deck — gradients, glassmorphism, stock imagery, rounded SaaS chrome — reads as overhead. The system therefore borrows its cues from documents that cost money to ignore: ledgers, surveys, engineering drawings.

---

## Keywords

`editorial` · `ledger` · `flat` · `tonal` · `annotated` · `sober` · `precise` · `bilingual-ready`

---

## Colors

Never pure `#000000`. Never pure `#FFFFFF`. Every neutral is warm — the page should feel like paper stock, not a screen default.

| Token | Hex | Role |
|---|---|---|
| `--bone` | `#F2EFE8` | Canvas. The default page background. |
| `--paper` | `#F8F6F0` | Lightest surface. Raised tonal bands, table headers, input fields. This is the ceiling — nothing is whiter. |
| `--bone-2` | `#E9E4D9` | Recessed tonal bands. Alternate full-bleed sections. |
| `--ink` | `#201E1A` | Text, borders, the inverted band. The floor — nothing is blacker. |
| `--ink-2` | `#57534A` | Secondary text, captions, de-emphasized table cells. 6.7:1 on bone. |
| `--line` | `#D6D0C3` | Hairline rules, table borders, section separators. |
| `--oxide` | `#8C3B23` | Accent. Links, hover states, focus rings, active nav, one marked word per display headline, the "recommended" row in pricing. 6.5:1 on bone — passes AA at any size. |
| `--oxide-soft` | `#C98A70` | The accent's only tint. Accent duty on the ink band, where `--oxide` itself lacks contrast. |

### On the accent (the requested indigo replacement)

**Proposal: oxide** — a rust/red-earth `#8C3B23`, same structural role the indigo held, none of its associations. Indigo on a flat neutral canvas is the default costume of a venture-backed dev tool; your clients have seen it on every SaaS invoice they resent. Oxide reads instead as *rubrication* — the red an auditor, a surveyor, or a proofreader puts on a document by hand. It marks findings. That is literally the business.

Rules of use are unchanged from the indigo's role: it never fills large areas, never appears as a background band, and appears at most once per viewport as display-scale text. It is a pen, not a paint bucket.

**Runner-up, if oxide feels alarming in context:** ledger green `#31513F` (same contrast class on bone, reads as banker's/accountant's green). Swap the token, change nothing else.

---

## Typography

Two families, both SIL Open Font License, both self-hostable, both with full Latin Extended coverage — including `œ Œ é è ê ë à â ç î ï ô û ù «»` — so the French build is a copy swap, not a font hunt.

| Role | Family | Weights | Notes |
|---|---|---|---|
| Display & body | **Archivo** (variable, Google Fonts, OFL) | 400, 500 | Grotesk without the tech-mono coldness. Display is always weight **400** — size does the talking, not weight. 500 is reserved for buttons, table headers, and inline emphasis. Nothing on the site is bold. |
| Annotation | **IBM Plex Mono** (Google Fonts, OFL) | 400, 500 | Index numbers, section labels, prices, captions, data. Always uppercase or tabular figures. The voice of measurement. |

### Tracking law (from the secondary reference)

Headlines sit at weight 400 and tracking tightens as size grows:

| Size | Letter-spacing |
|---|---|
| ≥ 96px | `-0.035em` |
| 56–95px | `-0.025em` |
| 32–55px | `-0.015em` |
| 18–31px | `-0.005em` |
| Body (≤17px) | `0` |
| Mono annotation (uppercase) | `+0.08em` |

---

## Type scale

The reference jumps from display straight to 10px annotation. Cadence keeps both poles and adds the **reading register** between them — the sizes where method and pricing actually get read. Display sizes are `clamp()`-based so the ~20% longer French copy compresses gracefully instead of wrapping badly.

| Slot | Size | Leading | Face | Use |
|---|---|---|---|---|
| Display XL | `clamp(40px, 10vw, 144px)` | 0.95 | Archivo 400 | Hero statement only. One per page. |
| Display L | `clamp(32px, 6.5vw, 84px)` | 1.0 | Archivo 400 | Offer names, section-opening claims. Floor is 32px so it stays a clear step below Display XL's 40px at the 375px breakpoint. |
| Heading | `clamp(30px, 4vw, 40px)` | 1.15 | Archivo 400 | Section titles ("Method", "Pricing"). |
| Subheading | `24px` | 1.3 | Archivo 400 | Method step titles, table row leads. |
| **Lead** | `20px` | 1.5 | Archivo 400 | First paragraph of a section. The persuasion size. |
| **Body** | `17px` | 1.65 | Archivo 400 | Everything a skeptic must actually read. Max measure 68ch. |
| Small | `14px` | 1.5 | Archivo 400 | Legal, footnotes, form hints. |
| Annotation | `12px` | 1.4 | Plex Mono 400 | Section indices (`01`, `02`), labels, prices in tables. **Floor is 11px** — the reference's 10px fails once French diacritics stack on it. |

### French-proofing rules (build in English, break in neither)

1. **No fixed-width text slots.** Buttons, nav items, tabs, and table headers size from padding, never from a set width.
2. **Headroom test.** Any label styled at Subheading or above must survive its French translation. The three offers are the stress case:
   `Audit → Audit` (±0) · `Design → Conception` (+67%) · `Implementation → Mise en œuvre` (−1 char but contains `œ`). Size the offer header slot for **"Conception"**, verify the font renders **"œuvre"**, and the system holds.
3. **Standing test strings** for any new component: `Mise en œuvre`, `Diagnostic opérationnel`, `Prendre rendez-vous`, `Déroulé de la mission`.
4. **Display uses `clamp()`, never a fixed px**, so a +20% headline trades size for fit instead of overflowing.
5. Mono annotations stay uppercase in French too — verify accented capitals (`É`, `À`) render; do not strip accents from capitals, that's a typo in French.

---

## Surfaces & structure

- **Radius: `0px`.** Everywhere. Buttons, inputs, tables, images-if-ever.
- **Shadows: none.** Depth is expressed tonally, never with elevation.
- **Imagery: none.** No photos, no illustrations, no icons beyond typographic marks (`→`, `+`, `01`). The mono annotations and hairlines *are* the visual layer.
- **Borders:** `1px solid var(--line)` for structure; `1px solid var(--ink)` when a component must assert itself (primary button outline, the recommended pricing row).
- **Sections are full-bleed tonal bands, not cards.** The page is a stack of bands: `bone → paper → bone-2 → ink → bone`. Adjacent bands must differ in tone. At most **one ink (inverted) band per page** — spend it on the section that carries the argument (pricing or the closing call). On the ink band: text is `--bone`, secondary text `#A8A296`, accent duty passes to `--oxide-soft`.
- **Band anatomy:** each opens with a mono annotation row — index number left (`01`), section label right (`MÉTHODE` / `METHOD`) — above a hairline, then the Heading. This is the ledger rhythm that replaces card chrome.

## Spacing

Base unit **8px**. Band vertical padding `96–160px` desktop, `64px` mobile. Content column: max-width `1160px`, 12-column grid, `24px` gutters. Reading content (method, pricing prose) narrows to `68ch` — full-bleed backgrounds, narrow text.

## Breakpoints

Exactly four, and no others — no ad-hoc media queries at component-convenient widths. Design and QA at each value; `clamp()` handles everything between them.

| Name | Width | Layout |
|---|---|---|
| `--bp-s` | `375px` | Design floor. Single column, band padding `64px`, grid collapses, pricing table restacked (all prices still visible). Nothing is verified below this width. |
| `--bp-m` | `768px` | Grid engages (12-col), pricing table goes tabular, nav on one line. |
| `--bp-l` | `1160px` | Content column reaches its max-width; from here only band padding and display size grow. |
| `--bp-xl` | `1440px` | Ceiling. Band padding at its `160px` max; content stays at `1160px` and centers — the canvas widens, the document does not. |

Media queries are `min-width` only, written against these four tokens.

---

## Components

**Primary button** — ink fill, bone text, Archivo 500 at 15px, padding `14px 28px`, radius 0. Hover: fill shifts to `--oxide`. On ink bands: bone fill, ink text.

**Secondary button** — transparent, `1px solid var(--ink)`, same metrics. Hover: ink fill, bone text.

**Focus state** — `2px solid var(--oxide)`, `outline-offset: 2px`, never removed.

**Links** — underlined, `text-underline-offset: 3px`, `1px` thickness, ink; hover shifts text and underline to `--oxide`. No unaccompanied color-only links.

**Method steps** — mono index (`01` `02` `03`) in `--oxide`, Subheading title, Body text, hairline between steps. A numbered procedure, not a feature grid.

**Pricing table** — one hairline table for all three offers: not three cards, and never an accordion. All three prices are visible without any interaction, at every breakpoint — on narrow screens the table restacks, it does not collapse. Mono for figures and terms, Archivo for descriptions. The recommended offer gets a `1px` ink border and a mono `RECOMMENDED` tag — no fill, no badge shapes. Fixed prices displayed plainly; a fixed number in mono is the whole trust argument.

**Nav** — text only: wordmark set in Archivo 400 tracked normally, links in mono uppercase 12px. Active link in `--oxide`. Hairline below.

**Forms** — `--paper` field on bone, `1px solid var(--ink-2)` border (fields must read as interactive; `--line` is reserved for rules, table borders, and separators), radius 0, ink focus border. Labels in mono uppercase 12px above the field.

---

## Motion

Nearly none. `150ms ease-out` on `color`, `background-color`, `border-color` only. No transforms, no parallax, no scroll-triggered entrances. A document does not animate.

---

## What this system refuses

Gradients · shadows · rounded corners · photography · icon sets · testimonial carousels · badge walls · emoji · more than one accent per viewport · pure black · pure white · bold display type. Each refusal is the positioning: an advisor shows you the finding; an agency shows you a show.
