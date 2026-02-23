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
 * Update one patch reach-cache rebuild status row.
 *
 * @param {'a'|'b'|string} patch - Patch key.
 * @param {unknown} inputHash - Reach-cache IPC input hash.
 * @param {unknown} outputHash - Reach-cache IPC output hash.
 * @returns {void}
 */
function setRebuildStatus(patch, inputHash, outputHash) {
  const statusEl = document.getElementById(`rebuild-reach-status-${patch}`);
  if (!statusEl) return;

  if (typeof inputHash === 'string' || typeof outputHash === 'string') {
    const inText = typeof inputHash === 'string' ? inputHash : '—';
    const outText = typeof outputHash === 'string' ? outputHash : '—';
    statusEl.textContent = formatHashPair(inputHash, outputHash);
    statusEl.title = `in: ${inText}\nout: ${outText}`;
    return;
  }

  statusEl.textContent = 'idle';
  statusEl.removeAttribute('title');
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

  const labelPrefix = label ? `${label} · ` : '';
  return `${labelPrefix}${created} · ${sessionId} · A ${patchA} · B ${patchB} · ${verification}`;
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
  return `${sessionId} · A ${formatPatchOutcome(patchA)} · B ${formatPatchOutcome(patchB)}`;
}

/**
 * Refresh session dropdown options from API.
 *
 * @param {{selectedId?: string | null}} [opts] - Optional selection override.
 * @returns {Promise<void>}
 */
async function refreshSessionList(opts = {}) {
  const select = document.getElementById('walker-session-select');
  if (!select) return;

  const selectedId = (typeof opts.selectedId === 'string') ? opts.selectedId : select.value;

  let payload;
  try {
    const response = await fetch('/api/walker/sessions');
    payload = await response.json();
  } catch (err) {
    _ctx.setStatus(`Failed to load sessions: ${err.message}`);
    return;
  }

  if (payload && payload.error) {
    _ctx.setStatus(`Failed to load sessions: ${payload.error}`);
    return;
  }

  const sessions = Array.isArray(payload && payload.sessions) ? payload.sessions : [];
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
      info.reach_cache_ipc_input_hash,
      info.reach_cache_ipc_output_hash
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
  refreshSessionList();
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
  const selectEl = document.getElementById('walker-session-select');

  if (saveBtn && labelInput && summaryEl) {
    saveBtn.addEventListener('click', async () => {
      const rawLabel = labelInput.value;
      const normalizedLabel = rawLabel.trim();
      const body = {};
      if (normalizedLabel.length > 0) {
        body.label = normalizedLabel;
      }

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
        const response = await fetch('/api/walker/load-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
        const payload = await response.json();
        if (payload.error) {
          summaryEl.textContent = `Load failed: ${payload.error}`;
          _ctx.setStatus(`Session load failed: ${payload.error}`);
          return;
        }

        summaryEl.textContent = formatSessionLoadSummary(payload);
        if (payload.patch_a && payload.patch_a.loaded && typeof payload.patch_a.run_id === 'string') {
          loadSessionRunIntoPatch('a', payload.patch_a.run_id);
        }
        if (payload.patch_b && payload.patch_b.loaded && typeof payload.patch_b.run_id === 'string') {
          loadSessionRunIntoPatch('b', payload.patch_b.run_id);
        }
        _ctx.setStatus(`Session loaded: ${payload.session_id || sessionId}`);
        await refreshWalkerStatsMicroState();
      } catch (err) {
        summaryEl.textContent = `Load failed: ${err.message}`;
        _ctx.setStatus(`Session load failed: ${err.message}`);
      } finally {
        loadBtn.disabled = false;
      }
    });
  }

  ['a', 'b'].forEach(patch => {
    const rebuildBtn = document.getElementById(`rebuild-reach-cache-${patch}`);
    const rebuildStatusEl = document.getElementById(`rebuild-reach-status-${patch}`);
    if (!rebuildBtn || !rebuildStatusEl) return;

    rebuildBtn.addEventListener('click', async () => {
      const P = patch.toUpperCase();
      const runId = _ctx.state[`corpus${P}`];
      if (typeof runId !== 'string' || runId.length === 0) {
        _ctx.setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      rebuildBtn.disabled = true;
      rebuildStatusEl.textContent = 'rebuilding…';
      _ctx.setStatus(`Patch ${P}: rebuilding reach cache…`);

      try {
        const response = await fetch('/api/walker/rebuild-reach-cache', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ patch, run_id: runId }),
        });
        const payload = await response.json();
        if (payload.error) {
          rebuildStatusEl.textContent = 'error';
          rebuildStatusEl.title = payload.error;
          _ctx.setStatus(`Patch ${P}: reach-cache rebuild failed — ${payload.error}`);
          return;
        }

        setRebuildStatus(patch, payload.ipc_input_hash, payload.ipc_output_hash);
        _ctx.setStatus(`Patch ${P}: reach cache rebuilt`);
        await refreshWalkerStatsMicroState();
      } catch (err) {
        rebuildStatusEl.textContent = 'error';
        rebuildStatusEl.title = err.message;
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
  setRebuildStatus(patch, null, null);

  setCorpusStatus(patch, label, 'neutral');
  setCorpusHashes(patch, null, null, null, null);
  setCorpusHashVerification(patch, null, null, null, null);
  document.getElementById(`status-corpus-${patch}`).textContent = runId;
  _ctx.state[`corpus${P}`] = runId;
  _ctx.setStatus(`Patch ${P}: loading corpus ${runId}…`);

  fetch('/api/walker/load-corpus', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patch: patch, run_id: runId }),
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
