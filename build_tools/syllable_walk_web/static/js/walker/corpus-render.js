/*
   walker/corpus-render.js
   DOM render helpers for walker corpus/session micro-state.
*/

'use strict';

const REBUILD_REACH_META = {
  idle: {
    badge: 'idle',
    badgeClass: 'is-pending',
  },
  rebuilding: {
    badge: 'running',
    badgeClass: 'is-pending',
  },
  verified: {
    badge: 'verified',
    badgeClass: 'is-verified',
  },
  recommended: {
    badge: 'rebuild',
    badgeClass: 'is-mismatch',
  },
  missing: {
    badge: 'missing',
    badgeClass: 'is-missing',
  },
  rebuilt: {
    badge: 'rebuilt',
    badgeClass: 'is-verified',
  },
  error: {
    badge: 'error',
    badgeClass: 'is-error',
  },
};

/**
 * Apply corpus status text with a semantic visual state.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {string} text - Status text to render.
 * @param {'neutral'|'loaded'|'error'} [state='neutral'] - Visual state token.
 * @returns {void}
 */
export function setCorpusStatus(patch, text, state = 'neutral') {
  const el = document.getElementById(`corpus-status-${patch}`);
  if (!el) return;

  el.textContent = text;
  el.classList.remove('is-loaded', 'is-error');
  if (state === 'loaded') {
    el.classList.add('is-loaded');
  } else if (state === 'error') {
    el.classList.add('is-error');
  }
}

/**
 * Compact a full SHA-256 hash for narrow UI rendering.
 *
 * @param {unknown} value - Candidate hash value.
 * @returns {string}
 */
export function compactHash(value) {
  if (typeof value !== 'string' || value.length < 16) return '—';
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

/**
 * Render one "in/out" hash pair label.
 *
 * @param {unknown} inputHash - IPC input hash.
 * @param {unknown} outputHash - IPC output hash.
 * @returns {string}
 */
function formatHashPair(inputHash, outputHash) {
  return `in ${compactHash(inputHash)} · out ${compactHash(outputHash)}`;
}

/**
 * Update manifest/cache hash rows for one patch corpus panel.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {unknown} manifestInputHash - Manifest IPC input hash.
 * @param {unknown} manifestOutputHash - Manifest IPC output hash.
 * @param {unknown} cacheInputHash - Reach-cache IPC input hash.
 * @param {unknown} cacheOutputHash - Reach-cache IPC output hash.
 * @returns {void}
 */
export function setCorpusHashes(
  patch,
  manifestInputHash,
  manifestOutputHash,
  cacheInputHash,
  cacheOutputHash
) {
  const manifestEl = document.getElementById(`corpus-manifest-ipc-${patch}`);
  const cacheEl = document.getElementById(`corpus-cache-ipc-${patch}`);
  if (!manifestEl || !cacheEl) return;

  manifestEl.textContent = formatHashPair(manifestInputHash, manifestOutputHash);
  cacheEl.textContent = formatHashPair(cacheInputHash, cacheOutputHash);

  if (typeof manifestInputHash === 'string' || typeof manifestOutputHash === 'string') {
    const inText = typeof manifestInputHash === 'string' ? manifestInputHash : '—';
    const outText = typeof manifestOutputHash === 'string' ? manifestOutputHash : '—';
    manifestEl.title = `in: ${inText}\nout: ${outText}`;
  } else {
    manifestEl.removeAttribute('title');
  }

  if (typeof cacheInputHash === 'string' || typeof cacheOutputHash === 'string') {
    const inText = typeof cacheInputHash === 'string' ? cacheInputHash : '—';
    const outText = typeof cacheOutputHash === 'string' ? cacheOutputHash : '—';
    cacheEl.title = `in: ${inText}\nout: ${outText}`;
  } else {
    cacheEl.removeAttribute('title');
  }
}

/**
 * Resolve rebuild signal state from one cache verification token.
 *
 * @param {unknown} verificationStatus - Cache verification status from API.
 * @returns {'idle'|'verified'|'recommended'|'missing'|'error'}
 */
export function rebuildStateFromVerification(verificationStatus) {
  if (verificationStatus === 'verified') return 'verified';
  if (verificationStatus === 'mismatch') return 'recommended';
  if (verificationStatus === 'missing') return 'missing';
  if (verificationStatus === 'error') return 'error';
  return 'idle';
}

/**
 * Update one patch rebuild micro-signal (badge + text).
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {{
 *   state?: 'idle'|'rebuilding'|'verified'|'recommended'|'missing'|'rebuilt'|'error',
 *   reason?: unknown,
 *   inputHash?: unknown,
 *   outputHash?: unknown
 * }} [model={}] - Rebuild state model.
 * @returns {void}
 */
export function setRebuildStatus(patch, model = {}) {
  const statusEl = document.getElementById(`rebuild-reach-status-${patch}`);
  const badgeEl = document.getElementById(`rebuild-reach-badge-${patch}`);
  if (!statusEl || !badgeEl) return;

  const rawState = (model && typeof model.state === 'string') ? model.state : 'idle';
  const state = Object.prototype.hasOwnProperty.call(REBUILD_REACH_META, rawState) ? rawState : 'idle';
  const reason = (model && typeof model.reason === 'string') ? model.reason : '';
  const inputHash = model ? model.inputHash : null;
  const outputHash = model ? model.outputHash : null;
  const hasHashes = typeof inputHash === 'string' || typeof outputHash === 'string';

  const meta = REBUILD_REACH_META[state];
  badgeEl.classList.remove('is-pending', 'is-verified', 'is-mismatch', 'is-missing', 'is-error', 'is-stale');
  badgeEl.classList.add(meta.badgeClass);
  badgeEl.textContent = meta.badge;

  if (state === 'verified' || state === 'rebuilt') {
    statusEl.textContent = hasHashes ? formatHashPair(inputHash, outputHash) : 'ipc hashes unavailable';
  } else if (state === 'recommended') {
    statusEl.textContent = `rebuild recommended${reason ? ` · ${reason}` : ''}`;
  } else if (state === 'missing') {
    statusEl.textContent = `cache missing${reason ? ` · ${reason}` : ''}`;
  } else if (state === 'rebuilding') {
    statusEl.textContent = 'computing reaches + writing IPC sidecar…';
  } else if (state === 'error') {
    statusEl.textContent = `rebuild failed${reason ? ` · ${reason}` : ''}`;
  } else {
    statusEl.textContent = 'no rebuild yet';
  }

  statusEl.removeAttribute('title');
  badgeEl.removeAttribute('title');
}

/**
 * Normalise verification status to one known token.
 *
 * @param {unknown} value - Raw status from API.
 * @returns {'pending'|'verified'|'mismatch'|'missing'|'error'}
 */
function normalizeVerificationStatus(value) {
  if (value === 'verified') return 'verified';
  if (value === 'mismatch') return 'mismatch';
  if (value === 'missing') return 'missing';
  if (value === 'error') return 'error';
  return 'pending';
}

/**
 * Human-readable short label for one verification status token.
 *
 * @param {'pending'|'verified'|'mismatch'|'missing'|'error'} status - Normalized status.
 * @returns {string}
 */
function verificationLabel(status) {
  if (status === 'verified') return 'verified';
  if (status === 'mismatch') return 'mismatch';
  if (status === 'missing') return 'missing';
  if (status === 'error') return 'error';
  return 'pending';
}

/**
 * Update one hash verification badge element.
 *
 * @param {HTMLElement | null} element - Badge element.
 * @param {unknown} rawStatus - Raw status from API.
 * @param {unknown} rawReason - Optional reason from API.
 * @returns {void}
 */
function setHashBadge(element, rawStatus, rawReason) {
  if (!element) return;
  const status = normalizeVerificationStatus(rawStatus);
  element.classList.remove('is-pending', 'is-verified', 'is-mismatch', 'is-missing', 'is-error');
  element.classList.add(`is-${status}`);
  element.textContent = verificationLabel(status);
  if (typeof rawReason === 'string' && rawReason.length > 0) {
    element.title = rawReason;
  } else {
    element.removeAttribute('title');
  }
}

/**
 * Update manifest/cache verification badges for one patch corpus panel.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {unknown} manifestStatus - Manifest verification status.
 * @param {unknown} manifestReason - Manifest verification reason.
 * @param {unknown} cacheStatus - Reach-cache verification status.
 * @param {unknown} cacheReason - Reach-cache verification reason.
 * @returns {void}
 */
export function setCorpusHashVerification(
  patch,
  manifestStatus,
  manifestReason,
  cacheStatus,
  cacheReason
) {
  setHashBadge(document.getElementById(`corpus-manifest-ipc-badge-${patch}`), manifestStatus, manifestReason);
  setHashBadge(document.getElementById(`corpus-cache-ipc-badge-${patch}`), cacheStatus, cacheReason);
}

/**
 * Normalize patch comparison relation from stats payload.
 *
 * @param {unknown} rawRelation - API relation token.
 * @returns {'same'|'different'|'unknown'}
 */
function normalizePatchRelation(rawRelation) {
  if (rawRelation === 'same') return 'same';
  if (rawRelation === 'different') return 'different';
  return 'unknown';
}

/**
 * Update the top-bar patch comparison badge and text.
 *
 * @param {unknown} rawComparison - ``patch_comparison`` payload from stats API.
 * @returns {void}
 */
export function setPatchComparison(rawComparison) {
  const badge = document.getElementById('walker-patch-compare-badge');
  const text = document.getElementById('walker-patch-compare-text');
  if (!badge || !text) return;

  const relation = normalizePatchRelation(rawComparison && rawComparison.corpus_hash_relation);
  const policy = (rawComparison && typeof rawComparison.policy === 'string') ? rawComparison.policy : 'none';
  const reason = (rawComparison && typeof rawComparison.reason === 'string') ? rawComparison.reason : '';

  badge.classList.remove('is-pending', 'is-verified', 'is-mismatch', 'is-missing', 'is-error');
  if (relation === 'same') {
    badge.classList.add('is-verified');
  } else if (relation === 'different') {
    badge.classList.add('is-mismatch');
  } else {
    badge.classList.add('is-pending');
  }
  badge.textContent = relation;
  text.textContent = `policy ${policy}`;

  if (reason.length > 0) {
    badge.title = reason;
    text.title = reason;
  } else {
    badge.removeAttribute('title');
    text.removeAttribute('title');
  }
}
