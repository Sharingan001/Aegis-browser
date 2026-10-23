/**
 * Aegis Browser - Cell Store (Abstract Data Model)
 *
 * Design constraints:
 * 1. Represents abstract Cell mappings: cell -> { N, S, I }.
 * 2. Does NOT assume per-tab process preferences (ref: D-008).
 * 3. Contains strictly NO security claims in any description or label.
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
      N0: { code: 'N0', name: 'Direct', summary: 'Standard route via local network gateway' },
      N1: { code: 'N1', name: 'Encrypted DNS', summary: 'Strict encrypted DNS without cleartext fallback' },
      N2: { code: 'N2', name: 'Tor Circuit', summary: 'Three-hop onion routed circuit with remote DNS resolution' },
      N3: { code: 'N3', name: 'Tor Bridge', summary: 'Pluggable transport or bridge routed circuit' }
    },
    surface: {
      S1: { code: 'S1', name: 'Standard Surface', summary: 'Full web platform feature set enabled' },
      S2: { code: 'S2', name: 'Reduced Surface', summary: 'Hardened platform baseline with WebRTC restricted' },
      S3: { code: 'S3', name: 'Restricted Surface', summary: 'JIT and WebAssembly disabled; WebGL disabled' },
      S4: { code: 'S4', name: 'Minimal Surface', summary: 'Scripts blocked by default; static document mode' }
    },
    identity: {
      I1: { code: 'I1', name: 'Standard Partition', summary: 'Standard first-party cookie and cache partitioning' },
      I2: { code: 'I2', name: 'Isolated Cell', summary: 'Isolated container storage, cookies, and cache' },
      I3: { code: 'I3', name: 'Resistant Surface', summary: 'Standardized canvas and audio resistance enabled' },
      I4: { code: 'I4', name: 'Ephemeral State', summary: 'In-memory session; storage cleared upon Cell closure' }
    }
  };

  const DEFAULT_CELLS = {
    'cell-research': {
      cell_id: 'cell-research',
      name: 'Research & Analysis',
      color: '#38BDF8',
      route: 'N2',
      surface: 'S3',
      identity: 'I4',
      badge_text: 'S3',
      notes: 'Onion circuit routing with JIT disabled and ephemeral state.'
    },
    'cell-work': {
      cell_id: 'cell-work',
      name: 'Work Workspace',
      color: '#818CF8',
      route: 'N1',
      surface: 'S2',
      identity: 'I2',
      badge_text: 'S2',
      notes: 'Encrypted DNS with dedicated container storage isolation.'
    },
    'cell-detonation': {
      cell_id: 'cell-detonation',
      name: 'Detonation & Triage',
      color: '#EF4444',
      route: 'N2',
      surface: 'S4',
      identity: 'I4',
      badge_text: 'S4',
      notes: 'Static content mode with script execution disabled.'
    },
    'cell-default': {
      cell_id: 'cell-default',
      name: 'Standard Browsing',
      color: '#10B981',
      route: 'N0',
      surface: 'S1',
      identity: 'I1',
      badge_text: 'S1',
      notes: 'Default platform profile with first-party state partitioning.'
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
