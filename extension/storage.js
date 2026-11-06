// storage.js — read/write configuration, seen job IDs, and monitoring metadata.

const DEFAULT_SEARCH_URL =
  "https://www.google.com/about/careers/applications/jobs/results" +
  "?target_level=EARLY&employment_type=FULL_TIME&sort_by=date&location=India";

export const DEFAULTS = {
  config: {
    searchUrl: DEFAULT_SEARCH_URL,
    serviceNowUrl: "https://careers.servicenow.com/jobs/xml/?rss=true",
    appleUrl: "https://jobs.apple.com/en-in/search?sort=newest&location=india-INDC&key=Ai&lang=english-us-en_US",
    deloitteUrl: "https://southasiacareers.deloitte.com/search/?q=&title=Developer&sortColumn=referencedate&sortDirection=desc&searchby=location",
    ibmEnabled: true,
    microsoftEnabled: true,
    amazonUrl: "https://amazon.jobs/en/search.json?result_limit=100&sort=recent&category[]=software-development&category[]=data-science&category[]=fulfillment-warehouse-associate&category[]=machine-learning-science&category[]=systems-quality-security-engineering&category[]=operations-it-support-engineering&category[]=business-merchant-development&category[]=project-program-product-management-technical&category[]=business-intelligence&industry_experience=less_than_1_year&country=IND",
    // Empty keywords => match every job. Case-insensitive substring match on the title.
    keywords: [],
    // Empty locations => accept any location returned by the search.
    locations: [],
    checkIntervalMinutes: 1,
    paused: false,
  },
  meta: {
    initialized: false, // true once the first silent seed has stored existing jobs
    lastCheckTime: null,
    lastCheckStatus: "never", // "ok" | "error" | "never"
    lastError: null,
    detectedCount: 0,
    recentAlerts: [], // [{ id, title, location, url, time }]
  },
};

export async function getConfig() {
  const { config } = await chrome.storage.local.get("config");
  const merged = { ...DEFAULTS.config, ...(config || {}) };
  merged.keywords = [];
  merged.locations = [];
  return merged;
}

export async function setConfig(patch) {
  const current = await getConfig();
  const next = { ...current, ...patch };
  await chrome.storage.local.set({ config: next });
  return next;
}

export async function getMeta() {
  const { meta } = await chrome.storage.local.get("meta");
  return { ...DEFAULTS.meta, ...(meta || {}) };
}

export async function setMeta(patch) {
  const current = await getMeta();
  const next = { ...current, ...patch };
  await chrome.storage.local.set({ meta: next });
  return next;
}

export async function getSeenIds() {
  const { seenIds } = await chrome.storage.local.get("seenIds");
  return new Set(seenIds || []);
}

export async function addSeenIds(ids) {
  const seen = await getSeenIds();
  for (const id of ids) seen.add(id);
  // Keep the list bounded so storage does not grow without limit.
  const arr = Array.from(seen).slice(-2000);
  await chrome.storage.local.set({ seenIds: arr });
}

export async function recordAlerts(jobs) {
  const meta = await getMeta();
  const recent = jobs
    .map((j) => ({ id: j.id, title: j.title, location: j.location, url: j.url, posted: j.posted || null, time: Date.now() }))
    .concat(meta.recentAlerts)
    .slice(0, 20);
  await setMeta({
    detectedCount: meta.detectedCount + jobs.length,
    recentAlerts: recent,
  });
}
