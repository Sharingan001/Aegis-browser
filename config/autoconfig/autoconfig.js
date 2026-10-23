// Aegis Browser - autoconfig.js
// Placed in: firefox-esr/defaults/pref/autoconfig.js
//
// VERIFY-S-021: autoconfig mechanism in ESR 153.
// The integer 0 means no byte-offset obfuscation (plain text .cfg).
pref("general.config.obscure_value", 0);
// The config file name, relative to the Firefox application directory.
pref("general.config.filename", "aegis.cfg");
// Explicitly assert and enforce autoconfig sandboxing
pref("general.config.sandbox_enabled", true);
