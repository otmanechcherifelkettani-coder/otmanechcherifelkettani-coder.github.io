import { readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Workbench } from '../src/domain/workbench.js';
import { USERS } from '../src/domain/catalog.js';

export const cases = JSON.parse(readFileSync(new URL('../data/candidate_cases.json', import.meta.url), 'utf8'));
export const byId = new Map(cases.map((c) => [c.case_id, c]));
export const get = (id) => structuredClone(byId.get(id));
export const NOW = Date.parse('2026-03-08T08:00:00Z');
export const memLog = () => { const a = []; return { append: (e) => a.push(e), readAll: () => a, a }; };
export const U = USERS;
let cached;
export function freshWb(opts = {}) { return new Workbench({ cases, log: memLog(), audit: memLog(), now: () => NOW, ...opts }); }
export function sharedWb() { return (cached ||= freshWb()); }
export const tmp = () => mkdtempSync(join(tmpdir(), 'rn-'));
// Manager acknowledges then reassesses
export const ackAndOwn = (wb, id, user = U['u-dm-1']) => wb.command(user, id, 'acknowledge', {});
