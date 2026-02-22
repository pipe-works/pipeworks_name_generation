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
 * Fetch discovered runs and populate both Patch A and Patch B dropdowns.
 *
 * If a dropdown already has a selected run that still exists, the selection
 * is restored after refresh.
 *
 * @returns {void}
 */
export function populateCorpusDropdowns() {
  /* Fetch runs separately for each patch so per-patch corpus directories
   * (configured via INI) are respected. The ?patch= query parameter
   * tells the server which directory to discover from. */
  ['a', 'b'].forEach(patch => {
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
          const syllables = run.syllable_count.toLocaleString();
          const selections = run.selection_count
            ? ` · ${run.selection_count} selections`
            : '';
          const label = `${runId} (${syllables} syl${selections} · ${run.extractor_type})`;

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
      });
  });
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
