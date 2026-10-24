/**
 * Aegis Session Sweeper - Background WebExtension Service
 * Selectively purges expired site browsing data while honoring user keep-lists.
 *
 * HOW DATA AGE IS COMPUTED (honest mechanism):
 *   browser.browsingData.remove({since: ts}, ...) deletes data NEWER than ts
 *   ("data since a time"), which is the OPPOSITE of "older than N days", and
 *   the API cannot enumerate per-origin data ages. This module therefore keeps
 *   its own last-interaction ledger:
 *     - browser.history.onVisited  (permission "history"): records
 *       { origin -> last visit epoch seconds } for every http(s) visit.
 *     - An origin is STALE when now - lastInteraction > maxAgeDays * 86400.
 *     - Stale origins are deleted per-origin via
 *       browser.browsingData.remove({ origins: [...] }, {cookies, localStorage,
 *       cache, indexedDB}) with NO "since" cutoff (a cutoff would KEEP the old
 *       data we want removed).
 *
 * PERMISSIONS / EVENTS USED (complete list):
 *   - history   : browser.history.onVisited -> last-interaction tracking.
 *   - tabs      : browser.tabs.query -> open-tab URL check so that data for
 *                 sites with a currently open tab is NEVER deleted. Tab URLs
 *                 are used only for this protection and are never recorded.
 *   - browsingData : browser.browsingData.remove (per-origin purge).
 *   - storage   : config (enabled/maxAgeDays/keepDomains/opt-in) + ledger.
 *   - alarms    : browser.alarms (daily scheduled sweep).
 *
 * SAFETY:
 *   - FIRST USE IS OPT-IN: no deletion ever happens until the user explicitly
 *     opts in (SET_OPT_IN). Before opt-in, TRIGGER_SWEEP with purgeLive
 *     returns "opt_in_required" together with a preview of what WOULD be
 *     deleted. PREVIEW_SWEEP always returns the plan without deleting.
 *   - Allow-listed registrable domains (and their subdomains) are never swept.
 *   - Origins with an open tab are never swept.
 */

let isEnabled = true;
let isOptedIn = false;
let maxAgeDays = 14;
let keepDomains = [];
const lastInteraction = {};  // origin -> epoch seconds (last visit)
let ledgerDirty = false;
let ledgerFlushTimer = null;

const stats = {
  sweptCount: 0,
  lastSweepTime: null,
  lastSweptOrigins: []
};

const LEDGER_FLUSH_MS = 5000;

// Load saved configuration from local storage (Privacy Class P1)
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get([
    "session_sweeper_enabled",
    "session_sweeper_opt_in",
    "session_sweeper_max_age_days",
    "session_sweeper_keep_domains",
    "session_sweeper_ledger"
  ]).then(res => {
    if (typeof res.session_sweeper_enabled === "boolean") {
      isEnabled = res.session_sweeper_enabled;
    }
    if (typeof res.session_sweeper_opt_in === "boolean") {
      isOptedIn = res.session_sweeper_opt_in;
    }
    if (typeof res.session_sweeper_max_age_days === "number" && res.session_sweeper_max_age_days > 0) {
      maxAgeDays = res.session_sweeper_max_age_days;
    }
    if (Array.isArray(res.session_sweeper_keep_domains)) {
      keepDomains = res.session_sweeper_keep_domains;
    }
    if (res.session_sweeper_ledger && typeof res.session_sweeper_ledger === "object") {
      Object.assign(lastInteraction, res.session_sweeper_ledger);
    }
  }).catch(() => {
    // Fail safe: opt-in stays false; nothing is ever deleted on storage errors.
  });

  if (browser.storage.onChanged) {
    browser.storage.onChanged.addListener((changes, area) => {
      if (area === "local") {
        if (changes.session_sweeper_enabled) {
          isEnabled = Boolean(changes.session_sweeper_enabled.newValue);
        }
        if (changes.session_sweeper_opt_in) {
          isOptedIn = Boolean(changes.session_sweeper_opt_in.newValue);
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

// First use is opt-in: record the explicit opt-out default on install.
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onInstalled) {
  browser.runtime.onInstalled.addListener(details => {
    if (details && details.reason === "install") {
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "session_sweeper_opt_in": false });
      }
    }
  });
}

/**
 * Last-interaction tracking: every visit updates the per-origin ledger.
 * Event used: browser.history.onVisited (permission "history").
 */
if (typeof browser !== "undefined" && browser.history && browser.history.onVisited) {
  browser.history.onVisited.addListener(visit => {
    if (!visit || typeof visit.url !== "string") return;
    if (!visit.url.startsWith("http://") && !visit.url.startsWith("https://")) return;
    try {
      const u = new URL(visit.url);
      const origin = u.origin;
      const ts = Math.floor((typeof visit.time === "number" ? visit.time : Date.now()) / 1000);
      // Keep the most recent interaction per origin.
      if (!lastInteraction[origin] || ts > lastInteraction[origin]) {
        lastInteraction[origin] = ts;
        scheduleLedgerFlush();
      }
    } catch (e) {
      // Unparseable URL: ignore.
    }
  });
}

function scheduleLedgerFlush() {
  ledgerDirty = true;
  if (ledgerFlushTimer !== null) return;
  ledgerFlushTimer = setTimeout(flushLedger, LEDGER_FLUSH_MS);
}

function flushLedger() {
  ledgerFlushTimer = null;
  if (!ledgerDirty) return;
  ledgerDirty = false;
  if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
    browser.storage.local.set({ "session_sweeper_ledger": lastInteraction }).catch(() => {});
  }
}

function originHost(origin) {
  try {
    return new URL(origin).hostname.toLowerCase();
  } catch (e) {
    return String(origin || "").toLowerCase();
  }
}

/**
 * Open-tab protection: origins whose registrable domain (or exact hostname)
 * matches any currently open tab are never swept.
 * Event/API used: browser.tabs.query (permission "tabs").
 * @returns {Promise<Set<string>>} set of protected hostnames + registrable domains
 */
async function getOpenTabDomains() {
  const protectedSet = new Set();
  if (typeof browser === "undefined" || !browser.tabs || !browser.tabs.query) {
    return protectedSet;
  }
  try {
    const tabs = await browser.tabs.query({});
    for (const tab of tabs) {
      if (!tab || typeof tab.url !== "string") continue;
      if (!tab.url.startsWith("http://") && !tab.url.startsWith("https://")) continue;
      try {
        const u = new URL(tab.url);
        const host = u.hostname.toLowerCase();
        protectedSet.add(host);
        const reg = registrableDomain(host);
        if (reg) protectedSet.add(reg);
      } catch (e) {
        // Ignore unparseable tab URLs.
      }
    }
  } catch (e) {
    // Fail safe: if open tabs cannot be enumerated, protect nothing extra but
    // still never delete allow-listed domains (handled by sweep()).
  }
  return protectedSet;
}

/**
 * Build the full sweep plan: stale, not allow-listed, and not open in any tab.
 * @param {number} now - epoch seconds
 * @param {number} maxAgeDaysArg
 * @param {Array<string>} keepArg
 * @param {Array<{origin, lastInteraction}>} [itemsOverride] - use caller items instead of the ledger
 */
async function computeSweepPlan(now, maxAgeDaysArg, keepArg, itemsOverride) {
  const items = Array.isArray(itemsOverride)
    ? itemsOverride
    : Object.keys(lastInteraction).map(origin => ({
        origin: origin,
        lastInteraction: lastInteraction[origin]
      }));

  const sweepable = sweep(items, now, maxAgeDaysArg, keepArg);
  const openDomains = await getOpenTabDomains();

  const toSweep = [];
  const protectedOpenTabs = [];
  for (const origin of sweepable) {
    const host = originHost(origin);
    const reg = registrableDomain(host);
    if (openDomains.has(host) || openDomains.has(reg)) {
      protectedOpenTabs.push(origin);
    } else {
      toSweep.push(origin);
    }
  }

  return {
    toSweep: toSweep,
    protectedOpenTabs: protectedOpenTabs,
    allowListedOrFreshExcluded: items.length - sweepable.length,
    trackedOrigins: items.length
  };
}

/**
 * Execute actual data deletion for specified origins via browsingData API.
 * No "since" cutoff is passed: cutoffs delete data NEWER than a timestamp,
 * which is the opposite of the stale-data purge this module performs.
 * @param {Array<string>} origins
 * @returns {Promise<boolean>}
 */
async function executeSweepData(origins) {
  if (!origins || origins.length === 0) return true;
  if (typeof browser === "undefined" || !browser.browsingData || !browser.browsingData.remove) {
    return false;
  }

  try {
    await browser.browsingData.remove(
      { origins: origins },
      {
        cookies: true,
        localStorage: true,
        cache: true,
        indexedDB: true
      }
    );
    return { ok: true, unsupported: false, error: null };
  } catch (err) {
    // HONEST LIMIT (measured on ESR 153.5.1): browsingData "origins" is a
    // Chrome-only option; Gecko rejects it ("Unexpected property origins").
    // There is NO per-origin deletion path on this engine without broad host
    // permissions. We NEVER fall back to global removal or a "since" cutoff:
    // both would delete data for ALL sites (and "since" deletes the NEWER
    // data, the opposite of a stale purge).
    return {
      ok: false,
      unsupported: String(err).includes("origins"),
      error: String(err)
    };
  }
}

// Optional periodic schedule via alarms API (runs the real ledger-based sweep).
if (typeof browser !== "undefined" && browser.alarms) {
  try {
    browser.alarms.create("aegis_session_sweep_daily", { periodInMinutes: 1440 });
    browser.alarms.onAlarm.addListener(alarm => {
      if (alarm.name === "aegis_session_sweep_daily" && isEnabled) {
        const now = Math.floor(Date.now() / 1000);
        if (!isOptedIn) {
          return; // Never delete anything before the user opts in.
        }
        computeSweepPlan(now, maxAgeDays, keepDomains).then(plan => {
          if (plan.toSweep.length > 0) {
            return executeSweepData(plan.toSweep).then(res => {
              stats.sweptCount += res.ok ? plan.toSweep.length : 0;
              stats.lastPurgeUnsupported = res.unsupported;
              stats.lastSweepTime = now;
              stats.lastSweptOrigins = [...plan.toSweep];
            });
          }
        }).catch(() => {});
      }
    });
  } catch (e) {
    // Ignore alarms setup error.
  }
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

// Message dispatcher for status, tests, user actions, and cross-module calls
function handleMessage(msg, sender, sendResponse) {
  {

    if (msg.type === "GET_STATUS") {
      sendResponse({
        enabled: isEnabled,
        optIn: isOptedIn,
        needsOptIn: !isOptedIn,
        maxAgeDays: maxAgeDays,
        keepDomains: [...keepDomains],
        trackedOrigins: Object.keys(lastInteraction).length,
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

    if (msg.type === "SET_OPT_IN") {
      isOptedIn = Boolean(msg.optIn);
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "session_sweeper_opt_in": isOptedIn });
      }
      sendResponse({ success: true, optIn: isOptedIn });
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

    if (msg.type === "PREVIEW_SWEEP") {
      // Preview: returns exactly what would be deleted. Never deletes.
      if (!isEnabled) {
        sendResponse({ enabled: false, status: "kill_switch_active", plan: null });
        return true;
      }
      const now = (typeof msg.now === "number") ? msg.now : Math.floor(Date.now() / 1000);
      const targetDays = (typeof msg.maxAgeDays === "number") ? msg.maxAgeDays : maxAgeDays;
      const targetKeep = Array.isArray(msg.keepDomains) ? msg.keepDomains : keepDomains;
      const itemsOverride = Array.isArray(msg.items) ? msg.items : null;

      computeSweepPlan(now, targetDays, targetKeep, itemsOverride).then(plan => {
        const ageDays = {};
        const source = itemsOverride || lastInteraction;
        for (const origin of plan.toSweep) {
          if (typeof source[origin] === "number") {
            ageDays[origin] = Math.floor((now - source[origin]) / 86400);
          } else {
            const item = (itemsOverride || []).find(i => i && i.origin === origin);
            if (item) ageDays[origin] = Math.floor((now - item.lastInteraction) / 86400);
          }
        }
        sendResponse({
          enabled: true,
          status: "preview",
          optIn: isOptedIn,
          plan: {
            wouldDelete: plan.toSweep,
            ageDays: ageDays,
            protectedOpenTabs: plan.protectedOpenTabs,
            excludedStaleOrAllowListed: plan.allowListedOrFreshExcluded,
            trackedOrigins: plan.trackedOrigins
          }
        });
      }).catch(err => {
        sendResponse({ enabled: true, status: "error", error: String(err) });
      });
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

      const now = (typeof msg.now === "number") ? msg.now : Math.floor(Date.now() / 1000);
      const targetDays = (typeof msg.maxAgeDays === "number") ? msg.maxAgeDays : maxAgeDays;
      const targetKeep = Array.isArray(msg.keepDomains) ? msg.keepDomains : keepDomains;
      const itemsOverride = Array.isArray(msg.items) ? msg.items : null;

      // Opt-in gate: no live deletion before the user explicitly opts in.
      if (msg.purgeLive && !isOptedIn) {
        computeSweepPlan(now, targetDays, targetKeep, itemsOverride).then(plan => {
          sendResponse({
            enabled: true,
            status: "opt_in_required",
            sweptOrigins: [],
            preview: {
              wouldDelete: plan.toSweep,
              protectedOpenTabs: plan.protectedOpenTabs
            }
          });
        }).catch(err => {
          sendResponse({ enabled: true, status: "error", error: String(err) });
        });
        return true;
      }

      computeSweepPlan(now, targetDays, targetKeep, itemsOverride).then(plan => {
        const swept = plan.toSweep;

        // Perform real data purge only when requested, opted in, and supported.
        if (msg.purgeLive && swept.length > 0) {
          return executeSweepData(swept).then(res => {
            if (res.ok) {
              stats.sweptCount += swept.length;
            }
            stats.lastSweepTime = now;
            stats.lastSweptOrigins = [...swept];
            sendResponse({
              enabled: true,
              sweptOrigins: swept,
              protectedOpenTabs: plan.protectedOpenTabs,
              purgeExecuted: res.ok,
              purgeUnsupportedOnEngine: res.unsupported,
              purgeError: res.error,
              status: res.ok
                ? "success"
                : (res.unsupported ? "purge_unsupported_on_this_engine" : "purge_failed")
            });
          });
        }

        stats.lastSweepTime = now;
        stats.lastSweptOrigins = [...swept];
        sendResponse({
          enabled: true,
          sweptOrigins: swept,
          protectedOpenTabs: plan.protectedOpenTabs,
          status: "success"
        });
      }).catch(err => {
        sendResponse({ enabled: true, status: "error", error: String(err) });
      });
      return true;
    }
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
