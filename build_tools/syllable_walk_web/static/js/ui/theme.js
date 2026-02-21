/*
   ui/theme.js
   Section 1: Theme toggle behavior.
*/

'use strict';

/**
 * Initialise theme controls and restore persisted theme choice.
 *
 * @returns {void}
 * Side effects:
 * - Reads/writes ``localStorage['pw-theme']``.
 * - Updates root ``data-theme`` and toggle button label.
 */
export function initTheme() {
  const btn = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('pw-theme') || 'dark';
  applyTheme(saved);

  btn.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    applyTheme(next);
    localStorage.setItem('pw-theme', next);
  });
}

/**
 * Apply one of the supported visual themes.
 *
 * @param {'light'|'dark'|string} theme - Theme key to apply.
 * @returns {void}
 * Side effects:
 * - Sets ``document.documentElement.dataset.theme``.
 * - Rewrites theme-toggle button text.
 */
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById('theme-toggle');
  btn.textContent = theme === 'light' ? 'Dark Theme' : 'Light Theme';
}
