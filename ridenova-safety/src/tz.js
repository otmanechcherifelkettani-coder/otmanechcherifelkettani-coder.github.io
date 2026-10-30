// submitted_at is local city time without an offset. To build ONE global queue we convert to UTC.
// Assumption: UTC offsets valid for 1–7 March 2026 (before US/EU DST starts; southern-hemisphere
// DST still active in AU-SE, NZ, CL). Unknown cities fall back to the country default.

const COUNTRY = {
  AD: 1, AE: 4, AR: -3, AT: 1, AU: 10, BB: -4, BD: 6, BE: 1, BH: 3, BO: -4, BR: -3, CA: -5, CH: 1, CL: -3, CO: -5, CR: -6, CZ: 1,
  DE: 1, DK: 1, DO: -4, EC: -5, EE: 2, EG: 2, ES: 1, FI: 2, FR: 1, GB: 0, GH: 0, GR: 2, GT: -6, HK: 8, HN: -6, HR: 1, HU: 1,
  IE: 0, IN: 5.5, IT: 1, JM: -5, JO: 3, JP: 9, KE: 3, KR: 9, KW: 3, LB: 2, LC: -4, LK: 5.5, LT: 2, LU: 1, MT: 1, MX: -6, NG: 1,
  NL: 1, NO: 1, NP: 5.75, NZ: 13, PA: -5, PE: -5, PL: 1, PT: 0, PY: -3, QA: 3, RO: 2, SA: 3, SE: 1, SI: 1, SK: 1, SV: -6,
  TR: 3, TW: 8, UA: 2, UG: 3, US: -5, UY: -3, ZA: 2,
};
const CITY = {
  'Sydney': 11, 'Melbourne': 11, 'Brisbane': 10, 'Perth': 8,
  'Vancouver': -8, 'Calgary': -7, 'Toronto': -5, 'Montreal': -5,
  'Los Angeles': -8, 'Seattle': -8, 'Chicago': -6, 'Houston': -6, 'New York': -5, 'Miami': -5,
};

export const utcOffsetHours = (country, city) => CITY[city] ?? COUNTRY[country] ?? 0;

// Returns epoch ms (UTC).
export function submittedUtcMs(c) {
  const [d, t] = c.submitted_at.split('T');
  const [Y, M, D] = d.split('-').map(Number);
  const [h, m] = t.split(':').map(Number);
  return Date.UTC(Y, M - 1, D, h, m) - utcOffsetHours(c.country, c.city) * 3600e3;
}
