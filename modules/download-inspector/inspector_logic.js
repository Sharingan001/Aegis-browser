/**
 * Aegis Download Inspector - Core Verification Logic
 * Ported directly from prototypes/aegis_modules.py.
 */

const MAGIC_SIGNATURES = [
  { sig: [0x4D, 0x5A], type: "windows-executable" },          // MZ
  { sig: [0x7F, 0x45, 0x4C, 0x46], type: "linux-executable" }, // \x7fELF
  { sig: [0x25, 0x50, 0x44, 0x46], type: "pdf" },              // %PDF
  { sig: [0x50, 0x4B, 0x03, 0x04], type: "zip-or-office" },    // PK\x03\x04
  { sig: [0x89, 0x50, 0x4E, 0x47], type: "png" },              // \x89PNG
  { sig: [0xFF, 0xD8, 0xFF], type: "jpeg" },                    // \xff\xd8\xff
  { sig: [0x47, 0x49, 0x46, 0x38], type: "gif" },              // GIF8
  { sig: [0x23, 0x21], type: "script" }                         // #!
];

const RISKY_EXT = new Set([
  "exe", "scr", "msi", "bat", "cmd", "ps1", "vbs", "js", "jse", "wsf",
  "hta", "lnk", "jar", "com", "dll", "sh", "iso", "img"
]);

const DECOY_EXT = new Set([
  "pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "txt", "mp4", "mp3", "zip"
]);

const EXPECTED_FORMAT_MAP = {
  "pdf": "pdf",
  "png": "png",
  "jpg": "jpeg",
  "jpeg": "jpeg",
  "gif": "gif"
};

/**
 * Detects file type from byte prefix.
 * @param {Uint8Array} data
 * @returns {string}
 */
function detectFileType(data) {
  if (!data || data.length === 0) return "unknown";

  for (const { sig, type } of MAGIC_SIGNATURES) {
    if (data.length >= sig.length) {
      let match = true;
      for (let i = 0; i < sig.length; i++) {
        if (data[i] !== sig[i]) {
          match = false;
          break;
        }
      }
      if (match) return type;
    }
  }
  return "unknown";
}

/**
 * Computes SHA-256 hex digest of a Uint8Array buffer.
 * @param {Uint8Array} data
 * @returns {Promise<string>}
 */
async function computeSha256(data) {
  if (typeof crypto !== "undefined" && crypto.subtle && crypto.subtle.digest) {
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
  }
  return "unavailable";
}

/**
 * Inspects a downloaded file payload and filename for security risks.
 * @param {string} filename
 * @param {Uint8Array} data
 * @returns {Promise<{ sha256: string, size: number, claimedExt: string, detectedType: string, flags: Array<string>, level: string }>}
 */
async function inspectDownload(filename, data) {
  const parts = String(filename || "").toLowerCase().split(".");
  const ext = parts.length > 1 ? parts[parts.length - 1] : "";
  const detected = detectFileType(data);
  const flags = [];

  // Check 1: Double extension (e.g. invoice.pdf.exe)
  if (parts.length >= 3) {
    const penultimate = parts[parts.length - 2];
    if (DECOY_EXT.has(penultimate) && RISKY_EXT.has(ext)) {
      flags.push(`HIGH double extension: looks like .${penultimate} but is .${ext}`);
    }
  }

  // Check 2: Direct risky extension
  if (RISKY_EXT.has(ext)) {
    flags.push(`MEDIUM executable/script type .${ext}: quarantine and do not auto-open`);
  }

  // Check 3: Disguised binary executable
  if ((detected === "windows-executable" || detected === "linux-executable") && !RISKY_EXT.has(ext)) {
    flags.push(`HIGH content is ${detected} but name says .${ext || "none"}`);
  }

  // Check 4: Mismatched standard document/media types
  const expected = EXPECTED_FORMAT_MAP[ext];
  if (expected && detected !== "unknown" && detected !== expected && detected !== "windows-executable" && detected !== "linux-executable") {
    flags.push(`MEDIUM name says .${ext} but content looks like ${detected}`);
  }

  // Check 5: Right-to-Left Override Unicode exploit (\u202e, \u202d)
  if (/[\u202e\u202d]/.test(filename)) {
    flags.push("HIGH filename contains a right-to-left override character (hides the true extension)");
  }

  // Check 6: Abnormally long filename
  if (filename && filename.length > 120) {
    flags.push("LOW very long filename");
  }

  // Severity Level calculation
  let level = "low";
  if (flags.some(f => f.startsWith("HIGH"))) {
    level = "high";
  } else if (flags.some(f => f.startsWith("MEDIUM"))) {
    level = "medium";
  }

  const sha256 = await computeSha256(data);

  return {
    sha256,
    size: data ? data.length : 0,
    claimedExt: ext,
    detectedType: detected,
    flags,
    level
  };
}

// Expose on globalThis for background scripts and test runners
if (typeof globalThis !== "undefined") {
  globalThis.inspectDownload = inspectDownload;
  globalThis.detectFileType = detectFileType;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    inspectDownload,
    detectFileType,
    computeSha256,
    MAGIC_SIGNATURES,
    RISKY_EXT,
    DECOY_EXT
  };
}
