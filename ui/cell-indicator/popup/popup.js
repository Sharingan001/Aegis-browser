/**
 * Aegis Browser - Cell Indicator Popup Logic
 */

/* global browser, chrome, CellStore */
const api = typeof browser !== 'undefined' ? browser : chrome;

document.addEventListener('DOMContentLoaded', () => {
  const cellDot = document.getElementById('cell-dot');
  const cellName = document.getElementById('cell-name');
  const cellNotes = document.getElementById('cell-notes');
  const cellBadge = document.getElementById('cell-badge-indicator');

  const networkCode = document.getElementById('network-code');
  const networkTitle = document.getElementById('network-title');
  const networkDesc = document.getElementById('network-desc');

  const surfaceCode = document.getElementById('surface-code');
  const surfaceTitle = document.getElementById('surface-title');
  const surfaceDesc = document.getElementById('surface-desc');

  const identityCode = document.getElementById('identity-code');
  const identityTitle = document.getElementById('identity-title');
  const identityDesc = document.getElementById('identity-desc');

  const cellSelect = document.getElementById('cell-select');

  let currentTabId = null;

  function render(cell, definitions, allCells) {
    if (!cell) return;

    // Active Cell Info
    cellName.textContent = cell.name;
    cellNotes.textContent = cell.notes;
    cellDot.style.backgroundColor = cell.color;
    cellDot.style.boxShadow = `0 0 8px ${cell.color}`;

    cellBadge.textContent = cell.surface;
    cellBadge.style.borderColor = cell.color;
    cellBadge.style.color = cell.color;

    // Network Axis
    const netDef = (definitions && definitions.network && definitions.network[cell.route]) || {
      name: cell.route,
      summary: 'Route active'
    };
    networkCode.textContent = cell.route;
    networkTitle.textContent = netDef.name;
    networkDesc.textContent = netDef.summary;

    // Surface Axis
    const surfDef = (definitions && definitions.surface && definitions.surface[cell.surface]) || {
      name: cell.surface,
      summary: 'Surface profile active'
    };
    surfaceCode.textContent = cell.surface;
    surfaceTitle.textContent = surfDef.name;
    surfaceDesc.textContent = surfDef.summary;

    // Identity Axis
    const identDef = (definitions && definitions.identity && definitions.identity[cell.identity]) || {
      name: cell.identity,
      summary: 'Identity posture active'
    };
    identityCode.textContent = cell.identity;
    identityTitle.textContent = identDef.name;
    identityDesc.textContent = identDef.summary;

    // Switcher Options
    if (cellSelect && allCells && cellSelect.options.length === 0) {
      allCells.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = c.cell_id;
        opt.textContent = `${c.name} (${c.route} / ${c.surface} / ${c.identity})`;
        if (c.cell_id === cell.cell_id) {
          opt.selected = true;
        }
        cellSelect.appendChild(opt);
      });
    } else if (cellSelect) {
      cellSelect.value = cell.cell_id;
    }
  }

  // Determine current tab and load state
  if (api.tabs && api.tabs.query) {
    api.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        currentTabId = tabs[0].id;
      }
      fetchAndRender();
    });
  } else {
    fetchAndRender();
  }

  function fetchAndRender() {
    if (api.runtime && api.runtime.sendMessage) {
      api.runtime.sendMessage(
        { action: 'GET_ACTIVE_CELL', tabId: currentTabId },
        (response) => {
          if (response && response.cell) {
            render(response.cell, response.definitions, response.allCells);
          } else if (typeof CellStore !== 'undefined') {
            fallbackLocalRender();
          }
        }
      );
    } else if (typeof CellStore !== 'undefined') {
      fallbackLocalRender();
    }
  }

  function fallbackLocalRender() {
    const cell = CellStore.getActiveCell();
    const defs = CellStore.getAxisDefinitions();
    const all = CellStore.getAllCells();
    render(cell, defs, all);
  }

  // Handle prototype switcher change
  if (cellSelect) {
    cellSelect.addEventListener('change', (e) => {
      const selectedId = e.target.value;
      if (api.runtime && api.runtime.sendMessage) {
        api.runtime.sendMessage(
          { action: 'SWITCH_CELL', cellId: selectedId, tabId: currentTabId },
          (response) => {
            if (response && response.success) {
              fetchAndRender();
            }
          }
        );
      } else if (typeof CellStore !== 'undefined') {
        CellStore.setActiveCell(selectedId);
        fallbackLocalRender();
      }
    });
  }
});
