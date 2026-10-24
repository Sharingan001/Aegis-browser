/**
 * Aegis Command Palette - Background WebExtension Service
 * Manages keyboard shortcut triggers, omnibar search, and command execution.
 */

let isEnabled = true;
const executionLog = [];

// Load saved configuration from local storage
if (typeof browser !== "undefined" && browser.storage && browser.storage.local) {
  browser.storage.local.get(["command_palette_enabled"]).then(res => {
    if (typeof res.command_palette_enabled === "boolean") {
      isEnabled = res.command_palette_enabled;
    }
  }).catch(() => {
    // Fail safe to default enabled state
  });

  if (browser.storage.onChanged) {
    browser.storage.onChanged.addListener((changes, area) => {
      if (area === "local" && changes.command_palette_enabled) {
        isEnabled = Boolean(changes.command_palette_enabled.newValue);
      }
    });
  }
}

/**
 * Executes a registered command action.
 * @param {string} commandId
 * @param {Object} [context={}]
 * @returns {Promise<Object>} Execution result
 */
async function executeCommand(commandId, context = {}) {
  if (!isEnabled) {
    return { success: false, status: "kill_switch_active", commandId };
  }

  const result = {
    commandId: commandId,
    timestamp: Date.now(),
    success: true,
    action: "executed"
  };

  switch (commandId) {
    case "clean-active-url":
      result.detail = "Initiated URL cleaning for active tab";
      break;

    case "inspect-site-xray":
      result.detail = "Triggered site security posture inspection";
      break;

    case "trigger-session-sweep":
      result.detail = "Dispatched session sweep trigger";
      break;

    case "view-tier-posture":
      result.detail = "Queried active tier configuration";
      break;

    case "open-isolated-cell":
      result.detail = "Opened new isolated container cell";
      break;

    default:
      result.detail = `Custom command '${commandId}' executed`;
      break;
  }

  executionLog.push(result);
  return result;
}

// Global keyboard shortcut listener
if (typeof browser !== "undefined" && browser.commands && browser.commands.onCommand) {
  browser.commands.onCommand.addListener(async command => {
    if (!isEnabled) return;
    await executeCommand(command);
  });
}

// Runtime message dispatcher
if (typeof browser !== "undefined" && browser.runtime && browser.runtime.onMessage) {
  browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || typeof msg !== "object") return;

    if (msg.type === "GET_STATUS") {
      sendResponse({
        enabled: isEnabled,
        commandsCount: BUILTIN_COMMANDS.length,
        executionLogCount: executionLog.length
      });
      return true;
    }

    if (msg.type === "SET_ENABLED") {
      isEnabled = Boolean(msg.enabled);
      if (browser.storage && browser.storage.local) {
        browser.storage.local.set({ "command_palette_enabled": isEnabled });
      }
      sendResponse({ success: true, enabled: isEnabled });
      return true;
    }

    if (msg.type === "SEARCH_COMMANDS") {
      if (!isEnabled) {
        sendResponse({ enabled: false, results: [], status: "kill_switch_active" });
        return true;
      }
      const results = filterCommands(msg.query || "");
      sendResponse({
        enabled: true,
        query: msg.query || "",
        results: results
      });
      return true;
    }

    if (msg.type === "EXECUTE_COMMAND") {
      if (!isEnabled) {
        sendResponse({ enabled: false, status: "kill_switch_active" });
        return true;
      }
      executeCommand(msg.commandId, msg.context).then(res => {
        sendResponse(res);
      }).catch(err => {
        sendResponse({ success: false, error: String(err) });
      });
      return true;
    }
  });
}
