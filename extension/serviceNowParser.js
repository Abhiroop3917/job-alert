// serviceNowParser.js — parses ServiceNow Jobs RSS XML feed.
//
// The HTML search page is JS-rendered (only 1 job server-side), so we use the
// RSS feed at /jobs/xml/?rss=true instead. It returns all global jobs as XML;
// we filter client-side for country=India since the URL params are ignored.

import { isEntryLevelExperience } from "./experienceFilter.js";

const JOB_BLOCK_RE   = /<job>([\s\S]*?)<\/job>/g;
const TITLE_RE       = /<title><!\[CDATA\[([\s\S]*?)\]\]><\/title>/i;
const ID_RE          = /<apijobid><!\[CDATA\[([\s\S]*?)\]\]><\/apijobid>/i;
const URL_RE         = /<url><!\[CDATA\[([\s\S]*?)\]\]><\/url>/i;
const CITY_RE        = /<city><!\[CDATA\[([\s\S]*?)\]\]><\/city>/i;
const COUNTRY_RE     = /<country><!\[CDATA\[([\s\S]*?)\]\]><\/country>/i;
const DESCRIPTION_RE = /<description><!\[CDATA\[([\s\S]*?)\]\]><\/description>/i;

export function parseServiceNowJobs(xml) {
  const jobs = [];
  const seen = new Set();

  for (const m of xml.matchAll(JOB_BLOCK_RE)) {
    const block = m[1];

    const countryMatch = block.match(COUNTRY_RE);
    if (!countryMatch || countryMatch[1].trim() !== "India") continue;

    const idMatch = block.match(ID_RE);
    if (!idMatch) continue;
    const id = idMatch[1].trim();
    if (seen.has(id)) continue;
    seen.add(id);

    const titleMatch = block.match(TITLE_RE);
    if (!titleMatch) continue;

    const descMatch = block.match(DESCRIPTION_RE);
    const description = descMatch ? descMatch[1] : "";
    if (!isEntryLevelExperience(description)) continue;

    const urlMatch  = block.match(URL_RE);
    const cityMatch = block.match(CITY_RE);
    const city = cityMatch ? cityMatch[1].trim() : "";

    jobs.push({
      id: `sn-${id}`,
      title: titleMatch[1].trim(),
      location: city ? `${city}, India` : "India",
      url: urlMatch ? urlMatch[1].trim() : `https://careers.servicenow.com/jobs/${id}/`,
      source: "ServiceNow",
    });
  }

  return jobs;
}
