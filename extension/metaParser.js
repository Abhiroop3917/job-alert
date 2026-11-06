// metaParser.js — parses Meta Careers GraphQL search response and job detail pages.

export function parseMetaJobs(data) {
  const allJobs = data?.data?.job_search_with_featured_jobs_v2?.all_jobs ?? [];
  return allJobs
    .filter((j) => j.id)
    .map((j) => ({
      id:       `meta-${j.id}`,
      title:    j.title || '',
      location: j.locations?.join(', ') || 'India',
      url:      `https://www.metacareers.com/jobs/${j.id}/`,
      source:   'Meta',
    }));
}

export function parseMetaJobDetail(html) {
  const m = html.match(/"qualifications":"((?:[^"\\]|\\.)*)"/);
  if (!m) return '';
  return m[1]
    .replace(/\\n/g, '\n')
    .replace(/\\"/g, '"')
    .replace(/\\\//g, '/')
    .replace(/\\\\/g, '\\');
}
