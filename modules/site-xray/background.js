/**
 * Aegis Site X-ray - Background WebExtension Service
 * Passively observes response headers on main-frame navigations to audit security posture.
 */

let isEnabled = true;
const tabPostures = new Map();
let lastAudit = null;

// Load saved configuration from local storage
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get(["site_xray_enabled"]).then(res => {
    if (typeof res.site_xray_enabled === "boolean") {
      isEnabled = res.site_xray_enabled;
    }
  }).catch(() => {
    // Fail safe to default enabled state
  });

  if (browser.storage.onChanged) {
    browser.storage.onChanged.addListener((changes, area) => {
      if (area === "local" && changes.site_xray_enabled) {
        isEnabled = Boolean(changes.site_xray_enabled.newValue);
      }
    });
  }
}

/**
 * Passive webRequest.onHeadersReceived listener (non-blocking).
 */
function handleHeadersReceived(details) {
  if (!isEnabled) return;
  if (!details || !details.url) return;
  if (details.url.startsWith("moz-extension://") || details.url.startsWith("about:") || details.url.startsWith("data:")) {
    return;
  }

  const isHttps = details.url.toLowerCase().startsWith("https://");
  const findings = xrayHeaders(details.responseHeaders, isHttps);

  const report = {
    tabId: details.tabId,
    url: details.url,
    isHttps: isHttps,
    statusCode: details.statusCode,
    findings: findings,
    timestamp: Date.now()
  };

  if (details.tabId && details.tabId > 0) {
    tabPostures.set(details.tabId, report);
  }
  lastAudit = report;
}

if (typeof browser !== "undefined" && browser.webRequest && browser.webRequest.onHeadersReceived) {
  browser.webRequest.onHeadersReceived.addListener(
    handleHeadersReceived,
    { urls: ["<all_urls>"], types: ["main_frame"] },
    ["responseHeaders"]
  );
}

// Clean up tab posture cache on tab closure
if (typeof browser !== "undefined" && browser.tabs && browser.tabs.onRemoved) {
  browser.tabs.onRemoved.addListener(tabId => {
    tabPostures.delete(tabId);
  });
}

// Runtime message dispatcher
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || typeof msg !== "object") return;

    if (msg.type === "GET_STATUS") {
      sendResponse({
        enabled: isEnabled,
        cachedTabsCount: tabPostures.size,
        hasLastAudit: lastAudit !== null
      });
      return true;
    }

    if (msg.type === "SET_ENABLED") {
      isEnabled = Boolean(msg.enabled);
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "site_xray_enabled": isEnabled });
      }
      sendResponse({ success: true, enabled: isEnabled });
      return true;
    }

    if (msg.type === "GET_TAB_POSTURE") {
      if (!isEnabled) {
        sendResponse({ enabled: false, posture: null, status: "kill_switch_active" });
        return true;
      }
      const targetTab = msg.tabId !== undefined ? msg.tabId : (sender.tab ? sender.tab.id : null);
      const posture = (targetTab && tabPostures.has(targetTab))
        ? tabPostures.get(targetTab)
        : lastAudit;

      sendResponse({
        enabled: true,
        posture: posture
      });
      return true;
    }

    if (msg.type === "AUDIT_HEADERS") {
      if (!isEnabled) {
        sendResponse({ enabled: false, findings: [], status: "kill_switch_active" });
        return true;
      }
      const isHttps = Boolean(msg.isHttps);
      const findings = xrayHeaders(msg.headers, isHttps);
      sendResponse({
        enabled: true,
        findings: findings
      });
      return true;
    }
  });
}
