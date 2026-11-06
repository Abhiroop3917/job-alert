// appleParser.js — extract jobs from Apple Jobs search results HTML.
//
// Apple embeds all search results server-side inside:
//   window.__staticRouterHydrationData = JSON.parse("...");
// The inner string is a JSON-escaped blob. We match fields directly with
// regex on the raw HTML rather than trying to unescape the full blob, since
// service workers have no DOMParser and the blob is large.
//
// Field order within each serialized job object (verified):
//   positionId → postingTitle → transformedPostingTitle → locations[].name + countryID
//
// Pagination: append &page=N — handled by the shared fetchAllPages() in background.js.

// In the raw HTML, JSON is escaped: " → \" and \ → \\
// So regex patterns use \\" to match \" in the string.
const POS_ID_RE   = /\\"positionId\\":\\"(\d+)\\"/g;
const TITLE_RE    = /\\"postingTitle\\":\\"([^"\\\\]+)\\"/;
const SLUG_RE     = /\\"transformedPostingTitle\\":\\"([^"\\\\]+)\\"/;
const LOC_NAME_RE = /\\"name\\":\\"([^"\\\\]+)\\",\\"countryID\\":\\"iso-country-IND\\"/g;

function unescapeUnicode(s) {
  return s.replace(/\\u([0-9a-fA-F]{4})/g, (_, h) => String.fromCharCode(parseInt(h, 16)));
}

export function parseAppleJobs(html) {
  const jobs = [];
  const seen = new Set();
  const posMatches = [...html.matchAll(POS_ID_RE)];

  for (let i = 0; i < posMatches.length; i++) {
    const id = posMatches[i][1];
    if (seen.has(id)) continue;
    seen.add(id);

    // Slice a chunk between this positionId and the next one to scope the search.
    const start = posMatches[i].index;
    const end   = posMatches[i + 1] ? posMatches[i + 1].index : start + 4000;
    const chunk = html.slice(start, end);

    const titleMatch = chunk.match(TITLE_RE);
    if (!titleMatch) continue;

    const slugMatch = chunk.match(SLUG_RE);
    const locMatches = [...chunk.matchAll(LOC_NAME_RE)];

    const title    = unescapeUnicode(titleMatch[1]);
    const slug     = slugMatch ? slugMatch[1] : String(id);
    const cities   = [...new Set(locMatches.map(m => m[1]))];
    const location = cities.length > 0 ? cities.join(' / ') + ', India' : 'India';

    jobs.push({
      id:       `apple-${id}`,
      title,
      location,
      url:      `https://jobs.apple.com/en-in/details/${id}/${slug}`,
      source:   'Apple',
    });
  }

  return jobs;
}
