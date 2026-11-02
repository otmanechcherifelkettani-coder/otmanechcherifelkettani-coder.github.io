// Append-only JSONL files for case events and the access log. Durable across refresh and restart.
//
// chained: true -> every record carries prev_hash and hash = sha256(prev_hash + canonical record).
// Editing, inserting or deleting a record breaks verify(). That makes the log TAMPER-EVIDENT, not
// tamper-proof: someone with file access could rewrite the whole chain, which is why production
// would anchor the head hash somewhere the operator cannot write (WORM storage, a timestamping service).
// Retention purges a prefix of the chain and records the anchor it resumes from in <file>.anchor.json.

import { appendFileSync, readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { createHash } from 'node:crypto';

const GENESIS = '0'.repeat(64);
const canon = (o) => JSON.stringify(o, Object.keys(o).sort());
const sha = (s) => createHash('sha256').update(s).digest('hex');
const body = (r) => { const { hash, prev_hash, ...rest } = r; return rest; };

export class JsonlLog {
  constructor(file, { retentionDays = null, chained = false, nowMs = () => Date.now() } = {}) {
    this.file = file; this.chained = chained; this.anchorFile = file + '.anchor.json';
    mkdirSync(dirname(file), { recursive: true });
    if (!existsSync(file)) writeFileSync(file, '');
    if (retentionDays) this.purgeOlderThan(nowMs() - retentionDays * 864e5);
    const all = this.readAll();
    this.head = all.length ? all[all.length - 1].hash || null : this.anchor().resume_from;
  }
  anchor() { return existsSync(this.anchorFile) ? JSON.parse(readFileSync(this.anchorFile, 'utf8')) : { resume_from: GENESIS, purged: 0 }; }
  append(rec) {
    if (this.chained) { rec.prev_hash = this.head || GENESIS; rec.hash = sha(rec.prev_hash + canon(body(rec))); this.head = rec.hash; }
    appendFileSync(this.file, JSON.stringify(rec) + '\n');
  }
  readAll() { return readFileSync(this.file, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
  tail(n) { return this.readAll().slice(-n); }

  // Recompute the chain. Returns { ok, entries, broken_at, reason }.
  verify() {
    if (!this.chained) return { ok: null, reason: 'not chained' };
    let prev = this.anchor().resume_from;
    const all = this.readAll();
    for (let i = 0; i < all.length; i++) {
      const r = all[i];
      if (r.prev_hash !== prev) return { ok: false, entries: all.length, broken_at: i, reason: 'link to previous entry broken (entry inserted, removed or reordered)' };
      if (sha(prev + canon(body(r))) !== r.hash) return { ok: false, entries: all.length, broken_at: i, reason: 'entry content changed' };
      prev = r.hash;
    }
    return { ok: true, entries: all.length, head: prev, purged_by_retention: this.anchor().purged };
  }

  // Remove records (by real recording time). For a chained log only a PREFIX may go, so the chain
  // stays verifiable from the anchor.
  purgeOlderThan(cutoffMs) {
    const all = this.readAll();
    let k = 0;
    if (this.chained) while (k < all.length && all[k].recorded_at && Date.parse(all[k].recorded_at) < cutoffMs) k++;
    const keep = this.chained ? all.slice(k) : all.filter((r) => !r.recorded_at || Date.parse(r.recorded_at) >= cutoffMs);
    const removed = all.length - keep.length;
    if (!removed) return 0;
    if (this.chained) { const a = this.anchor(); writeFileSync(this.anchorFile, JSON.stringify({ resume_from: all[k - 1].hash, purged: a.purged + removed, last_purge_at: new Date().toISOString() })); }
    this.writeAll(keep);
    return removed;
  }
  writeAll(recs) { writeFileSync(this.file, recs.map((r) => JSON.stringify(r)).join('\n') + (recs.length ? '\n' : '')); }
}
