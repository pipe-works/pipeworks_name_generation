/*
   walker/corpus.js
   Section 10: walker corpus dropdown loading and walker-readiness polling.
*/

'use strict';

/** @type {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void,
 *   updateReachValues: (patch: string, reaches: Record<string, any>) => void
 * } | null} */
let _ctx = null;

/* per-patch run lists from /api/pipeline/runs */
let _corpusRunsByPatch = { a: [], b: [] };
/* { a: intervalId, b: intervalId } - per-patch polling timers */
let _walkerReadyPollers = {};
/* saved sessions map keyed by session_id */
let _sessionEntriesById = {};
/* last computed session integrity state for tooltip/modal rendering */
let _sessionIntegrityState = {
  status: 'unknown',
  reason: 'No session load has been evaluated yet.',
  recoveredFromStale: false,
  patchA: null,
  patchB: null,
  topStatus: 'unknown',
  topReason: 'not evaluated',
};
/* active session-lock status for this browser tab */
let _sessionLockState = {
  status: 'unlocked',
  reason: 'No session lock held.',
  sessionId: null,
  lock: null,
};
let _sessionLockHeartbeatTimer = null;

const SESSION_LOCK_HOLDER_STORAGE_KEY = 'pipeworks.walker.lock_holder_id';
const SESSION_LOCK_HEARTBEAT_MS = 10_000;

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

const REBUILD_REACH_META = {
  idle: {
    badge: 'idle',
    badgeClass: 'is-pending',
    tooltip: 'No rebuild action in this tab yet.',
  },
  rebuilding: {
    badge: 'running',
    badgeClass: 'is-pending',
    tooltip: 'Reach tables are being recomputed and IPC sidecar hashes rewritten.',
  },
  verified: {
    badge: 'verified',
    badgeClass: 'is-verified',
    tooltip: 'Reach Cache IPC is aligned with current run-local artifacts.',
  },
  recommended: {
    badge: 'rebuild',
    badgeClass: 'is-mismatch',
    tooltip: 'Reach Cache IPC mismatch detected. Rebuild is recommended.',
  },
  missing: {
    badge: 'missing',
    badgeClass: 'is-missing',
    tooltip: 'Reach Cache IPC artifact is missing. Rebuild is recommended.',
  },
  rebuilt: {
    badge: 'rebuilt',
    badgeClass: 'is-verified',
    tooltip: 'Reach cache was rebuilt and new IPC hashes were written.',
  },
  error: {
    badge: 'error',
    badgeClass: 'is-error',
    tooltip: 'Reach cache rebuild/verification failed.',
  },
};

/**
 * Return stable per-tab lock holder id used for cooperative session locking.
 *
 * This is intentionally not identity/auth data; it only distinguishes tabs in
 * the same browser profile for single-user coordination.
 *
 * @returns {string}
 */
export function getWalkerSessionLockHolderId() {
  if (typeof window === 'undefined') {
    return 'holder-nonbrowser';
  }
  const storage = window.sessionStorage;
  const existing = storage.getItem(SESSION_LOCK_HOLDER_STORAGE_KEY);
  if (typeof existing === 'string' && existing.length > 0) {
    return existing;
  }
  const randomPart = Math.random().toString(16).slice(2, 10);
  const holderId = `holder_${Date.now().toString(16)}_${randomPart}`;
  storage.setItem(SESSION_LOCK_HOLDER_STORAGE_KEY, holderId);
  return holderId;
}

/**
 * Resolve one run object's canonical run id.
 *
 * @param {{run_id?: string, path?: string}} run - Run payload from API.
 * @returns {string}
 */
function getRunId(run) {
  if (run && typeof run.run_id === 'string' && run.run_id.length > 0) {
    return run.run_id;
  }
  return '';
}

/**
 * Apply corpus status text with a semantic visual state.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {string} text - Status text to render.
 * @param {'neutral'|'loaded'|'error'} [state='neutral'] - Visual state token.
 * @returns {void}
 */
function setCorpusStatus(patch, text, state = 'neutral') {
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
function compactHash(value) {
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
function setCorpusHashes(patch, manifestInputHash, manifestOutputHash, cacheInputHash, cacheOutputHash) {
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
function rebuildStateFromVerification(verificationStatus) {
  if (verificationStatus === 'verified') return 'verified';
  if (verificationStatus === 'mismatch') return 'recommended';
  if (verificationStatus === 'missing') return 'missing';
  if (verificationStatus === 'error') return 'error';
  return 'idle';
}

/**
 * Update one patch rebuild micro-signal (badge + text + tooltip).
 *
 * This is the Level 1+2 state for rebuild guidance:
 * - Level 1: compact semantic badge (idle/rebuild/verified/error/etc.)
 * - Level 2: tooltip/status text indicating why a rebuild may be needed
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
function setRebuildStatus(patch, model = {}) {
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
function setCorpusHashVerification(
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
function setPatchComparison(rawComparison) {
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
 * @param {{
 *   status: string,
 *   reason: string,
 *   sessionId: string | null,
 *   lock: Record<string, any> | null
 * }} lockState - Current lock state model.
 * @returns {void}
 */
function setSessionLockSignal(lockState) {
  _sessionLockState = lockState;
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
 * @returns {{
 *   status: 'unknown'|'verified'|'stale'|'mismatch'|'missing'|'error',
 *   reason: string,
 *   recoveredFromStale: boolean,
 *   patchA: Record<string, any> | null,
 *   patchB: Record<string, any> | null,
 *   topStatus: string,
 *   topReason: string
 * }}
 */
function deriveSessionIntegrity(rawPayload) {
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

  const payload = /** @type {Record<string, any>} */ (rawPayload);
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
 * @param {{
 *   status: 'unknown'|'verified'|'stale'|'mismatch'|'missing'|'error',
 *   reason: string,
 *   recoveredFromStale: boolean,
 *   patchA: Record<string, any> | null,
 *   patchB: Record<string, any> | null,
 *   topStatus: string,
 *   topReason: string
 * }} integrity - Session-integrity model.
 * @returns {void}
 */
function setSessionIntegrity(integrity) {
  _sessionIntegrityState = integrity;
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
 * @param {Record<string, any> | null} patchResult - Patch result object from API.
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

  const meta = SESSION_INTEGRITY_META[_sessionIntegrityState.status] || SESSION_INTEGRITY_META.unknown;
  const rows = [
    ['Current State', meta.label.toUpperCase()],
    ['Short Meaning', meta.tooltip],
    ['Current Reason', _sessionIntegrityState.reason],
    ['Patch A', sessionIntegrityPatchDetail('A', _sessionIntegrityState.patchA)],
    ['Patch B', sessionIntegrityPatchDetail('B', _sessionIntegrityState.patchB)],
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
function initSessionIntegrityModal() {
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
 * Build a compact label for session dropdown options.
 *
 * @param {Record<string, any>} entry - One session list entry from API.
 * @returns {string}
 */
function formatSessionOptionLabel(entry) {
  const sessionId = (entry && typeof entry.session_id === 'string') ? entry.session_id : 'unknown-session';
  const created = (entry && typeof entry.created_at_utc === 'string')
    ? entry.created_at_utc.replace('T', ' ').slice(0, 16)
    : 'unknown time';
  const label = (entry && typeof entry.label === 'string' && entry.label.trim().length > 0)
    ? entry.label.trim()
    : null;
  const patchA = (entry && typeof entry.patch_a_run_id === 'string') ? entry.patch_a_run_id : '—';
  const patchB = (entry && typeof entry.patch_b_run_id === 'string') ? entry.patch_b_run_id : '—';
  const verification = (entry && typeof entry.verification_status === 'string')
    ? entry.verification_status
    : 'unknown';
  const verificationReason = (entry && typeof entry.verification_reason === 'string')
    ? entry.verification_reason
    : '';
  const verificationLabel = (
    verification === 'mismatch' && verificationReason.endsWith('run-state-output-hash-mismatch')
  )
    ? 'stale-session'
    : verification;
  const revision = (entry && Number.isInteger(entry.revision) && entry.revision >= 0)
    ? entry.revision
    : 0;
  const rootSessionId = (entry && typeof entry.root_session_id === 'string' && entry.root_session_id.length > 0)
    ? entry.root_session_id
    : sessionId;
  const lineageLabel = revision > 0
    ? `r${revision} of ${rootSessionId}`
    : 'r0 original';
  const lockStatus = (entry && typeof entry.lock_status === 'string')
    ? entry.lock_status
    : 'unlocked';
  const lock = (entry && entry.lock && typeof entry.lock === 'object') ? entry.lock : null;
  const lockHolder = (lock && typeof lock.holder_id === 'string') ? lock.holder_id : null;
  const lockExpires = (lock && typeof lock.expires_at_utc === 'string')
    ? lock.expires_at_utc
    : null;
  const holderId = getWalkerSessionLockHolderId();
  let lockLabel = 'lock:free';
  if (lockStatus === 'locked') {
    if (lockHolder && lockHolder === holderId) {
      lockLabel = 'lock:self';
    } else {
      lockLabel = lockExpires
        ? `LOCKED(other) ${lockExpires.slice(11, 19)}Z`
        : 'LOCKED(other)';
    }
  }

  const labelPrefix = label ? `${label} · ` : '';
  return `${labelPrefix}${created} · ${sessionId} · ${lineageLabel} · A ${patchA} · B ${patchB} · ${verificationLabel} · ${lockLabel}`;
}

/**
 * Render a concise summary line for one session load result.
 *
 * @param {Record<string, any>} payload - ``/api/walker/load-session`` payload.
 * @returns {string}
 */
function formatSessionLoadSummary(payload) {
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

/**
 * Stop lock heartbeat polling timer for this tab.
 *
 * @returns {void}
 */
function stopSessionLockHeartbeat() {
  if (_sessionLockHeartbeatTimer) {
    clearInterval(_sessionLockHeartbeatTimer);
    _sessionLockHeartbeatTimer = null;
  }
}

/**
 * Send one lock heartbeat for the active loaded session.
 *
 * @param {string} sessionId - Session id to heartbeat.
 * @returns {Promise<void>}
 */
async function sendSessionLockHeartbeat(sessionId) {
  const holderId = getWalkerSessionLockHolderId();
  const response = await fetch('/api/walker/session-lock/heartbeat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      lock_holder_id: holderId,
    }),
  });
  const payload = await response.json();
  if (payload.error) {
    throw new Error(payload.error);
  }
  setSessionLockSignal({
    status: payload.status || 'held',
    reason: payload.reason || 'session lock refreshed',
    sessionId,
    lock: (payload.lock && typeof payload.lock === 'object') ? payload.lock : null,
  });
}

/**
 * Start periodic heartbeat for one acquired session lock.
 *
 * @param {string} sessionId - Session id currently owned by this tab.
 * @returns {void}
 */
function startSessionLockHeartbeat(sessionId) {
  stopSessionLockHeartbeat();
  if (!sessionId) return;
  _sessionLockHeartbeatTimer = setInterval(() => {
    sendSessionLockHeartbeat(sessionId).catch(err => {
      stopSessionLockHeartbeat();
      setSessionLockSignal({
        status: 'error',
        reason: `lock heartbeat failed: ${err.message}`,
        sessionId,
        lock: null,
      });
    });
  }, SESSION_LOCK_HEARTBEAT_MS);
}

/**
 * Release one session lock owned by this tab.
 *
 * @param {string} sessionId - Session id to release.
 * @returns {Promise<Record<string, any>>}
 */
async function releaseSessionLock(sessionId) {
  const holderId = getWalkerSessionLockHolderId();
  const response = await fetch('/api/walker/session-lock/release', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      lock_holder_id: holderId,
    }),
  });
  const payload = await response.json();
  if (payload.error) {
    throw new Error(payload.error);
  }
  return payload;
}

/**
 * Update lock signal + heartbeat from one load-session payload.
 *
 * @param {Record<string, any>} payload - Load-session response payload.
 * @param {string} sessionId - Requested/loaded session id.
 * @returns {void}
 */
function applySessionLockFromLoadPayload(payload, sessionId) {
  const lockBlock = (payload && payload.session_lock && typeof payload.session_lock === 'object')
    ? payload.session_lock
    : null;
  const status = (lockBlock && typeof lockBlock.status === 'string') ? lockBlock.status : 'unlocked';
  const reason = (lockBlock && typeof lockBlock.reason === 'string') ? lockBlock.reason : 'no-lock-holder';
  const lock = (lockBlock && lockBlock.lock && typeof lockBlock.lock === 'object') ? lockBlock.lock : null;
  setSessionLockSignal({
    status,
    reason,
    sessionId,
    lock,
  });
  if (status === 'acquired' || status === 'held' || status === 'taken_over') {
    startSessionLockHeartbeat(sessionId);
    return;
  }
  stopSessionLockHeartbeat();
}

/**
 * Refresh session dropdown options from API.
 *
 * @param {{selectedId?: string | null, showLoadingSummary?: boolean}} [opts]
 *   - Optional selection override and loading-indicator behavior.
 * @returns {Promise<void>}
 */
async function refreshSessionList(opts = {}) {
  const select = document.getElementById('walker-session-select');
  if (!select) return;
  const summaryEl = document.getElementById('walker-session-summary');
  const loadBtn = document.getElementById('walker-load-session');
  const repairBtn = document.getElementById('walker-repair-session');
  const takeoverBtn = document.getElementById('walker-takeover-session-lock');

  const selectedId = (typeof opts.selectedId === 'string') ? opts.selectedId : select.value;
  const shouldShowLoadingSummary = opts.showLoadingSummary !== false;
  const placeholder = select.options[0] || null;
  const previousSummary = summaryEl ? summaryEl.textContent : '';
  if (placeholder) {
    placeholder.textContent = '-- Loading saved sessions --';
  }
  if (shouldShowLoadingSummary && summaryEl) {
    summaryEl.textContent = 'Loading saved sessions…';
    summaryEl.classList.add('is-loading');
  }
  select.disabled = true;
  if (loadBtn) loadBtn.disabled = true;
  if (repairBtn) repairBtn.disabled = true;
  if (takeoverBtn) takeoverBtn.disabled = true;

  let payload = null;
  try {
    const response = await fetch('/api/walker/sessions');
    payload = await response.json();
  } catch (err) {
    _ctx.setStatus(`Failed to load sessions: ${err.message}`);
  } finally {
    if (payload && payload.error) {
      _ctx.setStatus(`Failed to load sessions: ${payload.error}`);
    } else if (payload) {
      const sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
      _sessionEntriesById = {};
      sessions.forEach(entry => {
        if (entry && typeof entry.session_id === 'string' && entry.session_id.length > 0) {
          _sessionEntriesById[entry.session_id] = entry;
        }
      });

      while (select.options.length > 1) {
        select.remove(1);
      }

      sessions.forEach(entry => {
        if (!entry || typeof entry.session_id !== 'string' || entry.session_id.length === 0) return;
        const option = document.createElement('option');
        option.value = entry.session_id;
        option.textContent = formatSessionOptionLabel(entry);
        select.appendChild(option);
      });

      if (selectedId && Object.prototype.hasOwnProperty.call(_sessionEntriesById, selectedId)) {
        select.value = selectedId;
      } else {
        select.value = '';
      }
    }

    if (placeholder) {
      placeholder.textContent = '-- Select saved session --';
    }
    select.disabled = false;
    if (loadBtn) loadBtn.disabled = false;
    if (repairBtn) repairBtn.disabled = false;
    if (takeoverBtn) takeoverBtn.disabled = false;
    if (
      shouldShowLoadingSummary
      && summaryEl
      && summaryEl.textContent === 'Loading saved sessions…'
    ) {
      summaryEl.textContent = previousSummary || 'No session activity yet.';
    }
    if (summaryEl) {
      summaryEl.classList.remove('is-loading');
    }
  }
}

/**
 * Request fresh walker stats and sync hash/compare micro-state.
 *
 * @returns {Promise<void>}
 */
async function refreshWalkerStatsMicroState() {
  let stats;
  try {
    const response = await fetch('/api/walker/stats');
    stats = await response.json();
  } catch {
    return;
  }
  ['a', 'b'].forEach(patch => {
    const info = stats ? stats[`patch_${patch}`] : null;
    if (!info) return;
    setCorpusHashes(
      patch,
      info.manifest_ipc_input_hash,
      info.manifest_ipc_output_hash,
      info.reach_cache_ipc_input_hash,
      info.reach_cache_ipc_output_hash
    );
    setCorpusHashVerification(
      patch,
      info.manifest_ipc_verification_status,
      info.manifest_ipc_verification_reason,
      info.reach_cache_ipc_verification_status,
      info.reach_cache_ipc_verification_reason
    );
    setRebuildStatus(
      patch,
      {
        state: rebuildStateFromVerification(info.reach_cache_ipc_verification_status),
        reason: info.reach_cache_ipc_verification_reason,
        inputHash: info.reach_cache_ipc_input_hash,
        outputHash: info.reach_cache_ipc_output_hash,
      }
    );
    if (info.reaches) {
      _ctx.updateReachValues(patch, info.reaches);
    }
  });
  setPatchComparison(stats ? stats.patch_comparison : null);
}

/**
 * Initialise corpus dropdown selectors and load initial run options.
 *
 * @param {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void,
 *   updateReachValues: (patch: string, reaches: Record<string, any>) => void
 * }} ctx - Shared state and reach-update callback.
 * @returns {void}
 */
export function initCorpus(ctx) {
  _ctx = ctx;
  initCorpusDropdowns();
  initSessionControls();
  initSessionIntegrityModal();
  setSessionIntegrity(deriveSessionIntegrity(null));
  setSessionLockSignal({
    status: 'unlocked',
    reason: 'No session lock held.',
    sessionId: null,
    lock: null,
  });
  window.addEventListener('beforeunload', () => {
    if (
      !_sessionLockState
      || !_sessionLockState.sessionId
      || !['acquired', 'held', 'taken_over'].includes(_sessionLockState.status)
    ) {
      return;
    }
    const holderId = getWalkerSessionLockHolderId();
    const body = JSON.stringify({
      session_id: _sessionLockState.sessionId,
      lock_holder_id: holderId,
    });
    try {
      navigator.sendBeacon('/api/walker/session-lock/release', body);
    } catch {
      /* best-effort release only */
    }
  });
  refreshSessionList({ showLoadingSummary: true });
  window.addEventListener('pw:screen-changed', event => {
    const detail = event && event.detail ? event.detail : null;
    if (!detail || detail.screenId !== 'walker-main') return;
    refreshSessionList({ showLoadingSummary: true });
  });
  refreshWalkerStatsMicroState();
}

/**
 * Initialise the one-step corpus dropdown selectors for Patch A and Patch B.
 *
 * Wires up:
 *   1. Initial fetch - populates both dropdowns on page load
 *   2. Change listeners - selecting a run triggers loadCorpus() immediately
 *   3. Refresh buttons - re-fetch the run list without reloading the page
 *
 * @returns {void}
 */
function initCorpusDropdowns() {
  /* 1. Populate dropdowns on page load */
  populateCorpusDropdowns();

  /* 2. Wire up change events for both patches */
  ['a', 'b'].forEach(patch => {
    const select = document.getElementById(`corpus-select-${patch}`);
    if (!select) return;

    /*
     * When the user picks a run from the dropdown, immediately load the
     * corpus into the patch. The empty-string sentinel ("-- Select corpus --")
     * is ignored so re-selecting the placeholder is a no-op.
     */
    select.addEventListener('change', () => {
      const runId = select.value;
      if (!runId) return; /* placeholder selected - nothing to do */

      /* Look up the full run object for metadata (syllable count, etc.) */
      const run = (_corpusRunsByPatch[patch] || []).find(r => getRunId(r) === runId);
      if (!run) return;

      loadCorpus(patch, runId);
    });

    /* 3. Refresh button */
    const refreshBtn = document.getElementById(`corpus-refresh-${patch}`);
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => populateCorpusDropdowns());
    }
  });
}

/**
 * Ensure one run is selectable, then trigger corpus loading for a patch.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {string} runId - Target run id.
 * @returns {void}
 */
function loadSessionRunIntoPatch(patch, runId) {
  const select = document.getElementById(`corpus-select-${patch}`);
  if (!select) return;

  const hasRunNow = Array.from(select.options).some(opt => opt.value === runId);
  if (hasRunNow) {
    select.value = runId;
    loadCorpus(patch, runId);
    return;
  }

  populateCorpusDropdowns().then(() => {
    const refreshedSelect = document.getElementById(`corpus-select-${patch}`);
    if (!refreshedSelect) return;
    const hasRunAfterRefresh = Array.from(refreshedSelect.options).some(opt => opt.value === runId);
    if (hasRunAfterRefresh) {
      refreshedSelect.value = runId;
      loadCorpus(patch, runId);
      return;
    }
    _ctx.setStatus(`Patch ${patch.toUpperCase()}: run ${runId} not found in current run list`);
  });
}

/**
 * Wire session save/load and per-patch reach-cache rebuild controls.
 *
 * @returns {void}
 */
function initSessionControls() {
  const summaryEl = document.getElementById('walker-session-summary');
  const labelInput = document.getElementById('walker-session-label');
  const saveBtn = document.getElementById('walker-save-session');
  const refreshBtn = document.getElementById('walker-refresh-sessions');
  const loadBtn = document.getElementById('walker-load-session');
  const repairBtn = document.getElementById('walker-repair-session');
  const takeoverBtn = document.getElementById('walker-takeover-session-lock');
  const releaseLockBtn = document.getElementById('walker-release-session-lock');
  const selectEl = document.getElementById('walker-session-select');
  const holderId = getWalkerSessionLockHolderId();

  const setSessionIntegrityError = reason => {
    setSessionIntegrity({
      status: 'error',
      reason,
      recoveredFromStale: false,
      patchA: null,
      patchB: null,
      topStatus: 'error',
      topReason: reason,
    });
  };

  const setSessionLockError = (reason, sessionId = null, lockPayload = null) => {
    setSessionLockSignal({
      status: 'error',
      reason,
      sessionId,
      lock: lockPayload,
    });
  };

  const applySessionLoadPayload = (payload, sessionId) => {
    setSessionIntegrity(deriveSessionIntegrity(payload));
    applySessionLockFromLoadPayload(payload, payload.session_id || sessionId);
    if (summaryEl) {
      summaryEl.textContent = formatSessionLoadSummary(payload);
    }
    if (payload.patch_a && payload.patch_a.loaded && typeof payload.patch_a.run_id === 'string') {
      loadSessionRunIntoPatch('a', payload.patch_a.run_id);
    }
    if (payload.patch_b && payload.patch_b.loaded && typeof payload.patch_b.run_id === 'string') {
      loadSessionRunIntoPatch('b', payload.patch_b.run_id);
    }
    _ctx.setStatus(`Session loaded: ${payload.session_id || sessionId}`);
  };

  const loadSessionById = async (sessionId, opts = {}) => {
    const forceLock = Boolean(opts.forceLock);
    const response = await fetch('/api/walker/load-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        lock_holder_id: holderId,
        force_lock: forceLock,
      }),
    });
    const payload = await response.json();
    if (payload.error) {
      const error = new Error(payload.error);
      error.payload = payload;
      throw error;
    }
    applySessionLoadPayload(payload, sessionId);
    await refreshWalkerStatsMicroState();
    return payload;
  };

  if (saveBtn && labelInput && summaryEl) {
    saveBtn.addEventListener('click', async () => {
      const rawLabel = labelInput.value;
      const normalizedLabel = rawLabel.trim();
      const body = {};
      if (normalizedLabel.length > 0) {
        body.label = normalizedLabel;
      }
      body.lock_holder_id = holderId;

      saveBtn.disabled = true;
      _ctx.setStatus('Saving walker session…');
      try {
        const response = await fetch('/api/walker/save-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (payload.error) {
          summaryEl.textContent = `Save failed: ${payload.error}`;
          _ctx.setStatus(`Session save failed: ${payload.error}`);
          return;
        }
        const patchA = payload.patch_a || {};
        const patchB = payload.patch_b || {};
        summaryEl.textContent =
          `${payload.session_id || 'session'} saved · ` +
          `A ${patchA.status || 'unknown'} · B ${patchB.status || 'unknown'}`;
        _ctx.setStatus(`Session saved: ${payload.session_id || 'unknown-session'}`);
        if (normalizedLabel.length > 0) {
          labelInput.value = normalizedLabel;
        }
        await refreshSessionList({ selectedId: payload.session_id || null });
      } catch (err) {
        summaryEl.textContent = `Save failed: ${err.message}`;
        _ctx.setStatus(`Session save failed: ${err.message}`);
      } finally {
        saveBtn.disabled = false;
      }
    });
  }

  if (refreshBtn && summaryEl) {
    refreshBtn.addEventListener('click', async () => {
      await refreshSessionList();
      summaryEl.textContent = 'Session list refreshed.';
      _ctx.setStatus('Session list refreshed');
    });
  }

  if (loadBtn && selectEl && summaryEl) {
      loadBtn.addEventListener('click', async () => {
        const sessionId = selectEl.value;
        if (!sessionId) {
        _ctx.setStatus('Select a saved session first');
        return;
      }

      loadBtn.disabled = true;
      _ctx.setStatus(`Loading session ${sessionId}…`);
      try {
        await loadSessionById(sessionId, { forceLock: false });
      } catch (err) {
        summaryEl.textContent = `Load failed: ${err.message}`;
        setSessionIntegrityError(err.message);
        if (err && err.payload && err.payload.lock_status === 'locked') {
          setSessionLockSignal({
            status: 'locked',
            reason: err.message,
            sessionId,
            lock: (err.payload.lock && typeof err.payload.lock === 'object') ? err.payload.lock : null,
          });
        } else {
          setSessionLockError(err.message, sessionId, null);
        }
        _ctx.setStatus(`Session load failed: ${err.message}`);
      } finally {
        loadBtn.disabled = false;
      }
    });
  }

  if (takeoverBtn && loadBtn && selectEl && summaryEl) {
    takeoverBtn.addEventListener('click', async () => {
      const sessionId = selectEl.value;
      if (!sessionId) {
        _ctx.setStatus('Select a saved session first');
        return;
      }
      takeoverBtn.disabled = true;
      loadBtn.disabled = true;
      _ctx.setStatus(`Taking over lock for session ${sessionId}…`);
      try {
        await loadSessionById(sessionId, { forceLock: true });
        _ctx.setStatus(`Lock taken over and session loaded: ${sessionId}`);
      } catch (err) {
        summaryEl.textContent = `Take over failed: ${err.message}`;
        setSessionIntegrityError(err.message);
        setSessionLockError(err.message, sessionId, null);
        _ctx.setStatus(`Session lock takeover failed: ${err.message}`);
      } finally {
        takeoverBtn.disabled = false;
        loadBtn.disabled = false;
      }
    });
  }

  if (releaseLockBtn && summaryEl) {
    releaseLockBtn.addEventListener('click', async () => {
      const selectedSessionId = selectEl && typeof selectEl.value === 'string' ? selectEl.value : '';
      const sessionId = selectedSessionId || _sessionLockState.sessionId;
      if (!sessionId) {
        _ctx.setStatus('No session lock to release');
        return;
      }
      releaseLockBtn.disabled = true;
      _ctx.setStatus(`Releasing session lock for ${sessionId}…`);
      try {
        await releaseSessionLock(sessionId);
        stopSessionLockHeartbeat();
        setSessionLockSignal({
          status: 'unlocked',
          reason: 'Session lock released.',
          sessionId: null,
          lock: null,
        });
        _ctx.setStatus(`Session lock released: ${sessionId}`);
      } catch (err) {
        summaryEl.textContent = `Release lock failed: ${err.message}`;
        setSessionLockError(err.message, sessionId, null);
        _ctx.setStatus(`Session lock release failed: ${err.message}`);
      } finally {
        releaseLockBtn.disabled = false;
      }
    });
  }

  if (repairBtn && loadBtn && selectEl && summaryEl) {
    repairBtn.addEventListener('click', async () => {
      const sessionId = selectEl.value;
      if (!sessionId) {
        _ctx.setStatus('Select a saved session first');
        return;
      }

      repairBtn.disabled = true;
      loadBtn.disabled = true;
      _ctx.setStatus(`Repairing session ${sessionId}…`);
      try {
        /* Ensure patch context matches selected session before writing repair revision. */
        await loadSessionById(sessionId, { forceLock: false });

        const selectedEntry = _sessionEntriesById[sessionId] || null;
        const body = {
          repair_from_session_id: sessionId,
          lock_holder_id: holderId,
        };
        if (
          selectedEntry
          && typeof selectedEntry.label === 'string'
          && selectedEntry.label.trim().length > 0
        ) {
          body.label = selectedEntry.label.trim();
        }

        const saveResponse = await fetch('/api/walker/save-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const savePayload = await saveResponse.json();
        if (savePayload.error) {
          summaryEl.textContent = `Repair failed: ${savePayload.error}`;
          _ctx.setStatus(`Session repair failed: ${savePayload.error}`);
          return;
        }

        const repairedSessionId = (savePayload && typeof savePayload.session_id === 'string')
          ? savePayload.session_id
          : null;
        await refreshSessionList({ selectedId: repairedSessionId });
        if (repairedSessionId) {
          await loadSessionById(repairedSessionId);
          _ctx.setStatus(`Session repaired: ${sessionId} -> ${repairedSessionId}`);
        } else {
          _ctx.setStatus(`Session repaired: ${sessionId}`);
        }
      } catch (err) {
        summaryEl.textContent = `Repair failed: ${err.message}`;
        setSessionIntegrityError(err.message);
        setSessionLockError(err.message, sessionId, null);
        _ctx.setStatus(`Session repair failed: ${err.message}`);
      } finally {
        repairBtn.disabled = false;
        loadBtn.disabled = false;
      }
    });
  }

  ['a', 'b'].forEach(patch => {
    const rebuildBtn = document.getElementById(`rebuild-reach-cache-${patch}`);
    const rebuildStatusEl = document.getElementById(`rebuild-reach-status-${patch}`);
    const rebuildBadgeEl = document.getElementById(`rebuild-reach-badge-${patch}`);
    if (!rebuildBtn || !rebuildStatusEl || !rebuildBadgeEl) return;

    rebuildBtn.addEventListener('click', async () => {
      const P = patch.toUpperCase();
      const runId = _ctx.state[`corpus${P}`];
      if (typeof runId !== 'string' || runId.length === 0) {
        _ctx.setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      rebuildBtn.disabled = true;
      setRebuildStatus(patch, {
        state: 'rebuilding',
        reason: 'manual rebuild started',
      });
      _ctx.setStatus(`Patch ${P}: rebuilding reach cache…`);

      try {
        const response = await fetch('/api/walker/rebuild-reach-cache', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            patch,
            run_id: runId,
            lock_holder_id: holderId,
          }),
        });
        const payload = await response.json();
        if (payload.error) {
          setRebuildStatus(patch, {
            state: 'error',
            reason: payload.error,
          });
          _ctx.setStatus(`Patch ${P}: reach-cache rebuild failed — ${payload.error}`);
          return;
        }

        setRebuildStatus(patch, {
          state: 'rebuilt',
          reason: payload.verification_reason,
          inputHash: payload.ipc_input_hash,
          outputHash: payload.ipc_output_hash,
        });
        _ctx.setStatus(`Patch ${P}: reach cache rebuilt`);
        await refreshWalkerStatsMicroState();
      } catch (err) {
        setRebuildStatus(patch, {
          state: 'error',
          reason: err.message,
        });
        _ctx.setStatus(`Patch ${P}: reach-cache rebuild failed — ${err.message}`);
      } finally {
        rebuildBtn.disabled = false;
      }
    });
  });
}

/**
 * Fetch discovered runs and populate both Patch A and Patch B dropdowns.
 *
 * If a dropdown already has a selected run that still exists, the selection
 * is restored after refresh.
 *
 * @returns {Promise<void>}
 */
export function populateCorpusDropdowns() {
  /* Fetch runs separately for each patch so per-patch corpus directories
   * (configured via INI) are respected. The ?patch= query parameter
   * tells the server which directory to discover from. */
  return Promise.all(
    ['a', 'b'].map(patch =>
      fetch(`/api/pipeline/runs?patch=${patch}`)
        .then(r => r.json())
        .then(data => {
          const runs = data.runs || [];
          _corpusRunsByPatch[patch] = runs;

          const select = document.getElementById(`corpus-select-${patch}`);
          if (!select) return;

          /* Remember the current selection so we can restore it after rebuild */
          const previousValue = select.value;

          /* Clear all options except the placeholder */
          while (select.options.length > 1) {
            select.remove(1);
          }

          /* Build an <option> for each discovered run. */
          runs.forEach(run => {
            const runId = getRunId(run);
            if (!runId) return;
            const syllableCountRaw = Number(run.syllable_count);
            const selectionCountRaw = Number(run.selection_count);
            const syllableCount = Number.isFinite(syllableCountRaw) ? syllableCountRaw : 0;
            const selectionCount = Number.isFinite(selectionCountRaw) ? selectionCountRaw : 0;
            const syllables = syllableCount.toLocaleString();
            const selections = selectionCount > 0
              ? ` · ${selectionCount} selections`
              : '';
            const extractor = (typeof run.extractor_type === 'string' && run.extractor_type.length > 0)
              ? run.extractor_type
              : 'unknown';
            const label = `${runId} (${syllables} syl${selections} · ${extractor})`;

            const option = document.createElement('option');
            option.value = runId;
            option.textContent = label;
            select.appendChild(option);
          });

          /* Restore previous selection if the run still exists in the new list */
          if (previousValue && Array.from(select.options).some(o => o.value === previousValue)) {
            select.value = previousValue;
          }
        })
        .catch(err => {
          console.warn(`Failed to fetch runs for patch ${patch}:`, err.message);
        })
    )
  );
}

/**
 * Load one selected corpus into a patch and begin readiness polling.
 *
 * @param {'a'|'b'|string} patch - Patch key receiving the corpus.
 * @param {string} runId - Selected run identifier.
 * @returns {void}
 */
function loadCorpus(patch, runId) {
  const P = patch.toUpperCase();
  const label = `${runId} · loading…`;
  setRebuildStatus(patch, {
    state: 'idle',
    reason: 'new corpus selected',
  });

  setCorpusStatus(patch, label, 'neutral');
  setCorpusHashes(patch, null, null, null, null);
  setCorpusHashVerification(patch, null, null, null, null);
  document.getElementById(`status-corpus-${patch}`).textContent = runId;
  _ctx.state[`corpus${P}`] = runId;
  _ctx.setStatus(`Patch ${P}: loading corpus ${runId}…`);
  const holderId = getWalkerSessionLockHolderId();

  fetch('/api/walker/load-corpus', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      patch: patch,
      run_id: runId,
      lock_holder_id: holderId,
    }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        setCorpusStatus(patch, `Error: ${data.error}`, 'error');
        _ctx.setStatus(`Patch ${P}: ${data.error}`);
        return;
      }
      const syllCount = (data.syllable_count || 0).toLocaleString();
      setCorpusStatus(
        patch,
        `${runId} · ${syllCount} syllables · walker loading…`
      );
      _ctx.setStatus(`Patch ${P}: ${syllCount} syllables loaded, walker initialising…`);

      /* Start polling for walker readiness */
      pollWalkerReady(patch);
    })
    .catch(err => {
      setCorpusStatus(patch, `Error: ${err.message}`, 'error');
      _ctx.setStatus(`Patch ${P}: load failed — ${err.message}`);
    });
}

/**
 * Poll walker stats until one patch reports ready status.
 *
 * @param {'a'|'b'|string} patch - Patch to monitor.
 * @returns {void}
 * Side effects:
 * - Starts/stops per-patch polling timer.
 * - Updates corpus status text and status bar.
 * - Triggers reach value updates when available.
 */
function pollWalkerReady(patch) {
  const P = patch.toUpperCase();
  const patchKey = `patch_${patch}`;

  /* Clear any existing poller */
  if (_walkerReadyPollers[patch]) {
    clearInterval(_walkerReadyPollers[patch]);
  }

  _walkerReadyPollers[patch] = setInterval(() => {
    fetch('/api/walker/stats')
      .then(r => r.json())
      .then(data => {
        const info = data[patchKey];
        if (!info) return;
        setPatchComparison(data.patch_comparison);
        setCorpusHashes(
          patch,
          info.manifest_ipc_input_hash,
          info.manifest_ipc_output_hash,
          info.reach_cache_ipc_input_hash,
          info.reach_cache_ipc_output_hash
        );
        setCorpusHashVerification(
          patch,
          info.manifest_ipc_verification_status,
          info.manifest_ipc_verification_reason,
          info.reach_cache_ipc_verification_status,
          info.reach_cache_ipc_verification_reason
        );
        setRebuildStatus(
          patch,
          {
            state: rebuildStateFromVerification(info.reach_cache_ipc_verification_status),
            reason: info.reach_cache_ipc_verification_reason,
            inputHash: info.reach_cache_ipc_input_hash,
            outputHash: info.reach_cache_ipc_output_hash,
          }
        );

        if (info.loader_status === 'error' || info.loading_error) {
          clearInterval(_walkerReadyPollers[patch]);
          _walkerReadyPollers[patch] = null;
          const runId = _ctx.state[`corpus${P}`] || info.corpus || 'unknown-run';
          const message = info.loading_error || 'Walker initialisation failed';
          setCorpusStatus(patch, `${runId} · ${message}`, 'error');
          _ctx.setStatus(`Patch ${P}: ${message}`);
          return;
        }

        if (info.walker_ready || info.loader_status === 'ready') {
          clearInterval(_walkerReadyPollers[patch]);
          _walkerReadyPollers[patch] = null;
          const runId = _ctx.state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          setCorpusStatus(patch, `${runId} · ${count} syllables · walker ready ✓`, 'loaded');
          _ctx.setStatus(`Patch ${P}: walker ready`);

          /* Update profile reach values once available in the stats response. */
          if (info.reaches) {
            _ctx.updateReachValues(patch, info.reaches);
          }
        } else if (info.loading_stage || info.loader_status === 'loading') {
          /* Show loading stage progress while walker is building. */
          const runId = _ctx.state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          const stageLabel = info.loading_stage || 'Loading corpus data';
          setCorpusStatus(patch, `${runId} · ${count} syllables · ${stageLabel}…`, 'neutral');
          _ctx.setStatus(`Patch ${P}: ${stageLabel}…`);
        }
      })
      .catch(() => { /* ignore polling errors */ });
  }, 1000);
}
