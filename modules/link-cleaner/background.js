/**
 * Aegis Link Cleaner - WebExtension Background Service
 * Intercepts web navigation requests and redirects to cleaned URLs.
 * Implements persistent kill-switch and user keep-list.
 */

let isEnabled = true;
let keepList = [];
const stats = {
  cleanedRequests: 0,
  removedParamsTotal: 0
};

// Load saved configuration from local storage
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get(["link_cleaner_enabled", "link_cleaner_keep_list"]).then(res => {
    if (typeof res.link_cleaner_enabled === "boolean") {
      isEnabled = res.link_cleaner_enabled;
    }
    if (Array.isArray(res.link_cleaner_keep_list)) {
      keepList = res.link_cleaner_keep_list;
    }
  }).catch(() => {
    // Fail safe to default enabled state
  });
}

/**
 * webRequest.onBeforeRequest filter
 */
function handleBeforeRequest(details) {
  // Kill switch check
  if (!isEnabled) {
    return {};
  }

  // Only intercept main_frame and sub_frame HTTP/HTTPS navigations
  if (!details.url) {
    return {};
  }

  const result = cleanLink(details.url, keepList);
  if (result.removedParams && result.removedParams.length > 0) {
    stats.cleanedRequests++;
    stats.removedParamsTotal += result.removedParams.length;

    return {
      redirectUrl: result.cleanedUrl
    };
  }

  return {};
}

if (typeof browser !== "undefined" && browser.webRequest && browser.webRequest.onBeforeRequest) {
  browser.webRequest.onBeforeRequest.addListener(
    handleBeforeRequest,
    { urls: ["<all_urls>"], types: ["main_frame", "sub_frame"] },
    ["blocking"]
  );
}

// Runtime message dispatcher for status, tests, and configuration
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || typeof msg !== "object") return;

    if (msg.type === "GET_STATUS") {
      sendResponse({
        enabled: isEnabled,
        keepList: [...keepList],
        stats: { ...stats }
      });
      return true;
    }

    if (msg.type === "SET_ENABLED") {
      isEnabled = Boolean(msg.enabled);
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "link_cleaner_enabled": isEnabled });
      }
      sendResponse({ success: true, enabled: isEnabled });
      return true;
    }

    if (msg.type === "SET_KEEP_LIST") {
      keepList = (typeof msg.keepList === "object" && msg.keepList !== null) ? msg.keepList : [];
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "link_cleaner_keep_list": keepList });
      }
      sendResponse({ success: true, keepList: keepList });
      return true;
    }

    if (msg.type === "CLEAN_URL") {
      const res = cleanLink(msg.url, msg.keep || keepList);
      sendResponse(res);
      return true;
    }
  });
}
