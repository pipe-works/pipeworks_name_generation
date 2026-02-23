/*
   walker/corpus-api.js
   Dedicated API transport helpers for walker corpus/session operations.
*/

'use strict';

/** @typedef {import('./corpus-contracts.js').WalkerApiErrorPayload} WalkerApiErrorPayload */
/** @typedef {import('./corpus-contracts.js').SessionLockStatusResponse} SessionLockStatusResponse */
/** @typedef {import('./corpus-contracts.js').WalkerLoadCorpusResponse} WalkerLoadCorpusResponse */
/** @typedef {import('./corpus-contracts.js').WalkerPipelineRunsPayload} WalkerPipelineRunsPayload */
/** @typedef {import('./corpus-contracts.js').WalkerStatsPayload} WalkerStatsPayload */
/** @typedef {import('./corpus-contracts.js').WalkerSessionsPayload} WalkerSessionsPayload */
/** @typedef {import('./corpus-contracts.js').WalkerSessionSavePayload} WalkerSessionSavePayload */
/** @typedef {import('./corpus-contracts.js').WalkerSessionLoadPayload} WalkerSessionLoadPayload */
/** @typedef {import('./corpus-contracts.js').WalkerRebuildReachCacheResponse} WalkerRebuildReachCacheResponse */

const JSON_HEADERS = { 'Content-Type': 'application/json' };
const PATHS = {
  loadCorpus: '/api/walker/load-corpus',
  walkerStats: '/api/walker/stats',
  walkerSessions: '/api/walker/sessions',
  saveSession: '/api/walker/save-session',
  loadSession: '/api/walker/load-session',
  sessionLockHeartbeat: '/api/walker/session-lock/heartbeat',
  sessionLockRelease: '/api/walker/session-lock/release',
  rebuildReachCache: '/api/walker/rebuild-reach-cache',
};

/**
 * Parse one JSON API response.
 *
 * Keeps transport behavior intentionally thin: caller-level error handling
 * remains authoritative so existing UI messages and flows stay unchanged.
 *
 * @param {Response} response - Browser fetch response object.
 * @returns {Promise<Record<string, any>>}
 */
function parseJson(response) {
  return response.json();
}

/**
 * Run one GET request and decode JSON.
 *
 * @param {string} path - API path.
 * @returns {Promise<Record<string, any>>}
 */
function getJson(path) {
  return fetch(path).then(parseJson);
}

/**
 * Run one JSON POST request and decode JSON.
 *
 * @param {string} path - API path.
 * @param {Record<string, any>} body - Request payload.
 * @returns {Promise<Record<string, any>>}
 */
function postJson(path, body) {
  return fetch(path, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  }).then(parseJson);
}

/**
 * List discovered pipeline runs for one patch corpus directory.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @returns {Promise<WalkerPipelineRunsPayload|WalkerApiErrorPayload>}
 */
export function listPipelineRuns(patch) {
  return getJson(`/api/pipeline/runs?patch=${patch}`);
}

/**
 * Load one selected corpus into walker patch state.
 *
 * @param {{patch: 'a'|'b'|string, runId: string, lockHolderId: string}} args - Load args.
 * @returns {Promise<WalkerLoadCorpusResponse|WalkerApiErrorPayload>}
 */
export function loadWalkerCorpus(args) {
  return postJson(PATHS.loadCorpus, {
    patch: args.patch,
    run_id: args.runId,
    lock_holder_id: args.lockHolderId,
  });
}

/**
 * Read current walker stats snapshot from API authority endpoint.
 *
 * @returns {Promise<WalkerStatsPayload|WalkerApiErrorPayload>}
 */
export function getWalkerStats() {
  return getJson(PATHS.walkerStats);
}

/**
 * List saved walker sessions.
 *
 * @returns {Promise<WalkerSessionsPayload|WalkerApiErrorPayload>}
 */
export function listWalkerSessions() {
  return getJson(PATHS.walkerSessions);
}

/**
 * Save current walker session snapshot.
 *
 * @param {Record<string, any>} body - Save payload.
 * @returns {Promise<WalkerSessionSavePayload|WalkerApiErrorPayload>}
 */
export function saveWalkerSession(body) {
  return postJson(PATHS.saveSession, body);
}

/**
 * Load one saved walker session.
 *
 * @param {{sessionId: string, lockHolderId: string, forceLock: boolean}} args - Load args.
 * @returns {Promise<WalkerSessionLoadPayload|WalkerApiErrorPayload>}
 */
export function loadWalkerSession(args) {
  return postJson(PATHS.loadSession, {
    session_id: args.sessionId,
    lock_holder_id: args.lockHolderId,
    force_lock: args.forceLock,
  });
}

/**
 * Heartbeat one session lock held by this tab.
 *
 * @param {{sessionId: string, lockHolderId: string}} args - Lock args.
 * @returns {Promise<SessionLockStatusResponse|WalkerApiErrorPayload>}
 */
export function heartbeatWalkerSessionLock(args) {
  return postJson(PATHS.sessionLockHeartbeat, {
    session_id: args.sessionId,
    lock_holder_id: args.lockHolderId,
  });
}

/**
 * Release one held session lock.
 *
 * @param {{sessionId: string, lockHolderId: string}} args - Lock args.
 * @returns {Promise<SessionLockStatusResponse|WalkerApiErrorPayload>}
 */
export function releaseWalkerSessionLock(args) {
  return postJson(PATHS.sessionLockRelease, {
    session_id: args.sessionId,
    lock_holder_id: args.lockHolderId,
  });
}

/**
 * Best-effort lock release using sendBeacon during page unload.
 *
 * @param {{sessionId: string, lockHolderId: string}} args - Lock args.
 * @returns {boolean}
 */
export function sendWalkerSessionLockReleaseBeacon(args) {
  const body = JSON.stringify({
    session_id: args.sessionId,
    lock_holder_id: args.lockHolderId,
  });
  return navigator.sendBeacon(PATHS.sessionLockRelease, body);
}

/**
 * Rebuild reach-cache tables and rewrite cache IPC sidecar hashes.
 *
 * @param {{patch: 'a'|'b'|string, runId: string, lockHolderId: string}} args - Rebuild args.
 * @returns {Promise<WalkerRebuildReachCacheResponse|WalkerApiErrorPayload>}
 */
export function rebuildWalkerReachCache(args) {
  return postJson(PATHS.rebuildReachCache, {
    patch: args.patch,
    run_id: args.runId,
    lock_holder_id: args.lockHolderId,
  });
}
