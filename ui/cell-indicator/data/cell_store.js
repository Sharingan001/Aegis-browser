/**
 * Aegis Browser - Cell Store (Abstract Data Model)
 *
 * Design constraints:
 * 1. Represents abstract Cell mappings: cell -> { N, S, I }.
 * 2. Does NOT assume per-tab process preferences (ref: D-008).
 * 3. STRICT PLACEHOLDER: Declared target postures only (NOT ENFORCED, NOT VERIFIED).
 * 4. Strictly NO security claims or unverified protection statements.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CellStore = factory();
  }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const AXIS_DEFINITIONS = {
    network: {
      N0: { code: 'N0', name: 'Direct (Target Spec)', summary: 'Target specification: standard direct route' },
      N1: { code: 'N1', name: 'Encrypted DNS (Target Spec)', summary: 'Target specification: strict DoH/DoT (placeholder, not active)' },
      N2: { code: 'N2', name: 'Tor Circuit (Target Spec)', summary: 'Target specification: 3-hop circuit (placeholder, not active)' },
      N3: { code: 'N3', name: 'Tor Bridge (Target Spec)', summary: 'Target specification: bridge circuit (placeholder, not active)' }
    },
    surface: {
      S1: { code: 'S1', name: 'Standard Surface (Target Spec)', summary: 'Target specification: standard feature set' },
      S2: { code: 'S2', name: 'Reduced Surface (Target Spec)', summary: 'Target specification: restricted WebRTC (placeholder, not active)' },
      S3: { code: 'S3', name: 'Restricted Surface (Target Spec)', summary: 'Target specification: JIT/WASM disabled (placeholder in fastpath default)' },
      S4: { code: 'S4', name: 'Minimal Surface (Target Spec)', summary: 'Target specification: scripts disabled (placeholder, not active)' }
    },
    identity: {
      I1: { code: 'I1', name: 'Standard Partition (Target Spec)', summary: 'Target specification: first-party state partition' },
      I2: { code: 'I2', name: 'Isolated Cell (Target Spec)', summary: 'Target specification: container isolation (placeholder, not active)' },
      I3: { code: 'I3', name: 'Resistant Surface (Target Spec)', summary: 'Target specification: fingerprint resistance (placeholder, not active)' },
      I4: { code: 'I4', name: 'Ephemeral State (Target Spec)', summary: 'Target specification: memory-only state (placeholder, not active)' }
    }
  };

  const DEFAULT_CELLS = {
    'cell-research': {
      cell_id: 'cell-research',
      name: 'Research (Placeholder)',
      color: '#38BDF8',
      route: 'N2',
      surface: 'S3',
      identity: 'I4',
      badge_text: 'DECL',
      notes: 'PLACEHOLDER: Declared target levels (not enforced, not verified).'
    },
    'cell-work': {
      cell_id: 'cell-work',
      name: 'Work Workspace (Placeholder)',
      color: '#818CF8',
      route: 'N1',
      surface: 'S2',
      identity: 'I2',
      badge_text: 'DECL',
      notes: 'PLACEHOLDER: Declared target levels (not enforced, not verified).'
    },
    'cell-detonation': {
      cell_id: 'cell-detonation',
      name: 'Detonation (Placeholder)',
      color: '#EF4444',
      route: 'N2',
      surface: 'S4',
      identity: 'I4',
      badge_text: 'DECL',
      notes: 'PLACEHOLDER: Declared target levels (not enforced, not verified).'
    },
    'cell-default': {
      cell_id: 'cell-default',
      name: 'Standard Browsing (Placeholder)',
      color: '#10B981',
      route: 'N0',
      surface: 'S1',
      identity: 'I1',
      badge_text: 'DECL',
      notes: 'PLACEHOLDER: Declared target levels (not enforced, not verified).'
    }
  };

  // State
  let activeCellId = 'cell-research';
  const tabCellMap = new Map();

  function getAxisDefinitions() {
    return AXIS_DEFINITIONS;
  }

  function getAllCells() {
    return Object.values(DEFAULT_CELLS);
  }

  function getCell(cellId) {
    return DEFAULT_CELLS[cellId] || DEFAULT_CELLS['cell-default'];
  }

  function getActiveCell() {
    return getCell(activeCellId);
  }

  function setActiveCell(cellId) {
    if (DEFAULT_CELLS[cellId]) {
      activeCellId = cellId;
      return true;
    }
    return false;
  }

  function getCellForTab(tabId) {
    const cellId = tabCellMap.get(tabId) || activeCellId;
    return getCell(cellId);
  }

  function setCellForTab(tabId, cellId) {
    if (DEFAULT_CELLS[cellId]) {
      tabCellMap.set(tabId, cellId);
      return true;
    }
    return false;
  }

  function removeTab(tabId) {
    tabCellMap.delete(tabId);
  }

  return {
    AXIS_DEFINITIONS,
    DEFAULT_CELLS,
    getAxisDefinitions,
    getAllCells,
    getCell,
    getActiveCell,
    setActiveCell,
    getCellForTab,
    setCellForTab,
    removeTab
  };
});
