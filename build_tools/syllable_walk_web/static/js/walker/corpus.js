/*
   walker/corpus.js
   Section 10: walker corpus dropdown loading and walker-readiness polling.
*/

'use strict';

import {
  heartbeatWalkerSessionLock,
  releaseWalkerSessionLock,
  listWalkerSessions,
  getWalkerStats,
  loadWalkerSession,
  saveWalkerSession,
  rebuildWalkerReachCache,
  listPipelineRuns,
  loadWalkerCorpus,
  sendWalkerSessionLockReleaseBeacon,
} from './corpus-api.js';
import {
  rebuildStateFromVerification,
  setCorpusHashes,
  setCorpusHashVerification,
  setCorpusStatus,
  setPatchComparison,
  setRebuildStatus,
} from './corpus-render.js';
import { initReachCacheActions } from './corpus-actions-cache.js';
import { initSessionActions } from './corpus-actions-session.js';
import {
  deriveSessionIntegrity,
  formatSessionLoadSummary,
  initSessionIntegrityModal,
  setSessionIntegrity,
  setSessionLockSignal,
} from './corpus-tooltips.js';
import {
  getCorpusRunsByPatch,
  setCorpusRunsByPatch,
  getWalkerReadyPoller,
  setWalkerReadyPoller,
  replaceSessionEntries,
  getSessionEntry,
  hasSessionEntry,
  resetSessionIntegrityState,
  getSessionLockState,
  resetSessionLockState,
  getSessionLockHeartbeatTimer,
  setSessionLockHeartbeatTimer,
} from './corpus-state.js';

/** @typedef {import('./corpus-contracts.js').WalkerApiErrorPayload} WalkerApiErrorPayload */
/** @typedef {import('./corpus-contracts.js').SessionLockState} SessionLockState */
/** @typedef {import('./corpus-contracts.js').SessionLockStatusResponse} SessionLockStatusResponse */
/** @typedef {import('./corpus-contracts.js').WalkerSessionLoadPayload} WalkerSessionLoadPayload */
/** @typedef {import('./corpus-contracts.js').WalkerSessionListEntry} WalkerSessionListEntry */
/** @typedef {import('./corpus-contracts.js').WalkerSessionsPayload} WalkerSessionsPayload */
/** @typedef {import('./corpus-contracts.js').WalkerPatchStats} WalkerPatchStats */
/** @typedef {import('./corpus-contracts.js').WalkerStatsPayload} WalkerStatsPayload */
/** @typedef {import('./corpus-contracts.js').WalkerCorpusContext} WalkerCorpusContext */

/** @type {WalkerCorpusContext | null} */
let _ctx = null;

const SESSION_LOCK_HOLDER_STORAGE_KEY = 'pipeworks.walker.lock_holder_id';
const SESSION_LOCK_HEARTBEAT_MS = 10_000;

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
 * Build a compact label for session dropdown options.
 *
 * @param {WalkerSessionListEntry} entry - One session list entry from API.
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
 * Stop lock heartbeat polling timer for this tab.
 *
 * @returns {void}
 */
function stopSessionLockHeartbeat() {
  const timer = getSessionLockHeartbeatTimer();
  if (timer) {
    clearInterval(timer);
    setSessionLockHeartbeatTimer(null);
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
  const payload = await heartbeatWalkerSessionLock({
    sessionId,
    lockHolderId: holderId,
  });
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
  const timer = setInterval(() => {
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
  setSessionLockHeartbeatTimer(timer);
}

/**
 * Release one session lock owned by this tab.
 *
 * @param {string} sessionId - Session id to release.
 * @returns {Promise<SessionLockStatusResponse>}
 */
async function releaseSessionLock(sessionId) {
  const holderId = getWalkerSessionLockHolderId();
  const payload = await releaseWalkerSessionLock({
    sessionId,
    lockHolderId: holderId,
  });
  if (payload.error) {
    throw new Error(payload.error);
  }
  return payload;
}

/**
 * Update lock signal + heartbeat from one load-session payload.
 *
 * @param {WalkerSessionLoadPayload} payload - Load-session response payload.
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

  /** @type {WalkerSessionsPayload|WalkerApiErrorPayload|null} */
  let payload = null;
  try {
    payload = await listWalkerSessions();
  } catch (err) {
    _ctx.setStatus(`Failed to load sessions: ${err.message}`);
  } finally {
    if (payload && payload.error) {
      _ctx.setStatus(`Failed to load sessions: ${payload.error}`);
    } else if (payload) {
      const sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
      replaceSessionEntries(sessions);

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

      if (selectedId && hasSessionEntry(selectedId)) {
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
 * Apply one patch stats block to corpus hash/verification/rebuild UI state.
 *
 * Centralizing this mapping keeps ``refreshWalkerStatsMicroState`` and
 * ``pollWalkerReady`` aligned to the same API-to-UI contract.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {WalkerPatchStats} info - Patch stats block from API.
 * @returns {void}
 */
function syncPatchStatsMicroState(patch, info) {
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
}

/**
 * Request fresh walker stats and sync hash/compare micro-state.
 *
 * @returns {Promise<void>}
 */
async function refreshWalkerStatsMicroState() {
  /** @type {WalkerStatsPayload|WalkerApiErrorPayload|undefined} */
  let stats;
  try {
    stats = await getWalkerStats();
  } catch {
    return;
  }
  ['a', 'b'].forEach(patch => {
    /** @type {WalkerPatchStats|null} */
    const info = stats ? stats[`patch_${patch}`] : null;
    if (!info) return;
    syncPatchStatsMicroState(patch, info);
    if (info.reaches) {
      _ctx.updateReachValues(patch, info.reaches);
    }
  });
  setPatchComparison(stats ? stats.patch_comparison : null);
}

/**
 * Initialise corpus dropdown selectors and load initial run options.
 *
 * @param {WalkerCorpusContext} ctx - Shared state and reach-update callback.
 * @returns {void}
 */
export function initCorpus(ctx) {
  _ctx = ctx;
  initCorpusDropdowns();
  initSessionControls();
  initSessionIntegrityModal();
  resetSessionIntegrityState();
  resetSessionLockState();
  setSessionIntegrity(deriveSessionIntegrity(null));
  setSessionLockSignal({
    status: 'unlocked',
    reason: 'No session lock held.',
    sessionId: null,
    lock: null,
  });
  window.addEventListener('beforeunload', () => {
    const lockState = getSessionLockState();
    if (
      !lockState
      || !lockState.sessionId
      || !['acquired', 'held', 'taken_over'].includes(lockState.status)
    ) {
      return;
    }
    const holderId = getWalkerSessionLockHolderId();
    try {
      sendWalkerSessionLockReleaseBeacon({
        sessionId: lockState.sessionId,
        lockHolderId: holderId,
      });
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
      const run = getCorpusRunsByPatch(patch).find(r => getRunId(r) === runId);
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
  initSessionActions({
    ctx: _ctx,
    getWalkerSessionLockHolderId,
    deriveSessionIntegrity,
    setSessionIntegrity,
    applySessionLockFromLoadPayload,
    formatSessionLoadSummary,
    loadSessionRunIntoPatch,
    loadWalkerSession,
    saveWalkerSession,
    refreshSessionList,
    refreshWalkerStatsMicroState,
    setSessionLockSignal,
    getSessionLockState,
    releaseSessionLock,
    stopSessionLockHeartbeat,
    getSessionEntry,
  });
  initReachCacheActions({
    ctx: _ctx,
    getWalkerSessionLockHolderId,
    setRebuildStatus,
    rebuildWalkerReachCache,
    refreshWalkerStatsMicroState,
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
      listPipelineRuns(patch)
        .then(data => {
          const runs = data.runs || [];
          setCorpusRunsByPatch(patch, runs);

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

  loadWalkerCorpus({
    patch: patch,
    runId,
    lockHolderId: holderId,
  })
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
  const existingPoller = getWalkerReadyPoller(patch);
  if (existingPoller) {
    clearInterval(existingPoller);
  }

  const poller = setInterval(() => {
    getWalkerStats()
      .then(data => {
        const info = data[patchKey];
        if (!info) return;
        setPatchComparison(data.patch_comparison);
        syncPatchStatsMicroState(patch, info);

        if (info.loader_status === 'error' || info.loading_error) {
          const activePoller = getWalkerReadyPoller(patch);
          if (activePoller) clearInterval(activePoller);
          setWalkerReadyPoller(patch, null);
          const runId = _ctx.state[`corpus${P}`] || info.corpus || 'unknown-run';
          const message = info.loading_error || 'Walker initialisation failed';
          setCorpusStatus(patch, `${runId} · ${message}`, 'error');
          _ctx.setStatus(`Patch ${P}: ${message}`);
          return;
        }

        if (info.walker_ready || info.loader_status === 'ready') {
          const activePoller = getWalkerReadyPoller(patch);
          if (activePoller) clearInterval(activePoller);
          setWalkerReadyPoller(patch, null);
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
  setWalkerReadyPoller(patch, poller);
}
