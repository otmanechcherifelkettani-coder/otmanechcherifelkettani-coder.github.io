# Cadence — website

`index.html` is the current site: a self-contained French single page (v2) — hero, à propos
(portrait + stats), méthode, règle des 5×, offre en trois étapes, chantiers types, limites,
contact. All CSS is inline in the file; fonts (Newsreader, Instrument Sans) load from Google
Fonts. A demo-video section is present but commented out until `assets/cadence-demo.mp4`
exists.

`work.html` and `about.html` are the earlier English pages (Claude Design handoff), kept for
reference; they are no longer linked from the home page.

## Files

```
index.html            Current site — French single page, self-contained (inline CSS)
work.html             Legacy — five case studies as an accordion (Context / Approach / Results)
about.html            Legacy — bio, portrait, trajectory, side projects, CTA
assets/styles.css     Stylesheet for the legacy pages only
assets/accordion.js   Legacy fallback — enforces one-open-at-a-time on older browsers
assets/portrait.webp  Portrait (760×760), used by index.html and about.html
```

No build step and no dependencies.

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
