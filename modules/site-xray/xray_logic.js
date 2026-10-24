/**
 * Aegis Site X-ray - Core Posture Analysis Logic
 * Reuses reference prototype logic from prototypes/aegis_modules.py.
 */

/**
 * Normalizes headers input into a lowercase lookup dictionary and cookie list.
 * @param {Object|Array<{name: string, value: string}>} rawHeaders
 * @returns {{ headers: Object<string, string>, cookies: Array<string> }}
 */
function normalizeHeaders(rawHeaders) {
  const headers = {};
  const cookies = [];

  if (!rawHeaders) {
    return { headers, cookies };
  }

  if (Array.isArray(rawHeaders)) {
    for (const item of rawHeaders) {
      if (!item || !item.name) continue;
      const k = item.name.toLowerCase();
      const v = item.value || "";
      if (k === "set-cookie") {
        cookies.push(v);
      } else {
        headers[k] = v;
      }
    }
  } else if (typeof rawHeaders === "object") {
    for (const [k, v] of Object.entries(rawHeaders)) {
      const lowerKey = k.toLowerCase();
      if (lowerKey === "set-cookie") {
        if (Array.isArray(v)) {
          cookies.push(...v);
        } else if (typeof v === "string") {
          cookies.push(v);
        }
      } else {
        headers[lowerKey] = String(v);
      }
    }
  }

  return { headers, cookies };
}

/**
 * Passive review of HTTP response headers received by the browser.
 * @param {Object|Array} rawHeaders
 * @param {boolean} isHttps
 * @returns {Array<[string, string]>} Array of [severity, message] tuples
 */
function xrayHeaders(rawHeaders, isHttps = false) {
  const { headers: h, cookies } = normalizeHeaders(rawHeaders);
  const out = [];

  function add(sev, msg) {
    out.push([sev, msg]);
  }

  // 1. Strict-Transport-Security (HTTPS only)
  if (isHttps && !h["strict-transport-security"]) {
    add("warn", "No HSTS header: browsers are not told to insist on HTTPS for this site");
  }

  // 2. Content-Security-Policy
  if (!h["content-security-policy"]) {
    add("warn", "No Content-Security-Policy: limited protection against injected scripts");
  } else {
    const csp = h["content-security-policy"].toLowerCase();
    if (csp.includes("unsafe-inline") || csp.includes("unsafe-eval")) {
      add("info", "CSP allows 'unsafe-inline' or 'unsafe-eval', which weakens its protection");
    }
  }

  // 3. Clickjacking (X-Frame-Options or CSP frame-ancestors)
  const cspVal = (h["content-security-policy"] || "").toLowerCase();
  if (!h["x-frame-options"] && !cspVal.includes("frame-ancestors")) {
    add("warn", "No clickjacking protection (X-Frame-Options or CSP frame-ancestors)");
  }

  // 4. X-Content-Type-Options
  if ((h["x-content-type-options"] || "").toLowerCase() !== "nosniff") {
    add("info", "Missing 'X-Content-Type-Options: nosniff'");
  }

  // 5. Referrer-Policy
  if (!h["referrer-policy"]) {
    add("info", "No Referrer-Policy: browser default applies");
  }

  // 6. Set-Cookie flags (Secure, HttpOnly, SameSite)
  for (const c of cookies) {
    const flags = c.toLowerCase();
    const name = c.split("=")[0].trim();

    if (isHttps && !flags.includes("secure")) {
      add("warn", `Cookie '${name}' lacks the Secure flag`);
    }
    if (!flags.includes("httponly")) {
      add("info", `Cookie '${name}' lacks HttpOnly (readable by page scripts)`);
    }
    if (!flags.includes("samesite")) {
      add("info", `Cookie '${name}' has no SameSite attribute`);
    }
  }

  // 7. Server version disclosure
  if (h["server"] && /\d+\.\d+/.test(h["server"])) {
    add("info", "Server header reveals a version number");
  }

  // Baseline clean verdict
  if (out.length === 0) {
    add("ok", "No common header issues found (this is not a full security assessment)");
  }

  return out;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { xrayHeaders, normalizeHeaders };
}
