/*
   walker/corpus-tooltips.js
   Session integrity + lock signal rendering and modal wiring.
*/

'use strict';

import { compactHash } from './corpus-render.js';
import {
  getSessionIntegrityState,
  setSessionIntegrityState,
  setSessionLockState,
} from './corpus-state.js';

/** @typedef {import('./corpus-contracts.js').SessionLockState} SessionLockState */
/** @typedef {import('./corpus-contracts.js').WalkerSessionLoadPatchResult} WalkerSessionLoadPatchResult */
/** @typedef {import('./corpus-contracts.js').WalkerSessionLoadPayload} WalkerSessionLoadPayload */
/** @typedef {import('./corpus-contracts.js').SessionIntegrityState} SessionIntegrityState */

const SESSION_INTEGRITY_META = {
  unknown: {
    label: 'unknown',
    tooltip: 'No session load has been evaluated in this browser tab yet.',
  },
  verified: {
    label: 'verified',
    tooltip: 'Session metadata and current verified run-state artifacts are aligned.',
  },
  stale: {
    label: 'stale',
    tooltip: 'Session metadata is stale, but restore recovered using latest verified run-state.',
  },
  mismatch: {
    label: 'mismatch',
    tooltip: 'Session metadata does not align with current run-state; review before trusting outputs.',
  },
  missing: {
    label: 'missing',
    tooltip: 'Session metadata references artifacts that are missing or unavailable.',
  },
  error: {
    label: 'error',
    tooltip: 'Session integrity check failed due to a read/parse/runtime error.',
  },
};

/**
 * Resolve one session-lock badge class from lock status token.
 *
 * @param {string} status - Session lock status token.
 * @returns {string}
 */
function sessionLockBadgeClass(status) {
  if (status === 'held' || status === 'acquired' || status === 'taken_over') return 'is-verified';
  if (status === 'locked') return 'is-mismatch';
  if (status === 'error') return 'is-error';
  if (status === 'missing') return 'is-missing';
  return 'is-pending';
}

/**
 * Render top-bar lock signal badge/text for session lock state.
 *
 * @param {SessionLockState} lockState - Current lock state model.
 * @returns {void}
 */
export function setSessionLockSignal(lockState) {
  setSessionLockState(lockState);
  const badge = document.getElementById('walker-session-lock-badge');
  const text = document.getElementById('walker-session-lock-text');
  if (!badge || !text) return;

  badge.classList.remove('is-pending', 'is-verified', 'is-mismatch', 'is-missing', 'is-error');
  badge.classList.add(sessionLockBadgeClass(lockState.status));
  let label = lockState.status || 'unlocked';
  if (label === 'taken_over') label = 'taken-over';
  badge.textContent = label;

  const holderId = (lockState.lock && typeof lockState.lock.holder_id === 'string')
    ? lockState.lock.holder_id
    : null;
  const expiresAt = (lockState.lock && typeof lockState.lock.expires_at_utc === 'string')
    ? lockState.lock.expires_at_utc
    : null;
  text.textContent = holderId
    ? `holder ${compactHash(holderId)}${expiresAt ? ` · exp ${expiresAt.slice(11, 19)}Z` : ''}`
    : (lockState.reason || 'no lock metadata');

  const titleParts = [];
  if (typeof lockState.reason === 'string' && lockState.reason.length > 0) {
    titleParts.push(lockState.reason);
  }
  if (holderId) titleParts.push(`holder: ${holderId}`);
  if (expiresAt) titleParts.push(`expires: ${expiresAt}`);
  const title = titleParts.join('\n');
  if (title.length > 0) {
    badge.title = title;
    text.title = title;
  } else {
    badge.removeAttribute('title');
    text.removeAttribute('title');
  }
}

/**
 * Resolve one session-integrity badge class from a normalized status token.
 *
 * @param {'unknown'|'verified'|'stale'|'mismatch'|'missing'|'error'} status - Integrity status.
 * @returns {string}
 */
function sessionIntegrityBadgeClass(status) {
  if (status === 'verified') return 'is-verified';
  if (status === 'stale') return 'is-stale';
  if (status === 'mismatch') return 'is-mismatch';
  if (status === 'missing') return 'is-missing';
  if (status === 'error') return 'is-error';
  return 'is-pending';
}

/**
 * Resolve one concise session-integrity state from load-session API payload.
 *
 * @param {unknown} rawPayload - ``/api/walker/load-session`` response payload.
 * @returns {SessionIntegrityState}
 */
export function deriveSessionIntegrity(rawPayload) {
  if (!rawPayload || typeof rawPayload !== 'object') {
    return {
      status: 'unknown',
      reason: SESSION_INTEGRITY_META.unknown.tooltip,
      recoveredFromStale: false,
      patchA: null,
      patchB: null,
      topStatus: 'unknown',
      topReason: 'not evaluated',
    };
  }

  const payload = /** @type {WalkerSessionLoadPayload} */ (rawPayload);
  const topStatus = (typeof payload.status === 'string' && payload.status.length > 0)
    ? payload.status
    : 'unknown';
  const topReason = (typeof payload.reason === 'string' && payload.reason.length > 0)
    ? payload.reason
    : 'not-evaluated';
  const recoveredFromStale = Boolean(payload.recovered_from_stale_session);
  const patchA = payload.patch_a && typeof payload.patch_a === 'object' ? payload.patch_a : null;
  const patchB = payload.patch_b && typeof payload.patch_b === 'object' ? payload.patch_b : null;
  const patchStatuses = [patchA, patchB]
    .map(p => (p && typeof p.verification_status === 'string') ? p.verification_status : null)
    .filter(Boolean);

  let status = 'unknown';
  if (recoveredFromStale) {
    status = 'stale';
  } else if (patchStatuses.includes('error') || topStatus === 'error') {
    status = 'error';
  } else if (patchStatuses.includes('mismatch') || topStatus === 'mismatch') {
    status = 'mismatch';
  } else if (topStatus === 'missing') {
    status = 'missing';
  } else if (topStatus === 'verified') {
    status = 'verified';
  }

  const defaultReason = SESSION_INTEGRITY_META[status]
    ? SESSION_INTEGRITY_META[status].tooltip
    : SESSION_INTEGRITY_META.unknown.tooltip;
  const reason = (typeof topReason === 'string' && topReason !== 'not-evaluated')
    ? topReason
    : defaultReason;

  return {
    status,
    reason,
    recoveredFromStale,
    patchA,
    patchB,
    topStatus,
    topReason,
  };
}

/**
 * Render the top-bar Session Integrity badge, tooltip, and reason text.
 *
 * @param {SessionIntegrityState} integrity - Session-integrity model.
 * @returns {void}
 */
export function setSessionIntegrity(integrity) {
  setSessionIntegrityState(integrity);
  const badge = document.getElementById('walker-session-integrity-badge');
  const text = document.getElementById('walker-session-integrity-text');
  if (!badge || !text) return;

  const meta = SESSION_INTEGRITY_META[integrity.status] || SESSION_INTEGRITY_META.unknown;
  badge.classList.remove(
    'is-pending',
    'is-verified',
    'is-mismatch',
    'is-missing',
    'is-error',
    'is-stale'
  );
  badge.classList.add(sessionIntegrityBadgeClass(integrity.status));
  badge.textContent = meta.label;
  badge.title = `${meta.tooltip} Reason: ${integrity.reason}`;
  text.textContent = integrity.recoveredFromStale
    ? 'recovered via latest run-state'
    : integrity.reason;
  text.title = integrity.reason;
}

/**
 * Build one short patch detail line for Session Integrity modal rendering.
 *
 * @param {string} label - Patch label ("A" or "B").
 * @param {WalkerSessionLoadPatchResult | null} patchResult - Patch result object from API.
 * @returns {string}
 */
function sessionIntegrityPatchDetail(label, patchResult) {
  if (!patchResult) return `Patch ${label}: not present in load response.`;
  const loaded = patchResult.loaded ? 'loaded' : 'not-loaded';
  const restored = patchResult.restored ? 'restored' : 'not-restored';
  const verification = (typeof patchResult.verification_status === 'string')
    ? patchResult.verification_status
    : 'unknown';
  const reason = (typeof patchResult.verification_reason === 'string')
    ? patchResult.verification_reason
    : 'no-reason';
  return `Patch ${label}: ${loaded}, ${restored}, verification=${verification}, reason=${reason}`;
}

/**
 * Render the Session Integrity modal content from current in-memory state.
 *
 * @returns {void}
 */
function renderSessionIntegrityModal() {
  const tbody = document.getElementById('session-integrity-modal-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const integrity = getSessionIntegrityState();
  const meta = SESSION_INTEGRITY_META[integrity.status] || SESSION_INTEGRITY_META.unknown;
  const rows = [
    ['Current State', meta.label.toUpperCase()],
    ['Short Meaning', meta.tooltip],
    ['Current Reason', integrity.reason],
    ['Patch A', sessionIntegrityPatchDetail('A', integrity.patchA)],
    ['Patch B', sessionIntegrityPatchDetail('B', integrity.patchB)],
    [
      'Compared To Patch Comparison',
      'Patch Comparison checks current Patch A/B corpus baseline relation (same/different). Session Integrity checks saved-session freshness and run-state trust.',
    ],
    [
      'Recovery Policy',
      'When stale hash drift is detected and recoverable, the API keeps warning status but restores using latest verified run-state artifacts.',
    ],
    [
      'Repair to Verified',
      'Use the "Repair Session" button after loading the selected session. This creates a new immutable revision linked to the original session, using current verified run-state references.',
    ],
  ];

  rows.forEach(([heading, content]) => {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = heading;
    const td = document.createElement('td');
    td.textContent = content;
    tr.appendChild(th);
    tr.appendChild(td);
    tbody.appendChild(tr);
  });
}

/**
 * Initialise Session Integrity modal open/close handlers.
 *
 * @returns {void}
 */
export function initSessionIntegrityModal() {
  const modal = document.getElementById('session-integrity-modal');
  const backdrop = document.getElementById('session-integrity-modal-backdrop');
  const closeBtn = document.getElementById('session-integrity-modal-close');
  const infoBtn = document.getElementById('walker-session-integrity-info');
  if (!modal || !infoBtn) return;

  infoBtn.addEventListener('click', () => {
    renderSessionIntegrityModal();
    modal.classList.remove('hidden');
  });

  [backdrop, closeBtn].forEach(el => {
    el?.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      modal.classList.add('hidden');
    }
  });
}

/**
 * Render a concise summary line for one session load result.
 *
 * @param {WalkerSessionLoadPayload} payload - ``/api/walker/load-session`` payload.
 * @returns {string}
 */
export function formatSessionLoadSummary(payload) {
  const sessionId = (payload && typeof payload.session_id === 'string') ? payload.session_id : 'unknown-session';
  const patchA = payload && payload.patch_a ? payload.patch_a : {};
  const patchB = payload && payload.patch_b ? payload.patch_b : {};
  const formatPatchOutcome = patchResult => {
    const verification = (patchResult && typeof patchResult.verification_status === 'string')
      ? patchResult.verification_status
      : 'unknown';
    let state = 'skipped';
    if (patchResult && patchResult.restored === true) {
      state = 'restored';
    } else if (verification === 'mismatch') {
      state = 'stale';
    } else if (verification === 'error') {
      state = 'error';
    } else if (patchResult && patchResult.loaded) {
      state = 'loaded';
    }
    return `${state}/${verification}`;
  };
  const recoveredFromStale = Boolean(payload && payload.recovered_from_stale_session);
  const stalePrefix = recoveredFromStale ? 'stale-session recovered · ' : '';
  return `${stalePrefix}${sessionId} · A ${formatPatchOutcome(patchA)} · B ${formatPatchOutcome(patchB)}`;
}
