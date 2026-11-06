// deloitteParser.js — parses Deloitte South Asia Careers HTML (SAP SuccessFactors platform).
// Desktop job links have href before class="jobTitle-link"; mobile has class first.
// Matching desktop-only avoids duplicates without needing ID-based dedup on title links.

const JOB_RE = /href="(\/job\/[^"]+?\/(\d{6,})\/?)"[^>]*class="jobTitle-link"[^>]*>([^<]+)<\/a>/g;
const LOC_RE = /class="jobLocation"[^>]*>\s*([\w\s,()./'-]+?)\s*<\/span>/;

function decodeEntities(s) {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .trim();
}

export function parseDeloitteJobs(html) {
  const jobs = [];
  const seen = new Set();

  for (const m of html.matchAll(JOB_RE)) {
    const id = m[2];
    if (seen.has(id)) continue;
    seen.add(id);

    const path = m[1];
    const title = decodeEntities(m[3]);
    const chunk = html.slice(m.index, m.index + 2000);
    const locMatch = chunk.match(LOC_RE);
    const rawLoc = locMatch ? locMatch[1].replace(/\s+/g, " ").trim() : "India";
    const location = rawLoc.replace(/,\s*IN\s*$/, ", India");

    jobs.push({
      id: `deloitte-${id}`,
      title,
      location,
      url: `https://southasiacareers.deloitte.com${path}`,
      source: "Deloitte",
    });
  }

  return jobs;
}
