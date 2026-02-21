/*
   pipeline/pipeline.js
   Sections 11, 19, 20, 21:
   directory browser, run readiness, monitor polling, and run history.
*/

'use strict';

/** @type {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void,
 *   populateCorpusDropdowns: () => void
 * } | null} */
let _ctx = null;

/* Cached run data for history screen (populated from API). */
let _historyRuns = [];

let _dirModalTarget = 'source';     /* 'source' or 'output' */
let _dirModalMode = 'directory';    /* 'directory' or 'file' */
let _dirModalCurrentPath = '.';
let _dirModalSelectedFile = null;   /* full path of selected file (file mode only) */

let _pipelinePoller = null;
let _lastLogOffset = 0;

/**
 * Initialise all pipeline tool behaviors.
 *
 * @param {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void,
 *   populateCorpusDropdowns: () => void
 * }} ctx - Shared state, status helper, and corpus-refresh callback.
 * @returns {void}
 */
export function initPipeline(ctx) {
  _ctx = ctx;
  initDirModal();
  initPipelineConfigureRun();
  initHistorySelection();
}

/**
 * Initialise the directory browser modal for source/output selection.
 *
 * @returns {void}
 */
function initDirModal() {
  const modal = document.getElementById('dir-modal');
  const backdrop = document.getElementById('dir-modal-backdrop');
  const closeBtn = document.getElementById('dir-modal-close');
  const cancelBtn = document.getElementById('dir-modal-cancel');
  const selectBtn = document.getElementById('dir-modal-select');

  function openModal(target, mode) {
    _dirModalTarget = target;
    _dirModalMode = mode || 'directory';
    _dirModalSelectedFile = null;
    const titleEl = document.getElementById('dir-modal-title');
    if (mode === 'file') {
      titleEl.textContent = 'Select Source File';
    } else {
      titleEl.textContent = target === 'source' ? 'Select Source Directory' : 'Select Output Directory';
    }
    selectBtn.disabled = true;
    modal.classList.remove('hidden');
    browseTo(_dirModalCurrentPath);
  }

  document.getElementById('pipe-browse-source')?.addEventListener('click', () => openModal('source', 'directory'));
  document.getElementById('pipe-browse-output')?.addEventListener('click', () => openModal('output', 'directory'));
  document.getElementById('pipe-select-files')?.addEventListener('click',  () => openModal('source', 'file'));

  selectBtn.addEventListener('click', () => {
    /* In file mode, use the selected file; in directory mode, use the current directory */
    const selected = _dirModalMode === 'file' ? _dirModalSelectedFile : _dirModalCurrentPath;
    if (!selected) return;

    /* Special case: changing the output base for corpus discovery.
     * After the base path is updated on the server, refresh the corpus
     * dropdowns so runs from the new location appear immediately. */
    if (_dirModalTarget === 'output-base') {
      modal.classList.add('hidden');
      fetch('/api/settings/output-base', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selected }),
      })
        .then(r => r.json())
        .then(data => {
          if (data.error) {
            _ctx.setStatus(`Error: ${data.error}`);
            return;
          }
          _ctx.setStatus(`Output base changed to ${data.output_base}`);
          /* Repopulate corpus dropdowns with runs from the new base */
          _ctx.populateCorpusDropdowns();
        })
        .catch(err => _ctx.setStatus(`Error: ${err.message}`));
      return;
    }

    if (_dirModalTarget === 'source') {
      _ctx.state.pipeSource = selected;
      const el = document.getElementById('pipe-source-path');
      el.textContent = selected;
      el.classList.add('is-set');
      document.getElementById('sb-pipe-source').textContent = selected.split('/').pop() || selected;
    } else {
      _ctx.state.pipeOutput = selected;
      const el = document.getElementById('pipe-output-path');
      el.textContent = selected;
      el.classList.add('is-set');
    }

    checkPipelineReady();
    modal.classList.add('hidden');
  });

  /* Close / Cancel / Backdrop — just hide the directory browser modal. */
  [closeBtn, cancelBtn, backdrop].forEach(el => {
    el?.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  });
}

/**
 * Fetch directory contents from API and render in the modal.
 *
 * @param {string} dirPath - Directory path to browse.
 * @returns {void}
 */
function browseTo(dirPath) {
  const browser = document.getElementById('dir-browser');
  if (!browser) return;
  browser.innerHTML = '<p class="placeholder-text">Loading…</p>';

  const selectBtn = document.getElementById('dir-modal-select');

  fetch('/api/browse-directory', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: dirPath }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        browser.innerHTML = `<p class="placeholder-text">${data.error}</p>`;
        return;
      }
      _dirModalCurrentPath = data.path;
      _dirModalSelectedFile = null;

      /* In directory mode, enable Select as soon as we have a valid path */
      if (_dirModalMode === 'directory') {
        selectBtn.disabled = false;
      } else {
        selectBtn.disabled = true;  /* file mode: wait for a file click */
      }
      browser.innerHTML = '';

      /* Breadcrumb with current path */
      const pathEl = document.createElement('div');
      pathEl.className = 'u-mono u-muted';
      pathEl.style.cssText = 'font-size:var(--text-xs);padding:0.25rem 0;margin-bottom:0.25rem;';
      pathEl.textContent = data.path;
      browser.appendChild(pathEl);

      /* Parent directory link */
      if (data.parent) {
        const parentEl = document.createElement('div');
        parentEl.className = 'corpus-browser__item';
        parentEl.innerHTML = '<span class="u-accent u-mono">../</span><span class="u-muted">parent directory</span>';
        parentEl.addEventListener('click', () => browseTo(data.parent));
        browser.appendChild(parentEl);
      }

      /* Directory and file entries */
      (data.entries || []).forEach(entry => {
        const el = document.createElement('div');
        el.className = 'corpus-browser__item';
        if (entry.type === 'directory') {
          el.innerHTML = `<span class="u-accent u-mono">${entry.name}/</span>`;
          el.addEventListener('click', () => browseTo(entry.path));
        } else {
          const kb = entry.size ? ` · ${(entry.size / 1024).toFixed(1)} KB` : '';
          el.innerHTML = `<span class="u-mono">${entry.name}</span><span class="u-muted">${kb}</span>`;

          /* In file mode, clicking a file selects it */
          if (_dirModalMode === 'file') {
            el.style.cursor = 'pointer';
            el.addEventListener('click', () => {
              /* Deselect previous */
              browser.querySelectorAll('.corpus-browser__item.is-selected')
                .forEach(prev => prev.classList.remove('is-selected'));
              el.classList.add('is-selected');
              _dirModalSelectedFile = entry.path;
              selectBtn.disabled = false;
            });
          }
        }
        browser.appendChild(el);
      });

      if (!data.entries || data.entries.length === 0) {
        const emptyEl = document.createElement('p');
        emptyEl.className = 'placeholder-text';
        emptyEl.textContent = '(empty directory)';
        browser.appendChild(emptyEl);
      }
    })
    .catch(err => {
      browser.innerHTML = `<p class="placeholder-text">Error: ${err.message}</p>`;
    });
}

/**
 * Enable/disable the pipeline run button based on source/output readiness.
 *
 * @returns {void}
 */
export function checkPipelineReady() {
  const ready = !!(_ctx.state.pipeSource && _ctx.state.pipeOutput);
  const runBtn = document.getElementById('pipe-run-btn');
  if (runBtn) runBtn.disabled = !ready;
  if (ready) {
    document.getElementById('pipe-status-text').textContent =
      `Ready — ${_ctx.state.pipeSource.split('/').pop()} → ${_ctx.state.pipeOutput.split('/').pop()}`;
  }
}

/**
 * Wire pipeline run/cancel button actions.
 *
 * @returns {void}
 */
function initPipelineConfigureRun() {
  document.getElementById('pipe-run-btn')?.addEventListener('click', startPipelineRun);
  document.getElementById('pipe-cancel-btn')?.addEventListener('click', cancelPipelineRun);
}

/**
 * Start a pipeline run from configured UI values.
 *
 * @returns {void}
 */
function startPipelineRun() {
  if (_ctx.state.pipeJobRunning) return;

  /* Read config from UI */
  const extractor = _ctx.state.pipeExtractor || 'pyphen';
  const langEl = document.querySelector('.lang-option.is-selected input[type="radio"]');
  const language = langEl ? langEl.value : 'auto';

  if (!_ctx.state.pipeSource) {
    _ctx.setStatus('Pipeline: select a source directory first');
    return;
  }

  const logEl = document.getElementById('monitor-log');
  const fillEl = document.getElementById('monitor-progress-fill');
  const statusEl = document.getElementById('monitor-job-status');
  const stageEl = document.getElementById('monitor-job-stage');
  const pctEl = document.getElementById('monitor-job-pct');
  const badge = document.getElementById('monitor-status-badge');
  const runBtn = document.getElementById('pipe-run-btn');
  const cancelBtn = document.getElementById('pipe-cancel-btn');

  /* Reset UI */
  logEl.innerHTML = '';
  fillEl.style.width = '0%';
  statusEl.textContent = 'starting…';
  statusEl.style.color = 'var(--col-warn)';
  stageEl.textContent = '—';
  pctEl.textContent = '0%';
  badge.textContent = 'Starting';
  badge.className = 'badge is-running';
  runBtn.disabled = true;
  cancelBtn.disabled = false;

  ['extract', 'normalize', 'annotate'].forEach(s => {
    const ind = document.getElementById(`stage-ind-${s}`);
    if (ind) ind.className = 'stage-indicator';
  });

  _ctx.setStatus('Pipeline: starting…');
  document.getElementById('sb-pipe-job-status').textContent = 'starting';

  /* POST to start pipeline */
  fetch('/api/pipeline/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      extractor: extractor,
      language: language,
      source_path: _ctx.state.pipeSource,
      output_dir: _ctx.state.pipeOutput || null,
    }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        statusEl.textContent = 'error';
        badge.textContent = 'Error';
        badge.className = 'badge is-error';
        runBtn.disabled = false;
        cancelBtn.disabled = true;
        _ctx.setStatus(`Pipeline: ${data.error}`);
        return;
      }
      _ctx.state.pipeJobRunning = true;
      _lastLogOffset = 0;
      startPipelinePolling();
    })
    .catch(err => {
      statusEl.textContent = 'error';
      runBtn.disabled = false;
      cancelBtn.disabled = true;
      _ctx.setStatus(`Pipeline: ${err.message}`);
    });
}

/**
 * Start monitor polling interval.
 *
 * @returns {void}
 */
function startPipelinePolling() {
  if (_pipelinePoller) clearInterval(_pipelinePoller);
  _pipelinePoller = setInterval(pollPipelineStatus, 500);
}

/**
 * Poll pipeline status endpoint and update monitor UI.
 *
 * @returns {void}
 */
function pollPipelineStatus() {
  fetch('/api/pipeline/status')
    .then(r => r.json())
    .then(data => {
      const logEl = document.getElementById('monitor-log');
      const fillEl = document.getElementById('monitor-progress-fill');
      const statusEl = document.getElementById('monitor-job-status');
      const stageEl = document.getElementById('monitor-job-stage');
      const pctEl = document.getElementById('monitor-job-pct');
      const badge = document.getElementById('monitor-status-badge');

      /* Append new log lines */
      const lines = data.log_lines || [];
      for (let i = _lastLogOffset; i < lines.length; i++) {
        const line = lines[i];
        const span = document.createElement('span');
        span.className = `log-line ${line.cls}`;
        span.textContent = line.text;
        logEl.appendChild(span);
      }
      _lastLogOffset = lines.length;
      logEl.scrollTop = logEl.scrollHeight;

      /* Update progress */
      const pct = data.progress_percent || 0;
      fillEl.style.width = `${pct}%`;
      pctEl.textContent = `${pct}%`;

      /* Update stage */
      if (data.current_stage) {
        stageEl.textContent = data.current_stage;
        updateStageIndicators(data.current_stage);
      }

      statusEl.textContent = data.status;
      document.getElementById('sb-pipe-job-status').textContent = data.status;

      /* Terminal states */
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        _ctx.state.pipeJobRunning = false;
        clearInterval(_pipelinePoller);
        _pipelinePoller = null;

        const runBtn = document.getElementById('pipe-run-btn');
        const cancelBtn = document.getElementById('pipe-cancel-btn');
        runBtn.disabled = false;
        cancelBtn.disabled = true;

        if (data.status === 'completed') {
          statusEl.style.color = 'var(--col-ok)';
          badge.textContent = 'Completed';
          badge.className = 'badge is-done';
          _ctx.setStatus('Pipeline: run complete');
          /* Auto-refresh corpus dropdowns so the new run appears immediately. */
          _ctx.populateCorpusDropdowns();
        } else if (data.status === 'failed') {
          statusEl.style.color = 'var(--col-error, red)';
          badge.textContent = 'Failed';
          badge.className = 'badge is-error';
          _ctx.setStatus(`Pipeline: failed — ${data.error_message || 'unknown error'}`);
        } else {
          statusEl.style.color = 'var(--col-text-muted)';
          badge.textContent = 'Cancelled';
          badge.className = 'badge badge--muted';
          _ctx.setStatus('Pipeline: cancelled');
        }
      } else {
        statusEl.style.color = 'var(--col-warn)';
        badge.textContent = 'Running';
        badge.className = 'badge is-running';
        _ctx.setStatus(`Pipeline: ${data.current_stage || 'running'}…`);
      }
    })
    .catch(() => { /* ignore polling errors */ });
}

/**
 * Update stage indicator chips based on current stage.
 *
 * @param {string} currentStage - Current pipeline stage key.
 * @returns {void}
 */
function updateStageIndicators(currentStage) {
  const order = ['extract', 'normalize', 'annotate', 'database'];
  const idx = order.indexOf(currentStage);

  order.forEach((s, i) => {
    const ind = document.getElementById(`stage-ind-${s}`);
    if (!ind) return;
    if (i < idx) ind.className = 'stage-indicator is-done';
    else if (i === idx) ind.className = 'stage-indicator is-running';
    /* leave future stages unchanged */
  });

  if (currentStage === 'complete') {
    order.forEach(s => {
      const ind = document.getElementById(`stage-ind-${s}`);
      if (ind) ind.className = 'stage-indicator is-done';
    });
  }
}

/**
 * Request cancellation of an in-flight pipeline run.
 *
 * @returns {void}
 */
function cancelPipelineRun() {
  if (!_ctx.state.pipeJobRunning) return;

  fetch('/api/pipeline/cancel', { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      /* Polling will pick up the cancelled state. */
    })
    .catch(() => { /* ignore */ });
}

/**
 * Initialise history panel selection and initial load.
 *
 * @returns {void}
 */
function initHistorySelection() {
  loadHistoryRuns();
}

/**
 * Fetch and render discovered pipeline runs in the history panel.
 *
 * @returns {void}
 */
function loadHistoryRuns() {
  const container = document.getElementById('history-runs');
  if (!container) return;

  fetch('/api/pipeline/runs')
    .then(r => r.json())
    .then(data => {
      _historyRuns = data.runs || [];
      container.innerHTML = '';

      if (_historyRuns.length === 0) {
        container.innerHTML = '<p class="placeholder-text">No pipeline runs found.</p>';
        return;
      }

      _historyRuns.forEach((run, idx) => {
        const ts = run.timestamp || '';
        const dateStr = ts.length >= 13
          ? `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(9, 11)}:${ts.slice(11, 13)}`
          : ts;

        const row = document.createElement('div');
        row.className = 'history-run' + (idx === 0 ? ' is-selected' : '');
        row.dataset.runId = run.path.split('/').pop();
        row.innerHTML = [
          `<span class="history-run__date u-muted">${dateStr}</span>`,
          `<span class="history-run__name u-accent">${run.extractor_type}</span>`,
          `<span class="badge badge--success">${run.syllable_count.toLocaleString()} syl</span>`,
        ].join('');

        row.addEventListener('click', () => {
          container.querySelectorAll('.history-run').forEach(r => r.classList.remove('is-selected'));
          row.classList.add('is-selected');
          populateHistoryDetail(run);
        });

        container.appendChild(row);
      });

      /* Auto-select first run */
      if (_historyRuns.length > 0) {
        populateHistoryDetail(_historyRuns[0]);
      }
    })
    .catch(() => {
      container.innerHTML = '<p class="placeholder-text">Failed to load runs.</p>';
    });
}

/**
 * Populate right-hand history details from one run payload.
 *
 * @param {{path: string, timestamp?: string, extractor_type: string, syllable_count: number, selection_count?: number}} run - Selected run metadata.
 * @returns {void}
 */
function populateHistoryDetail(run) {
  if (!run) return;

  const dirName = run.path.split('/').pop();
  const ts = run.timestamp || '';
  const dateStr = ts.length >= 13
    ? `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(9, 11)}:${ts.slice(11, 13)}:${ts.slice(13, 15)}`
    : ts;

  document.getElementById('history-detail-name').textContent = dirName;
  document.getElementById('hd-status').textContent = 'completed';
  document.getElementById('hd-started').textContent = dateStr;
  document.getElementById('hd-duration').textContent = '—';
  document.getElementById('hd-extractor').textContent = run.extractor_type;
  document.getElementById('hd-source').textContent = '—';
  document.getElementById('hd-files').textContent = '—';
  document.getElementById('hd-output').textContent = run.path;
  document.getElementById('hd-syllables').textContent = `${run.syllable_count.toLocaleString()} unique`;

  /* Stage indicators — all discovered runs completed all stages */
  const stageEls = document.querySelectorAll('.history-stages .stage-indicator');
  const stageNames = ['Extract', 'Normalize', 'Annotate'];
  stageEls.forEach((el, i) => {
    el.className = 'stage-indicator is-done';
    el.querySelector('.stage-indicator__label').textContent = stageNames[i];
  });

  /* Output tree */
  const treeEl = document.getElementById('history-output-tree');
  if (treeEl) {
    const selCount = run.selection_count || 0;
    const selLine = selCount > 0 ? `\n├── selections/           ${selCount} name classes` : '';
    treeEl.textContent = [
      `${dirName}/`,
      `├── data/`,
      `│   ├── corpus.db         ${run.syllable_count.toLocaleString()} syllables`,
      `│   └── *_annotated.json  annotated data`,
      selLine,
    ].filter(Boolean).join('\n');
  }
}
