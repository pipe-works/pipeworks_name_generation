/*
   core/status.js
   Shared status-bar helpers for the Build Tools frontend.
*/

'use strict';

/**
 * Set the global footer status text.
 *
 * @param {string} msg - Human-readable status message for users.
 * @returns {void}
 * Side effects:
 * - Updates ``#status-text`` if present.
 */
export function setStatus(msg) {
  const el = document.getElementById('status-text');
  if (el) el.textContent = msg;
}
