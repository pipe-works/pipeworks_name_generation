/*
   ui/navigation.js
   Sections 2-3: top-level tool switching and sub-screen navigation.
*/

'use strict';

/** @type {{
 *   state: Record<string, any>,
 *   populateRender: () => void,
 *   populateAnalysis: () => void
 * } | null} */
let _ctx = null;

/**
 * Initialise tool/screen navigation behavior.
 *
 * @param {{
 *   state: Record<string, any>,
 *   populateRender: () => void,
 *   populateAnalysis: () => void
 * }} ctx - Navigation dependencies and shared state.
 * @returns {void}
 * Side effects:
 * - Registers click handlers on tool tabs and screen tabs.
 */
export function initNavigation(ctx) {
  _ctx = ctx;
  initToolSwitcher();
  initTabNav();
}

/**
 * Wire click handlers for Pipeline/Walker tool tabs.
 *
 * @returns {void}
 */
function initToolSwitcher() {
  document.querySelectorAll('.tool-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      const tool = btn.dataset.tool;
      if (tool === _ctx.state.activeTool) return;
      switchTool(tool);
    });
  });
}

/**
 * Switch the active top-level tool and navigate to that tool's default sub-tab.
 *
 * @param {'pipeline'|'walker'|string} tool - Target tool identifier.
 * @returns {void}
 * Side effects:
 * - Mutates ``state.activeTool``.
 * - Toggles tool tab visual active states.
 * - Shows/hides per-tool sub-nav strips.
 */
function switchTool(tool) {
  _ctx.state.activeTool = tool;

  /* Update tool tab active state */
  document.querySelectorAll('.tool-tab').forEach(b => {
    b.classList.toggle('is-active', b.dataset.tool === tool);
    b.setAttribute('aria-current', b.dataset.tool === tool ? 'true' : 'false');
  });

  /* Show / hide sub-navs */
  document.getElementById('sub-nav-pipeline').classList.toggle('hidden', tool !== 'pipeline');
  document.getElementById('sub-nav-walker').classList.toggle('hidden', tool !== 'walker');

  /* Navigate to the first sub-screen of the selected tool */
  const firstTab = document.querySelector(`#sub-nav-${tool} .tab`);
  if (firstTab) {
    navigateToScreen(firstTab.dataset.screen);
  }

  /* Update status bar context */
  updateStatusBarContext(tool);
}

/**
 * Toggle Pipeline-vs-Walker status widgets in the footer/status bar.
 *
 * @param {'pipeline'|'walker'|string} tool - Active tool key.
 * @returns {void}
 */
export function updateStatusBarContext(tool) {
  document.querySelectorAll('.pipe-context').forEach(el => {
    el.classList.toggle('hidden', tool !== 'pipeline');
  });
  document.querySelectorAll('.walker-context').forEach(el => {
    el.classList.toggle('hidden', tool !== 'walker');
  });
}

/**
 * Wire click handlers for sub-screen tabs.
 *
 * @returns {void}
 */
function initTabNav() {
  document.querySelectorAll('.tab[data-screen]').forEach(btn => {
    btn.addEventListener('click', () => {
      navigateToScreen(btn.dataset.screen);
    });
  });
}

/**
 * Show one screen panel, hide all others, and refresh dynamic screens.
 *
 * @param {string} screenId - Target screen id suffix (without ``screen-`` prefix).
 * @returns {void}
 * Side effects:
 * - Mutates ``state.activeScreen``.
 * - Updates DOM visibility and tab active classes.
 * - Calls render/analysis population callbacks for lazy screens.
 */
export function navigateToScreen(screenId) {
  _ctx.state.activeScreen = screenId;

  /* Hide all screens */
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.remove('is-visible');
    s.hidden = true;
  });

  /* Show target screen */
  const target = document.getElementById(`screen-${screenId}`);
  if (target) {
    target.classList.add('is-visible');
    target.hidden = false;
  }

  /* Update active tab within the current tool's sub-nav */
  const tool = _ctx.state.activeTool;
  document.querySelectorAll(`#sub-nav-${tool} .tab`).forEach(t => {
    t.classList.toggle('is-active', t.dataset.screen === screenId);
  });

  /* Populate screens that need it */
  if (screenId === 'walker-render') _ctx.populateRender();
  if (screenId === 'walker-analysis') _ctx.populateAnalysis();

  window.dispatchEvent(new CustomEvent('pw:screen-changed', {
    detail: { screenId, tool },
  }));
}
