/*
   core/files.js
   Shared browser file/clipboard helpers used across feature modules.
*/

'use strict';

/**
 * Trigger a client-side download from string content.
 *
 * @param {string} content - File payload text.
 * @param {string} filename - Suggested output filename.
 * @param {string} type - MIME content type.
 * @returns {void}
 * Side effects:
 * - Creates/revokes a blob URL.
 * - Triggers an anchor click download.
 */
export function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
