/**
 * Aegis Session Sweeper - Core Sweep Logic
 * Reuses reference prototype logic from prototypes/aegis_modules.py.
 */

/**
 * Extracts registrable domain (eTLD+1) from a hostname.
 * Handles common multi-part suffixes like .co.uk, .com.au, etc.
 * @param {string} hostname
 * @returns {string}
 */
function registrableDomain(hostname) {
  if (!hostname || typeof hostname !== "string") return "";
  let host = hostname.toLowerCase().trim();
  // Strip port if present
  if (host.includes(":")) {
    host = host.split(":")[0];
  }

  // IPv4 or bracketed IPv6
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(host) || host.startsWith("[") || host === "localhost") {
    return host;
  }

  const parts = host.split(".");
  if (parts.length <= 2) {
    return host;
  }

  // Common two-level TLDs
  const twoLevelTlds = new Set([
    "co.uk", "org.uk", "gov.uk", "ac.uk",
    "com.au", "net.au", "org.au", "edu.au",
    "co.nz", "net.nz", "org.nz",
    "co.jp", "ne.jp", "ac.jp",
    "com.br", "net.br", "org.br",
    "com.sg", "edu.sg"
  ]);

  const lastTwo = parts.slice(-2).join(".");
  if (twoLevelTlds.has(lastTwo) && parts.length >= 3) {
    return parts.slice(-3).join(".");
  }

  return parts.slice(-2).join(".");
}

/**
 * Identifies origins whose stored site data has expired.
 * Allow-listed domains are never swept.
 *
 * @param {Array<{origin: string, lastInteraction: number, hasLogin?: boolean}>} items
 * @param {number} now - Current epoch timestamp in seconds.
 * @param {number} [maxAgeDays=14] - Maximum allowed inactivity threshold in days.
 * @param {Array<string>|Set<string>} [keepDomains=[]] - Domains to exempt from sweeping.
 * @returns {Array<string>} List of origins whose site data should be purged.
 */
function sweep(items, now, maxAgeDays = 14, keepDomains = []) {
  if (!Array.isArray(items)) return [];

  const keepSet = new Set();
  if (keepDomains) {
    for (const d of keepDomains) {
      if (typeof d === "string") {
        keepSet.add(d.toLowerCase().trim());
      }
    }
  }

  const thresholdSeconds = maxAgeDays * 86400;
  const out = [];

  for (const s of items) {
    if (!s || !s.origin || typeof s.lastInteraction !== "number") {
      continue;
    }

    let host = s.origin;
    try {
      if (s.origin.includes("://")) {
        const u = new URL(s.origin);
        host = u.hostname;
      }
    } catch (e) {
      // Fall back to s.origin as host string
    }

    const reg = registrableDomain(host);
    const hostLower = host.toLowerCase();

    // Check allow-list against registrable domain, full hostname, or wildcard match
    if (keepSet.has(reg) || keepSet.has(hostLower)) {
      continue;
    }

    // Check expiration
    if (now - s.lastInteraction > thresholdSeconds) {
      out.push(s.origin);
    }
  }

  return out;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { sweep, registrableDomain };
}
