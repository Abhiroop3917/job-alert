// jobParser.js — extract and normalize jobs from the Google Careers results HTML.
//
// The results page is server-rendered. Each job card contains an <h3> title,
// a set of location chips, and a "Learn more" anchor to jobs/results/<id>.
// The title sits several KB *before* the job link (nested location <li> chips
// live in between), so we pair each job id with its NEAREST PRECEDING <h3>.
// Service workers have no DOMParser, hence regex extraction.

const H3_RE = /<h3[^>]*>([\s\S]*?)<\/h3>/g;
const JOB_ID_RE = /jobs\/results\/(\d+)/g;
// Match "City, State/Country" style location chips (generic — covers India, USA, etc.)
const LOCATION_RE = /([A-Za-z][A-Za-z .'-]*(?:,\s*[A-Za-z][A-Za-z .'"-]*){1,3})/g;
// Match Google's relative posting time that appears near each job card
const POSTED_RE = /(\d+\s*(?:minute|minutes|hour|hours|day|days|week|weeks|m|h|d)\s*ago|just\s*(?:now|posted))/i;

function stripTags(html) {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseJobs(html) {
  // 1. All <h3> headings with their positions (includes filter headers, which
  //    is fine — they just never end up as the nearest-preceding for a job id).
  const headings = [];
  for (const m of html.matchAll(H3_RE)) {
    const text = stripTags(m[1]);
    if (text) headings.push({ pos: m.index, text });
  }

  // 2. Each unique job id, in document order.
  const jobs = [];
  const seen = new Set();
  for (const m of html.matchAll(JOB_ID_RE)) {
    const id = m[1];
    if (seen.has(id)) continue;
    seen.add(id);
    const pos = m.index;

    // Nearest preceding heading is the job title.
    let title = "";
    for (let i = headings.length - 1; i >= 0; i--) {
      if (headings[i].pos < pos) {
        title = headings[i].text;
        break;
      }
    }
    if (!title) continue;

    // Location chips and posting time appear in the window just before the job link.
    const window = html.slice(Math.max(0, pos - 3000), pos);
    const locMatches = window.match(LOCATION_RE) || [];
    const location =
      Array.from(new Set(locMatches.map((l) => l.trim()))).join(" / ") || "Unknown";
    const postedMatch = window.match(POSTED_RE);
    const posted = postedMatch ? postedMatch[1] : null;

    jobs.push({
      id,
      title,
      location,
      posted,
      url: `https://www.google.com/about/careers/applications/jobs/results/${id}`,
    });
  }

  return jobs;
}
