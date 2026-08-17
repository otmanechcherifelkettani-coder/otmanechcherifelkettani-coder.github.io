# UI UX Pro Max — vendored skill

Project-level install of the [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
plugin, copied into `.claude/skills/` so it loads automatically for any Claude Code
session in this repo (including ephemeral web/remote containers, where `~/.claude`
does not persist).

| | |
|---|---|
| Upstream | `nextlevelbuilder/ui-ux-pro-max-skill` |
| Release | `v2.15.0` |
| Commit | `a38d04c3d5c298c851dbe5e6ee1965ee3de42cb5` (2026-08-14) |
| License | MIT — see `.claude/ui-ux-pro-max-LICENSE` |

## Skills installed

| Skill | Purpose |
|---|---|
| `ui-ux-pro-max` | Core design intelligence — searchable styles, palettes, font pairings, UX guidelines, icons, chart types, 22 stack guides |
| `design` | Umbrella design skill — logos, corporate identity, banners, icons, social images |
| `design-system` | Three-layer design tokens (primitive → semantic → component), component specs |
| `ui-styling` | shadcn/ui + Tailwind implementation, canvas-based visual design (bundles TTF fonts) |
| `brand` | Brand voice, visual identity, messaging frameworks, consistency checks |
| `banner-design` | Platform-sized banners for social, ads, web heroes, print |
| `slides` | Strategic HTML presentations with Chart.js |

## Usage

The core skill exposes a local search CLI (no network, no API key):

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py --help
python3 .claude/skills/ui-ux-pro-max/scripts/search.py styles "minimal editorial"
```

Or just invoke it by name in a session: `/ui-ux-pro-max`.

## Updating

```bash
git clone --depth 1 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git /tmp/uupm
rm -rf .claude/skills && mkdir -p .claude/skills
cp -r /tmp/uupm/.claude/skills/. .claude/skills/
cp /tmp/uupm/LICENSE .claude/ui-ux-pro-max-LICENSE
```

Then update the release/commit row above.

## Notes

- `.claude/` is a dot-directory, so GitHub Pages/Jekyll excludes it from the published
  site. Nothing here is served at `otmanechcherifelkettani-coder.github.io`.
- Logo and icon generation in the `design` skill call Google Gemini and need an API key.
  Every other skill is fully local.
