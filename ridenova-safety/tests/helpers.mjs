import { readFileSync } from 'node:fs';
export const cases = JSON.parse(readFileSync(new URL('../data/candidate_cases.json', import.meta.url), 'utf8'));
export const byId = new Map(cases.map((c) => [c.case_id, c]));
export const get = (id) => structuredClone(byId.get(id));
