// experienceFilter.js — shared year-based experience filtering used by all parsers.
// Rule: scan text for "N years" patterns; keep job if max found is 0 (no requirement) or ≤ 2.

const YEAR_RE = /(\d+)\+?\s*(?:to\s*\d+\s*)?years?/gi;
const MAX_YEARS = 2;

export function maxYearsInText(text) {
  const clean = (text || "").replace(/<[^>]+>/g, " ");
  const matches = [...clean.matchAll(YEAR_RE)];
  if (matches.length === 0) return 0;
  return Math.max(...matches.map((m) => parseInt(m[1], 10)));
}

// Returns true when all provided texts together indicate ≤2 years or no explicit year requirement.
export function isEntryLevelExperience(...texts) {
  const maxReq = Math.max(...texts.map(maxYearsInText), 0);
  return maxReq === 0 || maxReq <= MAX_YEARS;
}
