// notifications.js — create desktop notifications and open the job on click.

// Maps a notification id to the job URL so a click can open the right page.
const pendingUrls = new Map();

export function notifyNewJob(job) {
  const notificationId = `gcjob-${job.id}`;
  pendingUrls.set(notificationId, job.url);
  const source = job.source || "Google Careers";

  chrome.notifications.create(notificationId, {
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: `New job — ${source}`,
    message: `${job.title}\n${job.location}`,
    priority: 2,
  });
}

// Registered once from background.js at startup.
export function registerNotificationClickHandler() {
  chrome.notifications.onClicked.addListener((notificationId) => {
    const url = pendingUrls.get(notificationId);
    if (url) {
      chrome.tabs.create({ url });
      pendingUrls.delete(notificationId);
    }
    chrome.notifications.clear(notificationId);
  });
}
