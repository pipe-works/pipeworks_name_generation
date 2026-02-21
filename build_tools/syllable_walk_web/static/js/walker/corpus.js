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
      const run = (_corpusRunsByPatch[patch] || []).find(r => r.path.split('/').pop() === runId);
      if (!run) return;

      loadCorpus(patch, runId, run);
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
          const runId = run.path.split('/').pop();
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
 * @param {{path: string}} run - Run metadata entry used by current view.
 * @returns {void}
 */
function loadCorpus(patch, runId, run) {
  const P = patch.toUpperCase();
  const label = `${runId} · loading…`;

  document.getElementById(`corpus-status-${patch}`).textContent = label;
  document.getElementById(`corpus-status-${patch}`).classList.add('is-loaded');
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
        document.getElementById(`corpus-status-${patch}`).textContent = `Error: ${data.error}`;
        _ctx.setStatus(`Patch ${P}: ${data.error}`);
        return;
      }
      const syllCount = (data.syllable_count || 0).toLocaleString();
      document.getElementById(`corpus-status-${patch}`).textContent =
        `${runId} · ${syllCount} syllables · walker loading…`;
      _ctx.setStatus(`Patch ${P}: ${syllCount} syllables loaded, walker initialising…`);

      /* Start polling for walker readiness */
      pollWalkerReady(patch);
    })
    .catch(err => {
      document.getElementById(`corpus-status-${patch}`).textContent = `Error: ${err.message}`;
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

        if (info.walker_ready) {
          clearInterval(_walkerReadyPollers[patch]);
          _walkerReadyPollers[patch] = null;
          const runId = _ctx.state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          document.getElementById(`corpus-status-${patch}`).textContent =
            `${runId} · ${count} syllables · walker ready ✓`;
          _ctx.setStatus(`Patch ${P}: walker ready`);

          /* Update profile reach values once available in the stats response. */
          if (info.reaches) {
            _ctx.updateReachValues(patch, info.reaches);
          }
        } else if (info.loading_stage) {
          /* Show loading stage progress while walker is building. */
          const runId = _ctx.state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          document.getElementById(`corpus-status-${patch}`).textContent =
            `${runId} · ${count} syllables · ${info.loading_stage}…`;
          _ctx.setStatus(`Patch ${P}: ${info.loading_stage}…`);
        }
      })
      .catch(() => { /* ignore polling errors */ });
  }, 1000);
}
