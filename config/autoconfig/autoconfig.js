// Aegis Browser — autoconfig.js
// Placed in: firefox-esr/defaults/pref/autoconfig.js
//
// VERIFY-S-021: verify this mechanism works in ESR 153.
// The autoconfig mechanism loads a .cfg file for preferences that cannot be
// set by enterprise policies. The pref below points Firefox to aegis.cfg.
//
// Reference: https://support.mozilla.org/en-US/kb/customizing-firefox-using-autoconfig
// (verify the current URL and syntax for ESR 153)

// The integer 0 means no obfuscation (required for autoconfig files).
pref("general.config.obscure_value", 0);
// The config file name, relative to the Firefox application directory.
pref("general.config.filename", "aegis.cfg");
