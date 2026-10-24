/**
 * Aegis Download Inspector - WebExtension Background Service
 * Intercepts downloads, evaluates signatures and filenames, and records quarantine events.
 * Implements persistent kill-switch and audit logging.
 */

let isEnabled = true;
const quarantineLog = [];
const stats = {
  totalInspected: 0,
  flaggedCount: 0
};

// Load saved configuration from local storage
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get(["download_inspector_enabled", "download_quarantine_log"]).then(res => {
    if (typeof res.download_inspector_enabled === "boolean") {
      isEnabled = res.download_inspector_enabled;
    }
    if (Array.isArray(res.download_quarantine_log)) {
      quarantineLog.push(...res.download_quarantine_log);
    }
  }).catch(() => {
    // Fail safe to default enabled
  });
}

/**
 * Handle new download events
 */
async function handleDownloadCreated(downloadItem) {
  if (!isEnabled || !downloadItem) return;

  stats.totalInspected++;
  const filename = downloadItem.filename || downloadItem.url || "";

  // Perform immediate metadata/filename inspection
  const report = await inspectDownload(filename, new Uint8Array(0));

  if (report.level === "high" || report.level === "medium") {
    stats.flaggedCount++;
    const entry = {
      id: downloadItem.id,
      url: downloadItem.url,
      filename: filename,
      level: report.level,
      flags: report.flags,
      timestamp: new Date().toISOString()
    };

    quarantineLog.push(entry);

    if (browser.storage && browser.storage.local) {
      browser.storage.local.set({ "download_quarantine_log": quarantineLog.slice(-50) });
    }

    // Emit event or warning (P1 local storage audit)
    if (report.level === "high" && browser.downloads && browser.downloads.pause) {
      try {
        await browser.downloads.pause(downloadItem.id);
      } catch (e) {
        // May already be paused or completed
      }
    }
  }
}

if (typeof browser !== "undefined" && browser.downloads && browser.downloads.onCreated) {
  browser.downloads.onCreated.addListener(handleDownloadCreated);
}

// Runtime message listener for inspection requests, tests, and kill-switch
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || typeof msg !== "object") return;

    if (msg.type === "GET_STATUS") {
      sendResponse({
        enabled: isEnabled,
        stats: { ...stats },
        quarantineLog: [...quarantineLog]
      });
      return true;
    }

    if (msg.type === "SET_ENABLED") {
      isEnabled = Boolean(msg.enabled);
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "download_inspector_enabled": isEnabled });
      }
      sendResponse({ success: true, enabled: isEnabled });
      return true;
    }

    if (msg.type === "INSPECT_FILE") {
      (async () => {
        const bytes = msg.bytes ? new Uint8Array(msg.bytes) : new Uint8Array(0);
        const report = await inspectDownload(msg.filename, bytes);
        sendResponse(report);
      })();
      return true; // Asynchronous response
    }
  });
}
