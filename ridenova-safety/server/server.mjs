// Entry point.   npm start            -> simulated AI, automation in SHADOW mode
//                ANTHROPIC_API_KEY=… npm start -> live AI for re-assessment, translation, policy Q&A
// Env: PORT (8080), REPLAY_NOW (2026-03-08T08:00:00Z), AUTOMATION_MODE (shadow|enabled),
//      AI_MODEL (claude-opus-5-5), AI_EFFORT (low), SIM_FAIL_PCT (5), RETENTION_DAYS (365)
import { createApp } from './app.mjs';

const PORT = Number(process.env.PORT || 8080);
const { server, wb, ai, now } = createApp();
server.listen(PORT, () => {
  console.log(`RideNova Safety Workbench → http://localhost:${PORT}/console.html`);
  console.log(`  ${wb.states.size} cases · AI ${ai.info().mode} (${ai.info().model}) · automation ${wb.mode} · replay clock ${new Date(now()).toISOString()}`);
});
