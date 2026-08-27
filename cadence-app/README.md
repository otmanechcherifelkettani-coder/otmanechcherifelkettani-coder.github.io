# Cadence — React app

Vite + React + TypeScript + Tailwind CSS v4, following the shadcn/ui project
structure. Home of the glassmorphism hero design for the Cadence site.

## Structure

```
components.json                          shadcn/ui CLI configuration
src/components/ui/                       shadcn components live here
src/components/ui/glassmorphism-trust-hero.tsx   the hero section
src/lib/utils.ts                         cn() helper (clsx + tailwind-merge)
src/App.tsx                              renders the hero full-screen
src/index.css                            Tailwind entry point
dist/                                    committed production build (served by GitHub Pages)
```

The `@/` import alias resolves to `src/` (see `vite.config.ts` and
`tsconfig.app.json`). Components must live in `src/components/ui` — that is
the path the shadcn CLI installs into and the path registry components import
from (`@/components/ui/...`), so keeping it means future `npx shadcn add
<component>` calls and copy-pasted registry components work unchanged.

## Develop

```sh
npm install
npm run dev       # local dev server
npm run build     # type-checks then builds to dist/ (commit dist/ after building)
```

## Add more shadcn components

```sh
npx shadcn@latest add button   # etc — config is already in components.json
```
