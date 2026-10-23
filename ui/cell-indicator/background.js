/**
 * Aegis Browser - Cell Indicator Background Service
 *
 * Updates the browserAction badge based on the active Cell's declared posture.
 * Does NOT assume per-tab preferences or mutate process-level prefs (ref: D-008).
 */

/* global browser, chrome, CellStore */
const api = typeof browser !== 'undefined' ? browser : chrome;

function updateBadgeForTab(tabId) {
  const cell = CellStore.getCellForTab(tabId);
  const badgeText = cell.surface || 'S1';
  const badgeColor = cell.color || '#38BDF8';

  if (api.browserAction && api.browserAction.setBadgeText) {
    api.browserAction.setBadgeText({ text: badgeText, tabId: tabId });
  }
  if (api.browserAction && api.browserAction.setBadgeBackgroundColor) {
    api.browserAction.setBadgeBackgroundColor({ color: badgeColor, tabId: tabId });
  }
}

// Tab activation listener
if (api.tabs && api.tabs.onActivated) {
  api.tabs.onActivated.addListener((activeInfo) => {
    updateBadgeForTab(activeInfo.tabId);
  });
}

// Tab updated listener
if (api.tabs && api.tabs.onUpdated) {
  api.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.status === 'complete') {
      updateBadgeForTab(tabId);
    }
  });
}

// Tab removed listener
if (api.tabs && api.tabs.onRemoved) {
  api.tabs.onRemoved.addListener((tabId) => {
    CellStore.removeTab(tabId);
  });
}

// Message handler for popup and internal communication
if (api.runtime && api.runtime.onMessage) {
  api.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.action) {
      return false;
    }

    switch (message.action) {
      case 'GET_ACTIVE_CELL': {
        const tabId = message.tabId;
        const cell = tabId ? CellStore.getCellForTab(tabId) : CellStore.getActiveCell();
        const definitions = CellStore.getAxisDefinitions();
        sendResponse({
          cell: cell,
          definitions: definitions,
          allCells: CellStore.getAllCells()
        });
        break;
      }

      case 'SWITCH_CELL': {
        const targetCellId = message.cellId;
        const tabId = message.tabId;
        const success = CellStore.setActiveCell(targetCellId);
        if (success && tabId) {
          CellStore.setCellForTab(tabId, targetCellId);
          updateBadgeForTab(tabId);
        }
        sendResponse({
          success: success,
          activeCell: CellStore.getActiveCell()
        });
        break;
      }

      default:
        sendResponse({ error: 'Unknown action' });
        break;
    }

    return true; // async response
  });
}

// Initial setup on startup
if (api.tabs && api.tabs.query) {
  api.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0]) {
      updateBadgeForTab(tabs[0].id);
    }
  });
}
