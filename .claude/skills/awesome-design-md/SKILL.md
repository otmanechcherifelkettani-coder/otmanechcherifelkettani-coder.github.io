---
name: awesome-design-md
description: Curated collection of 74 DESIGN.md design-system documents extracted from real developer-focused websites (Stripe, Linear, Vercel, Apple, Notion, Figma, and more). Use when building UI that should match a specific brand's design language, when the user names one of these brands as a visual reference, or when they ask for "a page that looks like X". Load the matching reference file and follow its tokens, patterns, and rules while generating UI.
---

# Awesome DESIGN.md

A library of ready-to-use `DESIGN.md` files, each a plain-text design-system document analyzing a real website: color tokens, typography, spacing, component patterns, motion, and layout rules. Source: https://github.com/VoltAgent/awesome-design-md (DESIGN.md is a concept introduced by Google Stitch).

## How to use

1. Identify which brand's design language the user wants (explicitly named, or pick the closest match to the aesthetic they describe).
2. Read `references/<brand>.md` for that brand.
3. Apply its design tokens, patterns, and rules when generating or restyling UI. Treat the file as the source of truth for look and feel — do not mix in tokens from other brands unless asked.
4. If the user wants the DESIGN.md in their project, copy the reference file to the project root as `DESIGN.md`.

## Available brands

airbnb, airtable, apple, binance, bmw-m, bmw, bugatti, cal, claude, clay, clickhouse, cohere, coinbase, composio, cursor, dell-1996, elevenlabs, expo, ferrari, figma, framer, hashicorp, hp, ibm, intercom, kraken, lamborghini, linear.app, lovable, mastercard, meta, minimax, mintlify, miro, mistral.ai, mongodb, nike, nintendo-2001, notion, nvidia, ollama, opencode.ai, pinterest, playstation, posthog, raycast, renault, replicate, resend, revolut, runwayml, sanity, sentry, shopify, slack, spacex, spotify, starbucks, stripe, supabase, superhuman, tesla, theverge, together.ai, uber, vercel, vodafone, voltagent, warp, webflow, wired, wise, x.ai, zapier

Each is available at `references/<name>.md` (e.g. `references/stripe.md`, `references/linear.app.md`).

## Picking a match from a described aesthetic

- Clean developer-tool minimalism: linear.app, vercel, raycast, resend, warp
- Polished fintech: stripe, wise, revolut, mastercard, coinbase
- Editorial / content: theverge, wired, notion, mintlify
- Bold / automotive / dramatic: tesla, ferrari, lamborghini, bugatti, bmw-m, spacex
- Playful consumer: airbnb, spotify, nike, starbucks, pinterest
- AI-native: claude, x.ai, mistral.ai, cohere, elevenlabs, runwayml
