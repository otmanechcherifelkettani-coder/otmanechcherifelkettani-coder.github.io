// Append-only JSONL files for case events and the access log. Durable across refresh and
// restart. NOT tamper-proof or immutable audit storage: anyone with file access can edit it.
import { appendFileSync, readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export class JsonlLog {
  constructor(file, { retentionDays = null } = {}) {
    this.file = file;
    mkdirSync(dirname(file), { recursive: true });
    if (!existsSync(file)) writeFileSync(file, '');
    if (retentionDays) this.purgeOlderThan(Date.now() - retentionDays * 864e5);
  }
  append(rec) { appendFileSync(this.file, JSON.stringify(rec) + '\n'); }
  readAll() { return readFileSync(this.file, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
  tail(n) { return this.readAll().slice(-n); }
  // Retention: drop records whose real recording time is older than the cut-off.
  purgeOlderThan(cutoffMs) {
    const all = this.readAll();
    const keep = all.filter((r) => !r.recorded_at || Date.parse(r.recorded_at) >= cutoffMs);
    if (keep.length !== all.length) writeFileSync(this.file, keep.map((r) => JSON.stringify(r)).join('\n') + (keep.length ? '\n' : ''));
    return all.length - keep.length;
  }
}
