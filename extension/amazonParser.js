// amazonParser.js — parses Amazon Jobs JSON API response.
// Amazon's API ignores industry_experience=less_than_1_year, so we filter
// by parsing basic_qualifications: keep jobs where max year requirement <= 2
// or where no year is mentioned at all.

const YEAR_RE = /(\d+)\+?\s*(?:to\s*\d+\s*)?years?/gi;
const MAX_YEARS = 2;

function maxYearsInText(text) {
  const clean = (text || "").replace(/<[^>]+>/g, " ");
  const matches = [...clean.matchAll(YEAR_RE)];
  if (matches.length === 0) return 0;
  return Math.max(...matches.map(m => parseInt(m[1], 10)));
}

function isEntryLevel(basicQualifications, description) {
  const bqMax   = maxYearsInText(basicQualifications);
  const descMax = maxYearsInText(description);
  const maxReq  = Math.max(bqMax, descMax);
  if (maxReq === 0) return true;  // no year requirement → include
  return maxReq <= MAX_YEARS;
}

export function parseAmazonJobs(data) {
  const jobs = (data && data.jobs) ? data.jobs : [];
  return jobs
    .filter(j => j.id_icims && isEntryLevel(j.basic_qualifications, j.description))
    .map(j => ({
      id:       `amazon-${j.id_icims}`,
      title:    (j.title || "").trim(),
      location: j.location || "",
      url:      `https://amazon.jobs${j.job_path || ""}`,
      posted:   j.posted_date || "",
      source:   "Amazon",
    }));
}
