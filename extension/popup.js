// popup.js — renders status and wires up the controls.

const $ = (id) => document.getElementById(id);

function send(msg) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msg, resolve));
}

function fmtTime(ts) {
  if (!ts) return "never";
  const d = new Date(ts);
  const diff = Math.round((Date.now() - ts) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  return d.toLocaleString();
}

function toast(text) {
  $("toast").textContent = text;
  if (text) setTimeout(() => ($("toast").textContent = ""), 3000);
}

function render({ config, meta }) {
  const dot = $("statusDot");
  dot.className = "dot";
  if (config.paused) {
    dot.classList.add("paused");
    $("statusText").textContent = "Paused";
  } else if (meta.lastCheckStatus === "error") {
    dot.classList.add("error");
    $("statusText").textContent = "Error";
  } else {
    $("statusText").textContent = "Monitoring";
  }

  $("lastCheck").textContent = fmtTime(meta.lastCheckTime);
  $("detected").textContent = meta.detectedCount;
  $("togglePause").textContent = config.paused ? "Resume" : "Pause";

  if (meta.lastCheckStatus === "error" && meta.lastError) {
    $("errorRow").style.display = "flex";
    $("errorText").textContent = meta.lastError.slice(0, 40);
  } else {
    $("errorRow").style.display = "none";
  }

  // Recent alerts
  $("recentCount").textContent = meta.recentAlerts.length;
  $("recentList").innerHTML = meta.recentAlerts
    .map(
      (a) =>
        `<div class="alert"><a href="${a.url}" target="_blank">${escapeHtml(a.title)}</a><br>` +
        `<span class="muted">${escapeHtml(a.location)}` +
        (a.posted ? ` · <span title="Posted on Google Careers">posted ${escapeHtml(a.posted)}</span>` : ``) +
        ` · detected ${fmtTime(a.time)}</span></div>`
    )
    .join("");

  // Settings fields
  $("searchUrl").value = config.searchUrl;
  $("serviceNowUrl").value = config.serviceNowUrl || "";
  $("appleUrl").value = config.appleUrl || "";
  $("deloitteUrl").value = config.deloitteUrl || "";
  $("ibmEnabled").checked = config.ibmEnabled !== false;
  $("microsoftEnabled").checked = config.microsoftEnabled !== false;
  $("amazonUrl").value = config.amazonUrl || "";
  $("interval").value = config.checkIntervalMinutes || 1;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

async function refresh() {
  render(await send({ type: "getStatus" }));
}

$("checkNow").addEventListener("click", async () => {
  $("checkNow").disabled = true;
  $("checkNow").textContent = "Checking…";
  const r = await send({ type: "checkNow" });
  $("checkNow").disabled = false;
  $("checkNow").textContent = "Check now";
  if (r?.firstRun) toast(`Seeded ${r.seeded} existing jobs (no alerts).`);
  else if (r?.ok) toast(`Done — ${r.newCount} new of ${r.totalMatching} matching.`);
  else toast(`Failed: ${r?.error || "unknown error"}`);
  refresh();
});

$("togglePause").addEventListener("click", async () => {
  const { config } = await send({ type: "getStatus" });
  await send({ type: "setPaused", paused: !config.paused });
  refresh();
});

$("testAlert").addEventListener("click", async () => {
  await send({ type: "testNotify" });
  toast("Test notification sent — look top-right of your screen.");
});

$("reset").addEventListener("click", async () => {
  if (!confirm("Reset all data? Seen jobs, count, and alerts will be cleared.")) return;
  $("reset").disabled = true;
  $("reset").textContent = "Resetting…";
  await send({ type: "reset" });
  $("reset").disabled = false;
  $("reset").textContent = "Reset";
  toast("Reset done — extension will re-seed on next check.");
  refresh();
});

$("save").addEventListener("click", async () => {
  const parseList = (v) =>
    v.split(",").map((s) => s.trim()).filter(Boolean);
  await send({
    type: "saveConfig",
    config: {
      searchUrl: $("searchUrl").value.trim(),
      serviceNowUrl: $("serviceNowUrl").value.trim(),
      appleUrl: $("appleUrl").value.trim(),
      deloitteUrl: $("deloitteUrl").value.trim(),
      ibmEnabled: $("ibmEnabled").checked,
      microsoftEnabled: $("microsoftEnabled").checked,
      amazonUrl: $("amazonUrl").value.trim(),
      checkIntervalMinutes: Math.max(1, parseInt($("interval").value, 10) || 1),
    },
  });
  toast("Settings saved.");
  refresh();
});

refresh();
