/**
 * Aegis Site X-ray - Background WebExtension Service
 * Passively observes response headers on main-frame navigations to audit security posture.
 *
 * PRIVACY DESIGN (Privacy Class P1):
 *   - Header VALUES (including full Set-Cookie strings, CSP policies, cookie
 *     names) are NEVER stored or logged. They are read transiently to derive
 *     booleans/counts and then discarded.
 *   - The stored posture record per tab contains ONLY: tabId, origin
 *     (scheme://host[:port]), isHttps, statusCode, derived boolean flags,
 *     cookie-flag counters, and a timestamp. No full URLs, no header values,
 *     no cookie names.
 *   - The only persisted data (browser.storage.local) is the enabled flag
 *     (local configuration). Posture records stay in memory and are dropped
 *     on restart and on tab close.
 *   - The "tabs" permission is NOT requested: tab lifecycle events
 *     (tabs.onRemoved) work without it, and tab URLs are not needed (the
 *     webRequest event supplies the URL transiently).
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
 * Derive a privacy-safe posture record from raw response headers.
 * Only booleans, counters, and the origin are produced. Header values and
 * cookie names never enter the returned object.
 * @param {string} url - response URL (transient; only origin is kept)
 * @param {Array<{name,value}>} responseHeaders
 * @param {number} statusCode
 * @returns {Object|null} sanitized posture record
 */
function derivePosture(url, responseHeaders, statusCode) {
  let origin = "";
  try {
    origin = new URL(url).origin;
  } catch (e) {
    return null;
  }

  const { headers: h, cookies } = normalizeHeaders(responseHeaders);
  const isHttps = url.toLowerCase().startsWith("https://");

  const csp = h["content-security-policy"] || "";
  let cookieSecureMissing = 0;
  let cookieHttpOnlyMissing = 0;
  let cookieSameSiteMissing = 0;
  for (const c of cookies) {
    const flags = c.toLowerCase();
    if (isHttps && !flags.includes("secure")) cookieSecureMissing++;
    if (!flags.includes("httponly")) cookieHttpOnlyMissing++;
    if (!flags.includes("samesite")) cookieSameSiteMissing++;
  }

  return {
    tabScoped: true,
    origin: origin,
    isHttps: isHttps,
    statusCode: statusCode,
    hasHSTS: isHttps && "strict-transport-security" in h,
    hasCSP: "content-security-policy" in h,
    cspAllowsUnsafeInlineOrEval: csp.toLowerCase().includes("unsafe-inline") ||
      csp.toLowerCase().includes("unsafe-eval"),
    hasClickjackingProtection: "x-frame-options" in h ||
      csp.toLowerCase().includes("frame-ancestors"),
    hasNosniff: (h["x-content-type-options"] || "").toLowerCase() === "nosniff",
    hasReferrerPolicy: "referrer-policy" in h,
    serverVersionDisclosed: Boolean(h["server"]) && /\d+\.\d+/.test(h["server"]),
    cookieCount: cookies.length,
    cookieSecureMissing: cookieSecureMissing,
    cookieHttpOnlyMissing: cookieHttpOnlyMissing,
    cookieSameSiteMissing: cookieSameSiteMissing,
    timestamp: Date.now()
  };
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

  const posture = derivePosture(details.url, details.responseHeaders || [], details.statusCode);
  if (!posture) return;

  if (details.tabId && details.tabId > 0) {
    tabPostures.set(details.tabId, posture);
  }
  lastAudit = posture;
}

if (typeof browser !== "undefined" && browser.webRequest && browser.webRequest.onHeadersReceived) {
  browser.webRequest.onHeadersReceived.addListener(
    handleHeadersReceived,
    { urls: ["<all_urls>"], types: ["main_frame"] },
    ["responseHeaders"]
  );
}

// Clean up tab posture cache on tab closure (no "tabs" permission needed)
if (typeof browser !== "undefined" && browser.tabs && browser.tabs.onRemoved) {
  browser.tabs.onRemoved.addListener(tabId => {
    tabPostures.delete(tabId);
  });
}

// Aegis cross-module sender allowlist: only Aegis built-in extension IDs may
// send external messages to this module (defense in depth on top of
// externally_connectable in the manifest).
const AEGIS_MODULE_IDS = new Set([
  "command-palette@aegis.local",
  "session-sweeper@aegis.local",
  "site-xray@aegis.local",
  "link-cleaner@aegis.local",
  "download-inspector@aegis.local"
]);

function handleMessage(msg, sender, sendResponse) {
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
      posture: posture  // sanitized record: booleans/counts/origin only
    });
    return true;
  }

  if (msg.type === "AUDIT_HEADERS") {
    if (!isEnabled) {
      sendResponse({ enabled: false, findings: [], status: "kill_switch_active" });
      return true;
    }
    // Transient on-demand analysis: findings are returned to the requester
    // and are NOT stored or logged by this module.
    const isHttps = Boolean(msg.isHttps);
    const findings = xrayHeaders(msg.headers, isHttps);
    sendResponse({
      enabled: true,
      findings: findings
    });
    return true;
  }
}

// Internal messages (own pages / content scripts)
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener(handleMessage);
}

// External messages from other Aegis modules: sender.id allowlist enforced.
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessageExternal) {
  browser.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
    if (!sender || !AEGIS_MODULE_IDS.has(sender.id)) {
      // Unknown/rogue sender: ignore entirely (fail closed).
      return;
    }
    return handleMessage(msg, sender, sendResponse);
  });
}
