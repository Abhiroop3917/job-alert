// ibmParser.js — parses IBM careers JSON API response.
// IBM uses POST https://www-api.ibm.com/search/api/v2 (Elasticsearch under the hood).
// field_keyword_18 = job level, field_keyword_19 = location city/country string.

export function parseIBMJobs(data) {
  const hits = data?.hits?.hits || [];
  const jobs = [];

  for (const hit of hits) {
    const src = hit._source || {};
    const rawId = hit._id;
    if (!rawId || !src.title) continue;

    const location = (src.field_keyword_19 || "India")
      .replace(/,\s*IN\s*$/i, ", India")
      .replace(/^Multiple Cities$/i, "India (Multiple Cities)");

    const url = src.url || `https://careers.ibm.com/careers/JobDetail?jobId=${rawId}`;

    jobs.push({
      id: `ibm-${rawId.slice(0, 20)}`,
      title: src.title.trim(),
      location,
      url,
      source: "IBM",
    });
  }

  return jobs;
}
