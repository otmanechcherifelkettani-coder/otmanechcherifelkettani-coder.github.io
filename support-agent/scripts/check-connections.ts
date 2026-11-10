/**
 * Smoke-test connectivity to Claude, Voyage AI and Supabase.
 * Each check runs independently; one failure does not stop the others.
 * Never prints key values.
 */
import { createAnthropic } from "@ai-sdk/anthropic";
import { generateText } from "ai";

type CheckResult = { name: string; ok: boolean; detail: string };

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`Missing environment variable ${name}`);
  return value;
}

function errorMessage(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  // Node's fetch reports network errors as "fetch failed" with the real reason in `cause`.
  const cause = err.cause instanceof Error ? err.cause.message : undefined;
  return cause ? `${err.message} (cause: ${cause})` : err.message;
}

async function checkClaude(): Promise<string> {
  const anthropic = createAnthropic({ apiKey: requireEnv("AGENT_ANTHROPIC_API_KEY") });
  const { text } = await generateText({
    model: anthropic("claude-haiku-5-5"),
    prompt: "Reply with OK",
    maxOutputTokens: 1024,
  });
  return `reply: ${JSON.stringify(text.trim())}`;
}

async function checkVoyage(): Promise<string> {
  const res = await fetch("https://api.voyageai.com/v1/embeddings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${requireEnv("VOYAGE_API_KEY")}`,
    },
    body: JSON.stringify({ input: ["hello"], model: "voyage-3.5" }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  }
  const json = (await res.json()) as { data?: { embedding: number[] }[] };
  const embedding = json.data?.[0]?.embedding;
  if (!Array.isArray(embedding)) throw new Error("Response had no embedding");
  return `vector length: ${embedding.length}`;
}

async function checkSupabase(): Promise<string> {
  const baseUrl = requireEnv("SUPABASE_URL").replace(/\/+$/, "");
  if (new URL(baseUrl).hostname === "supabase.com") {
    throw new Error(
      "SUPABASE_URL points at the Supabase dashboard, not the project API. " +
        "Use the Project URL (https://<project-ref>.supabase.co) from Project Settings → API.",
    );
  }
  const res = await fetch(`${baseUrl}/rest/v1/`, {
    headers: { apikey: requireEnv("SUPABASE_SECRET_KEY") },
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  }
  return `HTTP status: ${res.status}`;
}

async function run(name: string, fn: () => Promise<string>): Promise<CheckResult> {
  try {
    const detail = await fn();
    console.log(`PASS  ${name} — ${detail}`);
    return { name, ok: true, detail };
  } catch (err) {
    const detail = errorMessage(err);
    console.log(`FAIL  ${name} — ${detail}`);
    return { name, ok: false, detail };
  }
}

const results: CheckResult[] = [];
results.push(await run("Claude (claude-haiku-5-5)", checkClaude));
results.push(await run("Voyage (voyage-3.5)", checkVoyage));
results.push(await run("Supabase REST", checkSupabase));

const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exitCode = failed ? 1 : 0;
