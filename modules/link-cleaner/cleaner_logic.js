/**
 * Aegis Link Cleaner - Core Sanitization Logic
 * Reuses reference prototype logic from prototypes/aegis_modules.py.
 */

const TRACKING_PARAMS = new Set([
  "fbclid", "gclid", "dclid", "msclkid", "mc_eid", "mc_cid", "igshid", "yclid",
  "_hsenc", "_hsmi", "ref_src", "ref_url", "vero_id", "spm", "si"
]);

const TRACKING_PREFIXES = ["utm_", "pk_", "mtm_", "hsa_"];

/**
 * Strips tracking parameters from a URL string.
 * @param {string} rawUrl - The input URL to clean.
 * @param {Array<string>|Set<string>} [keep=[]] - Optional list of parameter names to preserve.
 * @returns {{ cleanedUrl: string, removedParams: Array<string> }}
 */
function cleanLink(rawUrl, keep = []) {
  if (!rawUrl || typeof rawUrl !== "string") {
    return { cleanedUrl: rawUrl, removedParams: [] };
  }

  const keepSet = new Set();
  if (keep) {
    if (Array.isArray(keep) || keep instanceof Set) {
      for (const k of keep) {
        keepSet.add(String(k).toLowerCase());
      }
    } else if (typeof keep === "object") {
      // Per-site keep map: { "example.com": ["spm"], "*": ["custom_param"] }
      try {
        const parsed = new URL(rawUrl);
        const hostname = parsed.hostname.toLowerCase();
        for (const [domain, params] of Object.entries(keep)) {
          const dom = domain.toLowerCase();
          if (dom === "*" || hostname === dom || hostname.endsWith("." + dom)) {
            if (Array.isArray(params) || params instanceof Set) {
              for (const p of params) {
                keepSet.add(String(p).toLowerCase());
              }
            } else if (typeof params === "string") {
              keepSet.add(params.toLowerCase());
            }
          }
        }
      } catch (e) {
        // Fall back to empty keepSet on malformed URL
      }
    }
  }

  try {
    const u = new URL(rawUrl);
    // Ignore non-http/https protocols (data:, about:, javascript:, etc.)
    if (u.protocol !== "http:" && u.protocol !== "https:") {
      return { cleanedUrl: rawUrl, removedParams: [] };
    }

    const removed = [];
    const preservedParams = [];

    // Parse query string preserving original parameter order
    for (const [key, val] of u.searchParams.entries()) {
      const lk = key.toLowerCase();
      const isTracking = TRACKING_PARAMS.has(lk) || TRACKING_PREFIXES.some(p => lk.startsWith(p));

      if (isTracking && !keepSet.has(lk)) {
        removed.push(key);
      } else {
        preservedParams.push([key, val]);
      }
    }

    if (removed.length === 0) {
      return { cleanedUrl: rawUrl, removedParams: [] };
    }

    // Reconstruct query
    const newSearchParams = new URLSearchParams();
    for (const [k, v] of preservedParams) {
      newSearchParams.append(k, v);
    }

    const queryStr = newSearchParams.toString();
    u.search = queryStr ? `?${queryStr}` : "";

    return {
      cleanedUrl: u.toString(),
      removedParams: removed
    };
  } catch (err) {
    // If URL parsing fails, return original unchanged (fail safe)
    return { cleanedUrl: rawUrl, removedParams: [] };
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { cleanLink, TRACKING_PARAMS, TRACKING_PREFIXES };
}
