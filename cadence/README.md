# Cadence — website

Static implementation of the Claude Design handoff in `../project/` (`Cadence Home.dc.html`,
`Cadence Work.dc.html`, `Cadence About.dc.html`).

## Files

```
index.html            Home    — hero, story, services, method + terminal, selected work, CTA
work.html             Work    — five case studies as an accordion (Context / Approach / Results)
about.html            About   — bio, portrait, trajectory, side projects, CTA
assets/styles.css     All design tokens and layout; one stylesheet for all three pages
assets/accordion.js   Fallback only — enforces one-open-at-a-time on older browsers
assets/portrait.webp  Portrait, extracted from the design bundle's image-slot state (760×760)
```

No build step and no dependencies. Fonts (Inter, Geist Mono) load from Google Fonts.

## Run locally

```sh
python3 -m http.server 8000   # then open http://localhost:8000
```

## Deploy

Upload the contents of this directory to any static host — Netlify, Vercel, Cloudflare Pages,
GitHub Pages, S3. No configuration needed.

## Notes

- The Work accordion is native `<details name="cases">`, so it works with JavaScript disabled.
  `accordion.js` only kicks in on engines that don't support the exclusive-accordion `name`
  attribute.
- Contact address (`otmankettani5@gmail.com`) and the LinkedIn URL appear in the header, footer,
  and CTAs on every page — search and replace across all three files if either changes.
