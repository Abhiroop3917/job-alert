// background.js — monitoring orchestration: schedule, fetch, parse, filter, detect, notify.

import { getConfig, setConfig, getMeta, setMeta, getSeenIds, addSeenIds, recordAlerts } from "./storage.js";
import { parseJobs } from "./jobParser.js";
import { parseServiceNowJobs } from "./serviceNowParser.js";
import { parseAppleJobs } from "./appleParser.js";
import { parseDeloitteJobs } from "./deloitteParser.js";
import { parseIBMJobs } from "./ibmParser.js";
import { parseAmazonJobs } from "./amazonParser.js";
import { parseMicrosoftJobs } from "./microsoftParser.js";
import { parseMetaJobs, parseMetaJobDetail } from "./metaParser.js";
import { applyFilters } from "./filters.js";
import { notifyNewJob, registerNotificationClickHandler } from "./notifications.js";
import { isEntryLevelExperience } from "./experienceFilter.js";

const ALARM_NAME = "gc-check";

registerNotificationClickHandler();

chrome.runtime.onInstalled.addListener(initialize);
chrome.runtime.onStartup.addListener(initialize);

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) runCheck("alarm");
});

// Messages from the popup.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    if (msg.type === "checkNow") {
      const result = await runCheck("manual");
      sendResponse(result);
    } else if (msg.type === "getStatus") {
      sendResponse({ config: await getConfig(), meta: await getMeta() });
    } else if (msg.type === "setPaused") {
      await setConfig({ paused: msg.paused });
      await scheduleAlarm();
      sendResponse({ ok: true });
    } else if (msg.type === "saveConfig") {
      await setConfig(msg.config);
      await scheduleAlarm();
      sendResponse({ ok: true });
    } else if (msg.type === "testNotify") {
      notifyNewJob({
        id: "test",
        title: "Software Engineer III, Google Cloud",
        location: "Bengaluru, Karnataka, India",
        url: "https://www.google.com/about/careers/applications/jobs/results?target_level=EARLY&employment_type=FULL_TIME&sort_by=date&location=India",
      });
      sendResponse({ ok: true });
    } else if (msg.type === "reset") {
      await chrome.storage.local.remove(["meta", "seenIds"]);
      await initialize();
      sendResponse({ ok: true });
    }
  })();
  return true; // keep the message channel open for the async response
});

async function scheduleAlarm() {
  const config = await getConfig();
  await chrome.alarms.clear(ALARM_NAME);
  if (!config.paused) {
    const period = Math.max(1, config.checkIntervalMinutes || 1);
    // Fire the first check after one period, not instantly — avoids racing the
    // install-time seed.
    chrome.alarms.create(ALARM_NAME, { periodInMinutes: period, delayInMinutes: period });
  }
}

// Silent first-run seeding: store the IDs of all jobs that currently match so we
// never alert for postings that existed before the user installed the extension.
// Only marks initialized when the fetch actually returned jobs, so a transient
// empty response can't cause a later flood.
async function seed() {
  try {
    const config = await getConfig();
    const matching = applyFilters(await fetchAllJobs(config), config);
    if (matching.length === 0) {
      await setMeta({ lastCheckTime: Date.now(), lastCheckStatus: "ok", lastError: null });
      return { ok: true, seeded: 0, note: "no jobs returned; not marking initialized" };
    }
    await addSeenIds(matching.map((j) => j.id));
    await setMeta({ initialized: true, lastCheckTime: Date.now(), lastCheckStatus: "ok", lastError: null });
    await updateBadge(0);
    return { ok: true, firstRun: true, seeded: matching.length };
  } catch (err) {
    await setMeta({ lastCheckTime: Date.now(), lastCheckStatus: "error", lastError: String(err.message || err) });
    await updateBadge("!", "#d93025");
    return { ok: false, error: String(err.message || err) };
  }
}

async function initialize() {
  const meta = await getMeta();
  if (!meta.initialized) await seed();
  await scheduleAlarm();
}

async function fetchResultsHtml(url, attempt = 1, timeoutMs = 30_000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      credentials: "omit",
      headers: { "Accept-Language": "en-US,en;q=0.9" },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.text();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") throw new Error(`Timeout fetching ${new URL(url).hostname}`);
    if (attempt < 3) {
      await new Promise((r) => setTimeout(r, attempt * 1500));
      return fetchResultsHtml(url, attempt + 1, timeoutMs);
    }
    throw err;
  }
}

// Fetch all paginated result pages using the given parser, return deduplicated jobs.
// opts.pageParam  — URL parameter name (default "page")
// opts.pageStart  — value for the first page (default 1)
// opts.pageStep   — increment per page (default 1)
// opts.timeoutMs  — per-request timeout (default 30 000 ms)
async function fetchAllPages(baseUrl, parserFn, opts = {}) {
  const { timeoutMs = 30_000, pageParam = "page", pageStart = 1, pageStep = 1 } = opts;
  const base = baseUrl
    .replace(new RegExp(`[&?]${pageParam}=\\d+`, "g"), "")
    .replace(/[?&]$/, "");
  const sep = base.includes("?") ? "&" : "?";
  const allJobs = [];
  const seenIds = new Set();
  for (let i = 0, pageVal = pageStart; i < 10; i++, pageVal += pageStep) {
    const html = await fetchResultsHtml(`${base}${sep}${pageParam}=${pageVal}`, 1, timeoutMs);
    const jobs = parserFn(html);
    if (jobs.length === 0) break;
    for (const job of jobs) {
      if (!seenIds.has(job.id)) {
        seenIds.add(job.id);
        allJobs.push(job);
      }
    }
  }
  return allJobs;
}

// Single-URL fetch (no pagination) — for sources like ServiceNow RSS that
// return everything in one response.
async function fetchSingle(url, parserFn, timeoutMs = 30_000) {
  const text = await fetchResultsHtml(url, 1, timeoutMs);
  return parserFn(text);
}

// IBM uses a POST JSON API (Elasticsearch). Filters for Entry Level + India are
// baked into the request body; pagination uses the Elasticsearch `from` param.
const IBM_API = "https://www-api.ibm.com/search/api/v2";
const IBM_PAGE_SIZE = 30;

async function fetchIBMJobs(timeoutMs = 30_000) {
  const allJobs = [];
  const seenIds = new Set();

  for (let from = 0; from < 300; from += IBM_PAGE_SIZE) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let data;
    try {
      const res = await fetch(IBM_API, {
        method: "POST",
        credentials: "omit",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({
          appId: "careers",
          scopes: ["careers2"],
          query: { bool: { must: [] } },
          post_filter: {
            bool: {
              must: [
                { term: { field_keyword_18: "Entry Level" } },
                { term: { field_keyword_05: "India" } },
              ],
            },
          },
          size: IBM_PAGE_SIZE,
          from,
          sort: [{ _score: "desc" }, { pageviews: "desc" }],
          lang: "zz",
          localeSelector: {},
          _source: ["_id", "title", "url", "field_keyword_18", "field_keyword_19"],
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`IBM API HTTP ${res.status}`);
      data = await res.json();
    } catch (err) {
      clearTimeout(timer);
      throw err;
    }

    const jobs = parseIBMJobs(data);
    if (jobs.length === 0) break;
    for (const job of jobs) {
      if (!seenIds.has(job.id)) { seenIds.add(job.id); allJobs.push(job); }
    }
    if (jobs.length < IBM_PAGE_SIZE) break;
  }

  return allJobs;
}

// Amazon Jobs uses a JSON API with offset-based pagination.
async function fetchAmazonJobs(baseUrl, timeoutMs = 30_000) {
  const base = baseUrl.replace(/[?&]offset=\d+/, "").replace(/[?&]$/, "");
  const sep  = base.includes("?") ? "&" : "?";
  const allJobs = [], seenIds = new Set();

  for (let offset = 0; offset < 1000; offset += 100) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${base}${sep}offset=${offset}`, { signal: controller.signal });
      if (!res.ok) break;
      const data = await res.json();
      const jobs = parseAmazonJobs(data);
      if (!jobs.length) break;
      for (const job of jobs) {
        if (!seenIds.has(job.id)) { seenIds.add(job.id); allJobs.push(job); }
      }
      if (jobs.length < 100) break;
    } finally {
      clearTimeout(timer);
    }
  }
  return allJobs;
}

// Microsoft Careers uses the Eightfold AI platform.
// Step 1: fetch the careers page to get a CSRF token.
// Step 2: call the JSON search API with that token.
const MICROSOFT_PAGE_URL = "https://apply.careers.microsoft.com/careers?start=0&location=India&sort_by=recent&filter_include_remote=1&filter_seniority=Entry";
const MICROSOFT_API_URL  = "https://apply.careers.microsoft.com/api/pcsx/search";

async function fetchMicrosoftJobs(timeoutMs = 30_000) {
  // Step 1: get CSRF token
  const pageRes = await fetch(MICROSOFT_PAGE_URL, { credentials: "include" });
  if (!pageRes.ok) throw new Error(`Microsoft page HTTP ${pageRes.status}`);
  const csrfToken = pageRes.headers.get("x-csrf-token");
  if (!csrfToken) throw new Error("Microsoft: CSRF token missing");

  // Step 2: call the search API
  const url = new URL(MICROSOFT_API_URL);
  const params = {
    domain: "microsoft.com", query: "", location: "India",
    start: "0", num_rec: "100", sort_by: "recent",
    filter_include_remote: "1", filter_seniority: "Entry",
  };
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const apiRes = await fetch(url.toString(), {
      credentials: "include",
      headers: {
        "Accept": "application/json, text/plain, */*",
        "X-CSRF-Token": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": MICROSOFT_PAGE_URL,
      },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!apiRes.ok) throw new Error(`Microsoft API HTTP ${apiRes.status}`);
    return parseMicrosoftJobs(await apiRes.json());
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

// Apple detail pages embed minimumQualifications inside the hydration JSON blob.
const APPLE_MIN_Q_RE = /"minimumQualifications":"((?:[^"\\]|\\[\s\S])*)"/;

// Fetch Apple jobs across pages, then filter each by minimumQualifications on the detail page.
async function fetchAppleJobs(baseUrl) {
  const allJobs = await fetchAllPages(baseUrl, parseAppleJobs);
  const checks = await Promise.all(
    allJobs.map(async (job) => {
      try {
        const detailHtml = await fetchResultsHtml(job.url);
        const mq = detailHtml.match(APPLE_MIN_Q_RE);
        let qualifications = "";
        if (mq) qualifications = mq[1].replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\\\/g, "\\");
        return isEntryLevelExperience(qualifications) ? job : null;
      } catch (_) {
        return job; // include on fetch error
      }
    })
  );
  return checks.filter(Boolean);
}

// Fetch Deloitte jobs across pages, then filter each by stripping the detail page and checking years.
async function fetchDeloitteJobs(baseUrl) {  const allJobs = await fetchAllPages(baseUrl, parseDeloitteJobs, { pageParam: "startrow", pageStart: 0, pageStep: 25 });
  const checks = await Promise.all(
    allJobs.map(async (job) => {
      try {
        const detailHtml = await fetchResultsHtml(job.url);
        const description = detailHtml.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
        return isEntryLevelExperience(description) ? job : null;
      } catch (_) {
        return job; // include on fetch error
      }
    })
  );
  return checks.filter(Boolean);
}

// Meta Careers: 2-step flow — extract session tokens from page HTML, POST to GraphQL,
// then filter each job by the qualifications text on its detail page.
const META_PAGE_URL    = "https://www.metacareers.com/jobsearch/?sort_by_new=true&offices[0]=Mumbai%2C%20India&offices[1]=Gurgaon%2C%20India&offices[2]=Bangalore%2C%20India&offices[3]=Hyderabad%2C%20India&offices[4]=New%20Delhi%2C%20India&roles[0]=Full%20time%20employment";
const META_GRAPHQL_URL = "https://www.metacareers.com/graphql";
const META_DOC_ID      = "27129360303422352";
const META_VARIABLES   = {
  search_input: {
    q: null, divisions: [],
    offices: ["Mumbai, India", "Gurgaon, India", "Bangalore, India", "Hyderabad, India", "New Delhi, India"],
    roles: ["Full time employment"],
    leadership_levels: [], saved_jobs: [], saved_searches: [], sub_teams: [], teams: [],
    is_leadership: false, is_remote_only: false, sort_by_new: true, results_per_page: null,
  },
  viewasUserID: null,
  isLoggedIn: false,
};

async function fetchMetaJobs() {
  // Step 1: load the page with a browser-like Accept header to get the token blob
  const ctrl1 = new AbortController();
  const t1 = setTimeout(() => ctrl1.abort(), 30_000);
  let pageHtml;
  try {
    const res = await fetch(META_PAGE_URL, {
      credentials: "omit",
      headers: {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
      },
      signal: ctrl1.signal,
    });
    clearTimeout(t1);
    if (!res.ok) throw new Error(`Meta page HTTP ${res.status}`);
    pageHtml = await res.text();
  } catch (err) {
    clearTimeout(t1);
    throw err;
  }

  const lsdM    = pageHtml.match(/"LSD",\[\],\{"token":"([^"]+)"/);
  const spinRM  = pageHtml.match(/"__spin_r":(\d+)/);
  const spinTM  = pageHtml.match(/"__spin_t":(\d+)/);
  if (!lsdM || !spinRM || !spinTM) throw new Error("Meta: could not extract session tokens");

  const lsd    = lsdM[1];
  const spinR  = spinRM[1];
  const spinT  = spinTM[1];

  // Step 2: POST to the Meta GraphQL search API
  const body = new URLSearchParams({
    av: "0", __user: "0", __a: "1",
    lsd, __rev: spinR, __spin_r: spinR, __spin_b: "trunk", __spin_t: spinT,
    fb_api_caller_class: "RelayModern",
    fb_api_req_friendly_name: "CareersJobSearchResultsV2DataQuery",
    server_timestamps: "true",
    variables: JSON.stringify(META_VARIABLES),
    doc_id: META_DOC_ID,
  });

  const ctrl2 = new AbortController();
  const t2 = setTimeout(() => ctrl2.abort(), 30_000);
  let data;
  try {
    const res = await fetch(META_GRAPHQL_URL, {
      method: "POST",
      credentials: "omit",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.metacareers.com",
        "Referer": "https://www.metacareers.com/jobsearch/",
      },
      body: body.toString(),
      signal: ctrl2.signal,
    });
    clearTimeout(t2);
    if (!res.ok) throw new Error(`Meta GraphQL HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    clearTimeout(t2);
    throw err;
  }

  const allJobs = parseMetaJobs(data);

  // Step 3: filter each job by the qualifications on its detail page, in parallel
  const checks = await Promise.all(
    allJobs.map(async (job) => {
      try {
        const detailHtml = await fetchResultsHtml(job.url);
        const qualifications = parseMetaJobDetail(detailHtml);
        return isEntryLevelExperience(qualifications) ? job : null;
      } catch (_) {
        return job; // include on fetch error
      }
    })
  );
  return checks.filter(Boolean);
}

// Fetch all jobs from every enabled source in parallel.
// Uses allSettled so a slow/failing source never blocks or breaks the others.
async function fetchAllJobs(config) {
  const sources = [fetchAllPages(config.searchUrl, parseJobs)];
  if (config.serviceNowUrl) sources.push(fetchSingle(config.serviceNowUrl, parseServiceNowJobs, 120_000));
  if (config.appleUrl)      sources.push(fetchAppleJobs(config.appleUrl));
  if (config.deloitteUrl)  sources.push(fetchDeloitteJobs(config.deloitteUrl));
  if (config.ibmEnabled)    sources.push(fetchIBMJobs());
  if (config.amazonUrl)     sources.push(fetchAmazonJobs(config.amazonUrl));
  if (config.microsoftEnabled !== false) sources.push(fetchMicrosoftJobs());
  if (config.metaEnabled !== false) sources.push(fetchMetaJobs());
  const results = await Promise.allSettled(sources);
  return results
    .filter((r) => r.status === "fulfilled")
    .flatMap((r) => r.value);
}

async function runCheck(trigger) {
  const config = await getConfig();
  if (config.paused && trigger === "alarm") {
    return { skipped: true };
  }

  try {
    const matching = applyFilters(await fetchAllJobs(config), config);

    // Not yet seeded: store existing jobs silently, no alerts.
    const meta = await getMeta();
    if (!meta.initialized) {
      return await seed();
    }

    const seen = await getSeenIds();
    const newJobs = matching.filter((j) => !seen.has(j.id));

    if (newJobs.length > 0) {
      for (const job of newJobs) notifyNewJob(job);
      await addSeenIds(newJobs.map((j) => j.id));
      await recordAlerts(newJobs);
    }

    // Reflect current state on the badge: a count when there are new jobs,
    // and — importantly — clear any leftover error "!" once a check succeeds.
    await updateBadge(newJobs.length);
    await setMeta({ lastCheckTime: Date.now(), lastCheckStatus: "ok", lastError: null });
    return { ok: true, newCount: newJobs.length, totalMatching: matching.length };
  } catch (err) {
    await setMeta({
      lastCheckTime: Date.now(),
      lastCheckStatus: "error",
      lastError: String(err.message || err),
    });
    await updateBadge("!", "#d93025");
    return { ok: false, error: String(err.message || err) };
  }
}

async function updateBadge(text, color = "#1a73e8") {
  const value = text === 0 || text === "" ? "" : String(text);
  await chrome.action.setBadgeText({ text: value });
  if (value) await chrome.action.setBadgeBackgroundColor({ color });
}

// Ensure an alarm exists whenever the worker spins up.
scheduleAlarm();
