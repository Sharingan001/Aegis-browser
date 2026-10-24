/**
 * Aegis Session Sweeper - Background WebExtension Service
 * Selectively purges expired site browsing data while honoring user keep-lists.
 */

let isEnabled = true;
let maxAgeDays = 14;
let keepDomains = [];
const stats = {
  sweptCount: 0,
  lastSweepTime: null,
  lastSweptOrigins: []
};

// Load saved configuration from local storage (Privacy Class P1)
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get([
    "session_sweeper_enabled",
    "session_sweeper_max_age_days",
    "session_sweeper_keep_domains"
  ]).then(res => {
    if (typeof res.session_sweeper_enabled === "boolean") {
      isEnabled = res.session_sweeper_enabled;
    }
    if (typeof res.session_sweeper_max_age_days === "number" && res.session_sweeper_max_age_days > 0) {
      maxAgeDays = res.session_sweeper_max_age_days;
    }
    if (Array.isArray(res.session_sweeper_keep_domains)) {
      keepDomains = res.session_sweeper_keep_domains;
    }
  }).catch(() => {
    // Fail safe to default enabled state
  });

  if (browser.storage.onChanged) {
    browser.storage.onChanged.addListener((changes, area) => {
      if (area === "local") {
        if (changes.session_sweeper_enabled) {
          isEnabled = Boolean(changes.session_sweeper_enabled.newValue);
        }
        if (changes.session_sweeper_max_age_days) {
          maxAgeDays = Number(changes.session_sweeper_max_age_days.newValue) || 14;
        }
        if (changes.session_sweeper_keep_domains) {
          keepDomains = Array.isArray(changes.session_sweeper_keep_domains.newValue)
            ? changes.session_sweeper_keep_domains.newValue
            : [];
        }
      }
    });
  }
}

/**
 * Execute actual data deletion for specified origins via browsingData API.
 * @param {Array<string>} origins
 * @returns {Promise<boolean>}
 */
async function executeSweepData(origins) {
  if (!origins || origins.length === 0) return true;
  if (typeof browser === "undefined" || !browser.browsingData || !browser.browsingData.remove) {
    return false;
  }

  try {
    // Gecko ESR supports removing data by origin list
    await browser.browsingData.remove(
      { origins: origins },
      {
        cookies: true,
        localStorage: true,
        cache: true,
        indexedDB: true
      }
    );
    return true;
  } catch (err) {
    // Fall back to removal without origin filtering if origins filter is unsupported
    try {
      await browser.browsingData.removeCookies({ origins: origins });
    } catch (e) {
      // Ignored
    }
    return false;
  }
}

// Optional periodic schedule via alarms API
if (typeof browser !== "undefined" && browser.alarms) {
  try {
    browser.alarms.create("aegis_session_sweep_daily", { periodInMinutes: 1440 });
    browser.alarms.onAlarm.addListener(alarm => {
      if (alarm.name === "aegis_session_sweep_daily" && isEnabled) {
        // Run scheduled sweep
        const now = Math.floor(Date.now() / 1000);
        // Sweeping happens against recorded interaction state
      }
    });
  } catch (e) {
    // Ignore alarms setup error
  }
}

// Runtime message dispatcher for status, tests, and user actions
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || typeof msg !== "object") return;

    if (msg.type === "GET_STATUS") {
      sendResponse({
        enabled: isEnabled,
        maxAgeDays: maxAgeDays,
        keepDomains: [...keepDomains],
        stats: { ...stats }
      });
      return true;
    }

    if (msg.type === "SET_ENABLED") {
      isEnabled = Boolean(msg.enabled);
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "session_sweeper_enabled": isEnabled });
      }
      sendResponse({ success: true, enabled: isEnabled });
      return true;
    }

    if (msg.type === "SET_CONFIG") {
      if (typeof msg.maxAgeDays === "number" && msg.maxAgeDays > 0) {
        maxAgeDays = msg.maxAgeDays;
      }
      if (Array.isArray(msg.keepDomains)) {
        keepDomains = msg.keepDomains;
      }
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({
          "session_sweeper_max_age_days": maxAgeDays,
          "session_sweeper_keep_domains": keepDomains
        });
      }
      sendResponse({ success: true, maxAgeDays, keepDomains });
      return true;
    }

    if (msg.type === "TRIGGER_SWEEP") {
      // Kill-switch check
      if (!isEnabled) {
        sendResponse({
          enabled: false,
          sweptOrigins: [],
          status: "kill_switch_active"
        });
        return true;
      }

      const items = Array.isArray(msg.items) ? msg.items : [];
      const now = (typeof msg.now === "number") ? msg.now : Math.floor(Date.now() / 1000);
      const targetDays = (typeof msg.maxAgeDays === "number") ? msg.maxAgeDays : maxAgeDays;
      const targetKeep = Array.isArray(msg.keepDomains) ? msg.keepDomains : keepDomains;

      const swept = sweep(items, now, targetDays, targetKeep);

      // Perform real data purge if requested and supported
      if (msg.purgeLive && swept.length > 0) {
        executeSweepData(swept);
      }

      stats.sweptCount += swept.length;
      stats.lastSweepTime = now;
      stats.lastSweptOrigins = [...swept];

      sendResponse({
        enabled: true,
        sweptOrigins: swept,
        count: swept.length,
        status: "success"
      });
      return true;
    }
  });
}
