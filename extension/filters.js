// filters.js — apply keyword and location filters to normalized jobs.

function matchesAnyKeyword(title, keywords) {
  if (!keywords || keywords.length === 0) return true; // no keywords => match all
  const lower = title.toLowerCase();
  return keywords.some((kw) => kw && lower.includes(kw.toLowerCase()));
}

function matchesAnyLocation(location, locations) {
  if (!locations || locations.length === 0) return true; // no location filter => match all
  const lower = location.toLowerCase();
  return locations.some((loc) => loc && lower.includes(loc.toLowerCase()));
}

export function applyFilters(jobs, config) {
  return jobs.filter(
    (job) =>
      matchesAnyKeyword(job.title, config.keywords) &&
      matchesAnyLocation(job.location, config.locations)
  );
}
