/**
 * Aegis Download Inspector - WebExtension Background Service
 * Intercepts downloads, evaluates filename/metadata signatures, and records audit flags.
 *
 * NOTE ON PERMISSIONS & SCOPE:
 * In the live WebExtension environment, downloads.onCreated only provides metadata
 * (downloadItem.id, url, filename, mime, fileSize). Without broad host permissions (<all_urls>)
 * and native file access, WebExtensions CANNOT inspect raw bytes or stream payloads.
 * Therefore, live hooks perform metadata/filename analysis (double extensions, RTLO, risky extensions).
 * True byte/magic inspection requires a privileged native helper or Gecko engine patch (SPIKE-007).
 * Flagged items are logged and optionally paused, NOT quarantined to an isolated sandbox.
 */

let isEnabled = true;
const flagLog = [];
const stats = {
  totalInspected: 0,
  flaggedCount: 0
};

// Load saved configuration from local storage
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get(["download_inspector_enabled", "download_flag_log"]).then(res => {
    if (typeof res.download_inspector_enabled === "boolean") {
      isEnabled = res.download_inspector_enabled;
    }
    if (Array.isArray(res.download_flag_log)) {
      flagLog.push(...res.download_flag_log);
    }
  }).catch(() => {
    // Fail safe to default enabled
  });
}

/**
 * Handle new download events (metadata-only in WebExtension sandbox)
 */
async function handleDownloadCreated(downloadItem) {
  if (!isEnabled || !downloadItem) return;

  stats.totalInspected++;
  const filename = downloadItem.filename || downloadItem.url || "";

  // Perform immediate metadata/filename inspection (0 bytes available in WebExtension hook)
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

    flagLog.push(entry);

    if (browser.storage && browser.storage.local) {
      browser.storage.local.set({ "download_flag_log": flagLog.slice(-50) });
    }

    // Flagged download: attempt pause if high risk
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
        flagLog: [...flagLog]
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
