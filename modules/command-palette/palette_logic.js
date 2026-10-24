/**
 * Aegis Command Palette - Command Registry and Filtering Logic
 */

const BUILTIN_COMMANDS = [
  {
    id: "clean-active-url",
    title: "Clean Current URL",
    description: "Strip tracking parameters (utm_*, fbclid, etc.) from active tab",
    keywords: ["url", "clean", "tracking", "sanitize", "strip"],
    category: "Privacy"
  },
  {
    id: "inspect-site-xray",
    title: "Inspect Site Security Posture",
    description: "Audit HTTP response headers (HSTS, CSP, cookies) for active site",
    keywords: ["xray", "headers", "security", "hsts", "csp", "audit"],
    category: "Security"
  },
  {
    id: "trigger-session-sweep",
    title: "Purge Expired Site Data",
    description: "Trigger Session Sweeper to clear stale cookies and storage",
    keywords: ["sweep", "session", "cookies", "cache", "purge", "clear"],
    category: "Storage"
  },
  {
    id: "view-tier-posture",
    title: "View Active Tier Posture",
    description: "Display current Surface, Identity, and Network tier configuration",
    keywords: ["tier", "surface", "identity", "network", "rfp", "fpp"],
    category: "Aegis Core"
  },
  {
    id: "open-isolated-cell",
    title: "Open New Isolated Cell",
    description: "Open tab in isolated container cell context",
    keywords: ["cell", "container", "isolate", "tab", "sandbox"],
    category: "Isolation"
  }
];

/**
 * Filters commands against user search query.
 * Matches case-insensitively against title, description, keywords, and ID.
 *
 * @param {string} query
 * @param {Array<Object>} [commands=BUILTIN_COMMANDS]
 * @returns {Array<Object>} Sorted list of matching command objects.
 */
function filterCommands(query, commands = BUILTIN_COMMANDS) {
  if (!Array.isArray(commands)) return [];
  if (!query || typeof query !== "string" || !query.trim()) {
    return [...commands];
  }

  const q = query.toLowerCase().trim();
  const tokens = q.split(/\s+/).filter(Boolean);

  const scored = [];
  for (const cmd of commands) {
    if (!cmd || !cmd.id) continue;

    const title = (cmd.title || "").toLowerCase();
    const desc = (cmd.description || "").toLowerCase();
    const id = cmd.id.toLowerCase();
    const keywords = Array.isArray(cmd.keywords) ? cmd.keywords.map(k => k.toLowerCase()) : [];

    let score = 0;

    // Exact title match gets highest score
    if (title === q) {
      score += 100;
    } else if (title.startsWith(q)) {
      score += 50;
    } else if (title.includes(q)) {
      score += 30;
    }

    // Token matching
    let allTokensMatch = true;
    for (const token of tokens) {
      let tokenMatch = false;
      if (title.includes(token)) {
        score += 15;
        tokenMatch = true;
      }
      if (desc.includes(token)) {
        score += 5;
        tokenMatch = true;
      }
      if (id.includes(token)) {
        score += 10;
        tokenMatch = true;
      }
      if (keywords.some(k => k.includes(token))) {
        score += 8;
        tokenMatch = true;
      }
      if (!tokenMatch) {
        allTokensMatch = false;
      }
    }

    if (score > 0 && allTokensMatch) {
      scored.push({ cmd, score });
    }
  }

  // Sort descending by score
  scored.sort((a, b) => b.score - a.score);
  return scored.map(item => item.cmd);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { BUILTIN_COMMANDS, filterCommands };
}
