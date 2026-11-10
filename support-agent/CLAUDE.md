# Support Agent

Customer support AI agent, following the structure of the freeCodeCamp
"Build a Support Agent with Vercel AI SDK" course, but using Claude (instead of
OpenAI) for generation and Voyage AI (instead of OpenAI) for embeddings.

## Stack

- TypeScript, Node 22, ESM. Run scripts with `tsx` (e.g. `npx tsx scripts/foo.ts`).
- LLM: Vercel AI SDK (`ai`) with `@ai-sdk/anthropic`.
  - Always create the provider explicitly:
    `createAnthropic({ apiKey: process.env.AGENT_ANTHROPIC_API_KEY })`
  - Never use, read, or set `ANTHROPIC_API_KEY`. Don't rely on the default `anthropic` export (it reads `ANTHROPIC_API_KEY`).
- Embeddings: Voyage AI via plain `fetch` to `https://api.voyageai.com/v1/embeddings`
  (`Authorization: Bearer ${process.env.VOYAGE_API_KEY}`). Default model: `voyage-3.5`.
- Vector store: Supabase (pgvector) via `@supabase/supabase-js`,
  using `SUPABASE_URL` and `SUPABASE_SECRET_KEY`.

## Environment variables

`AGENT_ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`
are provided by the environment.

## Rules

- Never write key values to any file, log, or commit. Only reference keys via `process.env`.
- Never print secrets in error messages or debug output.
- `.env` and `node_modules` stay git-ignored.
- Build incrementally: do only the step asked for.

## Commands

- `npm run check` — verify Claude, Voyage and Supabase connectivity (`scripts/check-connections.ts`)
- `npm run typecheck` — `tsc --noEmit`
