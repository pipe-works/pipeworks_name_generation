/*
   walker/corpus-state.js
   In-memory state store for walker/corpus module.
*/

'use strict';

/** @typedef {import('./corpus-contracts.js').WalkerPipelineRun} WalkerPipelineRun */
/** @typedef {import('./corpus-contracts.js').WalkerSessionListEntry} WalkerSessionListEntry */
/** @typedef {import('./corpus-contracts.js').SessionIntegrityState} SessionIntegrityState */
/** @typedef {import('./corpus-contracts.js').SessionLockState} SessionLockState */

/** @type {SessionIntegrityState} */
const DEFAULT_SESSION_INTEGRITY_STATE = Object.freeze({
  status: 'unknown',
  reason: 'No session load has been evaluated yet.',
  recoveredFromStale: false,
  patchA: null,
  patchB: null,
  topStatus: 'unknown',
  topReason: 'not evaluated',
});

/** @type {SessionLockState} */
const DEFAULT_SESSION_LOCK_STATE = Object.freeze({
  status: 'unlocked',
  reason: 'No session lock held.',
  sessionId: null,
  lock: null,
});

const _state = {
  corpusRunsByPatch: { a: [], b: [] },
  walkerReadyPollers: {},
  sessionEntriesById: {},
  sessionIntegrityState: { ...DEFAULT_SESSION_INTEGRITY_STATE },
  sessionLockState: { ...DEFAULT_SESSION_LOCK_STATE },
  sessionLockHeartbeatTimer: null,
};

/**
 * Read discovered corpus runs for one patch.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @returns {WalkerPipelineRun[]}
 */
export function getCorpusRunsByPatch(patch) {
  const runs = _state.corpusRunsByPatch[patch];
  return Array.isArray(runs) ? runs : [];
}

/**
 * Replace discovered corpus runs for one patch.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {WalkerPipelineRun[]} runs - Run list payload.
 * @returns {void}
 */
export function setCorpusRunsByPatch(patch, runs) {
  _state.corpusRunsByPatch[patch] = Array.isArray(runs) ? runs : [];
}

/**
 * Read one active walker-ready poller id.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @returns {number | null}
 */
export function getWalkerReadyPoller(patch) {
  const poller = _state.walkerReadyPollers[patch];
  return typeof poller === 'number' ? poller : null;
}

/**
 * Write one active walker-ready poller id.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {number | null} poller - Interval id.
 * @returns {void}
 */
export function setWalkerReadyPoller(patch, poller) {
  _state.walkerReadyPollers[patch] = poller;
}

/**
 * Replace session entry map from API sessions list.
 *
 * @param {WalkerSessionListEntry[]} sessions - Session list payload.
 * @returns {void}
 */
export function replaceSessionEntries(sessions) {
  const next = {};
  (Array.isArray(sessions) ? sessions : []).forEach(entry => {
    if (entry && typeof entry.session_id === 'string' && entry.session_id.length > 0) {
      next[entry.session_id] = entry;
    }
  });
  _state.sessionEntriesById = next;
}

/**
 * Resolve one saved session entry by id.
 *
 * @param {string} sessionId - Session id key.
 * @returns {WalkerSessionListEntry | null}
 */
export function getSessionEntry(sessionId) {
  if (!sessionId || typeof sessionId !== 'string') return null;
  const entry = _state.sessionEntriesById[sessionId];
  return entry && typeof entry === 'object' ? entry : null;
}

/**
 * Test whether one saved session id exists in current map.
 *
 * @param {string} sessionId - Session id key.
 * @returns {boolean}
 */
export function hasSessionEntry(sessionId) {
  if (!sessionId || typeof sessionId !== 'string') return false;
  return Object.prototype.hasOwnProperty.call(_state.sessionEntriesById, sessionId);
}

/**
 * Read current session-integrity state model.
 *
 * @returns {SessionIntegrityState}
 */
export function getSessionIntegrityState() {
  return _state.sessionIntegrityState;
}

/**
 * Write current session-integrity state model.
 *
 * @param {SessionIntegrityState} integrity - Integrity model.
 * @returns {void}
 */
export function setSessionIntegrityState(integrity) {
  _state.sessionIntegrityState = integrity;
}

/**
 * Reset session-integrity state to default model.
 *
 * @returns {void}
 */
export function resetSessionIntegrityState() {
  _state.sessionIntegrityState = { ...DEFAULT_SESSION_INTEGRITY_STATE };
}

/**
 * Read current session-lock state model.
 *
 * @returns {SessionLockState}
 */
export function getSessionLockState() {
  return _state.sessionLockState;
}

/**
 * Write current session-lock state model.
 *
 * @param {SessionLockState} lockState - Lock model.
 * @returns {void}
 */
export function setSessionLockState(lockState) {
  _state.sessionLockState = lockState;
}

/**
 * Reset session-lock state to default model.
 *
 * @returns {void}
 */
export function resetSessionLockState() {
  _state.sessionLockState = { ...DEFAULT_SESSION_LOCK_STATE };
}

/**
 * Read active lock-heartbeat timer id.
 *
 * @returns {number | null}
 */
export function getSessionLockHeartbeatTimer() {
  return typeof _state.sessionLockHeartbeatTimer === 'number'
    ? _state.sessionLockHeartbeatTimer
    : null;
}

/**
 * Write active lock-heartbeat timer id.
 *
 * @param {number | null} timerId - Interval id.
 * @returns {void}
 */
export function setSessionLockHeartbeatTimer(timerId) {
  _state.sessionLockHeartbeatTimer = timerId;
}
