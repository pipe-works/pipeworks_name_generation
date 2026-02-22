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
let _activePipelineStages = ['extract', 'normalize', 'annotate', 'database'];
let _defaultOutputBase = null;
let _selectedHistoryRunId = null;
let _historyRequestSeq = 0;

/**
 * Replace an element's content with one placeholder paragraph.
 *
 * @param {HTMLElement} el - Container element.
 * @param {string} message - Placeholder message.
 * @returns {void}
 */
function setPlaceholder(el, message) {
  if (!el) return;
  el.replaceChildren();
  const p = document.createElement('p');
  p.className = 'placeholder-text';
  p.textContent = message;
  el.appendChild(p);
}

/**
 * Resolve canonical run id from one run payload.
 *
 * @param {{run_id?: string, path?: string}} run - Run metadata from API.
 * @returns {string}
 */
function getRunId(run) {
  if (run && typeof run.run_id === 'string' && run.run_id.length > 0) {
    return run.run_id;
  }
  return '';
}

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
  initPipelineSettings();
  initDirModal();
  initPipelineConfigureRun();
  initPipelineStageToggles();
  initHistorySelection();
}

/**
 * Load server-side pipeline defaults used by the Configure panel.
 *
 * @returns {void}
 */
function initPipelineSettings() {
  fetch('/api/settings')
    .then(r => r.json())
    .then(data => {
      if (!data || data.error || !data.output_base) return;
      _defaultOutputBase = data.output_base;
      if (!_ctx.state.pipeOutput) {
        const el = document.getElementById('pipe-output-path');
        if (el) {
          el.textContent = `${_defaultOutputBase} (default)`;
          el.classList.add('is-set');
        }
      }
      checkPipelineReady();
    })
    .catch(() => { /* fallback to server defaults at run time */ });
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
  setPlaceholder(browser, 'Loading…');

  const selectBtn = document.getElementById('dir-modal-select');

  fetch('/api/browse-directory', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: dirPath }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        setPlaceholder(browser, String(data.error));
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
      browser.replaceChildren();

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
        const parentPath = document.createElement('span');
        parentPath.className = 'u-accent u-mono';
        parentPath.textContent = '../';
        const parentLabel = document.createElement('span');
        parentLabel.className = 'u-muted';
        parentLabel.textContent = 'parent directory';
        parentEl.append(parentPath, parentLabel);
        parentEl.addEventListener('click', () => browseTo(data.parent));
        browser.appendChild(parentEl);
      }

      /* Directory and file entries */
      (data.entries || []).forEach(entry => {
        const el = document.createElement('div');
        el.className = 'corpus-browser__item';
        if (entry.type === 'directory') {
          const nameEl = document.createElement('span');
          nameEl.className = 'u-accent u-mono';
          nameEl.textContent = `${entry.name}/`;
          el.appendChild(nameEl);
          el.addEventListener('click', () => browseTo(entry.path));
        } else {
          const kb = entry.size ? ` · ${(entry.size / 1024).toFixed(1)} KB` : '';
          const nameEl = document.createElement('span');
          nameEl.className = 'u-mono';
          nameEl.textContent = entry.name;
          const kbEl = document.createElement('span');
          kbEl.className = 'u-muted';
          kbEl.textContent = kb;
          el.append(nameEl, kbEl);

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
      setPlaceholder(browser, `Error: ${err.message}`);
    });
}

/**
 * Enable/disable the pipeline run button based on source/output readiness.
 *
 * @returns {void}
 */
export function checkPipelineReady() {
  const ready = !!_ctx.state.pipeSource;
  const runBtn = document.getElementById('pipe-run-btn');
  if (runBtn) runBtn.disabled = !ready;
  if (ready) {
    const outputLabel = _ctx.state.pipeOutput || _defaultOutputBase || '(server default)';
    document.getElementById('pipe-status-text').textContent =
      `Ready — ${_ctx.state.pipeSource.split('/').pop()} → ${outputLabel.split('/').pop()}`;
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
 * Enforce stage dependency in Configure UI.
 *
 * Annotate requires Normalize output. When Normalize is unchecked,
 * Annotate is auto-unchecked and disabled.
 *
 * @returns {void}
 */
function initPipelineStageToggles() {
  const normalizeEl = document.getElementById('stage-normalize');
  const annotateEl = document.getElementById('stage-annotate');

  if (!normalizeEl || !annotateEl) return;

  const sync = () => {
    if (!normalizeEl.checked) {
      annotateEl.checked = false;
      annotateEl.disabled = true;
    } else {
      annotateEl.disabled = false;
    }
  };

  normalizeEl.addEventListener('change', sync);
  sync();
}

/**
 * Read selected language for pipeline start.
 *
 * For pyphen, a non-empty custom language code overrides the radio selection.
 * For nltk, language is forced to "auto" (backend extractor ignores pyphen locales).
 *
 * @param {string} extractor - Selected extractor ("pyphen" or "nltk")
 * @returns {string}
 */
function readPipelineLanguage(extractor) {
  if (extractor !== 'pyphen') return 'auto';

  const custom = document.getElementById('custom-lang')?.value?.trim();
  if (custom) return custom;

  const langEl = document.querySelector('.lang-option.is-selected input[type="radio"]');
  return langEl ? langEl.value : 'auto';
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
  const language = readPipelineLanguage(extractor);
  const filePattern = document.getElementById('pipe-pattern')?.value?.trim() || '*.txt';
  const minRaw = document.getElementById('pipe-min-len')?.value ?? '';
  const maxRaw = document.getElementById('pipe-max-len')?.value ?? '';
  const minParsed = parseInt(minRaw, 10);
  const maxParsed = parseInt(maxRaw, 10);
  const minSyllableLength = Number.isNaN(minParsed) ? 2 : minParsed;
  const maxSyllableLength = Number.isNaN(maxParsed) ? 8 : maxParsed;
  const runNormalize = !!document.getElementById('stage-normalize')?.checked;
  const runAnnotate = runNormalize && !!document.getElementById('stage-annotate')?.checked;
  _activePipelineStages = ['extract'];
  if (runNormalize) _activePipelineStages.push('normalize');
  if (runAnnotate) {
    _activePipelineStages.push('annotate');
    _activePipelineStages.push('database');
  }

  if (!_ctx.state.pipeSource) {
    _ctx.setStatus('Pipeline: select a source directory first');
    return;
  }

  if (minSyllableLength < 1 || maxSyllableLength < 1) {
    _ctx.setStatus('Pipeline: min/max syllable length must be >= 1');
    return;
  }

  if (minSyllableLength > maxSyllableLength) {
    _ctx.setStatus('Pipeline: min syllable length must be <= max syllable length');
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

  ['extract', 'normalize', 'annotate', 'database'].forEach(s => {
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
      file_pattern: filePattern,
      min_syllable_length: minSyllableLength,
      max_syllable_length: maxSyllableLength,
      run_normalize: runNormalize,
      run_annotate: runAnnotate,
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
          _ctx.setStatus(data.output_path
            ? `Pipeline: run complete (${data.output_path})`
            : 'Pipeline: run complete');
          loadHistoryRuns({ forceNewest: true });
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
    if (!_activePipelineStages.includes(s)) {
      ind.className = 'stage-indicator';
      return;
    }
    if (i < idx) ind.className = 'stage-indicator is-done';
    else if (i === idx) ind.className = 'stage-indicator is-running';
    /* leave future stages unchanged */
  });

  if (currentStage === 'complete') {
    order.forEach(s => {
      const ind = document.getElementById(`stage-ind-${s}`);
      if (!ind) return;
      ind.className = _activePipelineStages.includes(s)
        ? 'stage-indicator is-done'
        : 'stage-indicator';
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
  window.addEventListener('pw:screen-changed', ev => {
    if (ev?.detail?.screenId === 'pipeline-history') {
      loadHistoryRuns();
    }
  });
  loadHistoryRuns({ forceNewest: true });
}

/**
 * Fetch and render discovered pipeline runs in the history panel.
 *
 * @param {{forceNewest?: boolean}=} opts - Optional refresh behavior.
 * @returns {void}
 */
function loadHistoryRuns(opts = {}) {
  const container = document.getElementById('history-runs');
  if (!container) return;
  const forceNewest = !!opts.forceNewest;
  const requestSeq = ++_historyRequestSeq;
  const preferredRunId = forceNewest ? null : _selectedHistoryRunId;

  fetch('/api/pipeline/runs')
    .then(r => r.json())
    .then(data => {
      if (requestSeq !== _historyRequestSeq) return;
      _historyRuns = data.runs || [];
      container.replaceChildren();

      if (_historyRuns.length === 0) {
        _selectedHistoryRunId = null;
        setPlaceholder(container, 'No pipeline runs found.');
        clearHistoryDetail();
        return;
      }

      let selectedRun = null;
      _historyRuns.forEach((run, idx) => {
        const ts = run.timestamp || '';
        const dateStr = ts.length >= 13
          ? `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(9, 11)}:${ts.slice(11, 13)}`
          : ts;
        const runId = getRunId(run);
        const isSelected = preferredRunId ? runId === preferredRunId : idx === 0;
        if (isSelected && !selectedRun) selectedRun = run;

        const row = document.createElement('div');
        row.className = 'history-run' + (isSelected ? ' is-selected' : '');
        row.dataset.runId = runId;
        const dateEl = document.createElement('span');
        dateEl.className = 'history-run__date u-muted';
        dateEl.textContent = dateStr;
        const nameEl = document.createElement('span');
        nameEl.className = 'history-run__name u-accent';
        nameEl.textContent = run.extractor_type;
        const badgeEl = document.createElement('span');
        badgeEl.className = 'badge badge--success';
        badgeEl.textContent = `${run.syllable_count.toLocaleString()} syl`;
        row.append(dateEl, nameEl, badgeEl);

        row.addEventListener('click', () => {
          container.querySelectorAll('.history-run').forEach(r => r.classList.remove('is-selected'));
          row.classList.add('is-selected');
          _selectedHistoryRunId = runId;
          populateHistoryDetail(run);
        });

        container.appendChild(row);
      });

      if (!selectedRun) {
        selectedRun = _historyRuns[0];
      }
      if (selectedRun) {
        _selectedHistoryRunId = getRunId(selectedRun);
        populateHistoryDetail(selectedRun);
      }
    })
    .catch(() => {
      if (requestSeq !== _historyRequestSeq) return;
      setPlaceholder(container, 'Failed to load runs.');
    });
}

/**
 * Reset History detail panel to placeholder values.
 *
 * @returns {void}
 */
function clearHistoryDetail() {
  document.getElementById('history-detail-name').textContent = '—';
  document.getElementById('hd-status').textContent = '—';
  document.getElementById('hd-started').textContent = '—';
  document.getElementById('hd-duration').textContent = '—';
  document.getElementById('hd-extractor').textContent = '—';
  document.getElementById('hd-source').textContent = '—';
  document.getElementById('hd-source').removeAttribute('title');
  document.getElementById('hd-files').textContent = '—';
  document.getElementById('hd-output').textContent = '—';
  document.getElementById('hd-syllables').textContent = '—';
  document.getElementById('hd-ipc-input').textContent = '—';
  document.getElementById('hd-ipc-input').removeAttribute('title');
  document.getElementById('hd-ipc-output').textContent = '—';
  document.getElementById('hd-ipc-output').removeAttribute('title');
  const treeEl = document.getElementById('history-output-tree');
  if (treeEl) {
    treeEl.textContent = '(Select a run to view details)';
  }
}

/**
 * Build a compact display form for long hash strings.
 *
 * @param {string | null | undefined} value - Hash value to render.
 * @returns {string} Compact hash text for UI.
 */
function compactHash(value) {
  if (typeof value !== 'string' || value.length === 0) return 'n/a';
  if (value.length <= 24) return value;
  return `${value.slice(0, 12)}...${value.slice(-12)}`;
}

/**
 * Populate right-hand history details from one run payload.
 *
 * @param {{path: string, timestamp?: string, extractor_type: string, syllable_count: number, selection_count?: number}} run - Selected run metadata.
 * @returns {void}
 */
function populateHistoryDetail(run) {
  if (!run) return;

  const dirName = getRunId(run) || 'unknown';
  const ts = run.timestamp || '';
  const startedUtc = typeof run.created_at_utc === 'string' ? run.created_at_utc : null;
  const dateStr = ts.length >= 13
    ? `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(9, 11)}:${ts.slice(11, 13)}:${ts.slice(13, 15)}`
    : ts;
  const startedDisplay = startedUtc && startedUtc.length >= 19
    ? startedUtc.replace('T', ' ').replace('Z', '')
    : dateStr;

  document.getElementById('history-detail-name').textContent = dirName;
  document.getElementById('hd-status').textContent = run.status || 'unknown';
  document.getElementById('hd-started').textContent = startedDisplay;
  document.getElementById('hd-duration').textContent = run.processing_time || 'n/a';
  document.getElementById('hd-extractor').textContent = run.extractor_type;
  const sourceEl = document.getElementById('hd-source');
  if (run.source_path) {
    const sourceBits = run.source_path.split('/');
    sourceEl.textContent = sourceBits[sourceBits.length - 1] || run.source_path;
    sourceEl.title = run.source_path;
  } else {
    sourceEl.textContent = 'n/a';
    sourceEl.removeAttribute('title');
  }
  if (typeof run.files_processed === 'number') {
    document.getElementById('hd-files').textContent =
      `${run.files_processed.toLocaleString()} ${run.files_processed === 1 ? 'file' : 'files'}`;
  } else {
    document.getElementById('hd-files').textContent = 'n/a';
  }
  document.getElementById('hd-output').textContent = run.path;
  document.getElementById('hd-syllables').textContent = `${run.syllable_count.toLocaleString()} unique`;
  const ipcInputEl = document.getElementById('hd-ipc-input');
  const ipcOutputEl = document.getElementById('hd-ipc-output');
  ipcInputEl.textContent = compactHash(run.ipc_input_hash);
  ipcOutputEl.textContent = compactHash(run.ipc_output_hash);
  if (typeof run.ipc_input_hash === 'string' && run.ipc_input_hash.length > 0) {
    ipcInputEl.title = run.ipc_input_hash;
  } else {
    ipcInputEl.removeAttribute('title');
  }
  if (typeof run.ipc_output_hash === 'string' && run.ipc_output_hash.length > 0) {
    ipcOutputEl.title = run.ipc_output_hash;
  } else {
    ipcOutputEl.removeAttribute('title');
  }

  /* Stage indicators come from manifest stage_statuses */
  const stageEls = document.querySelectorAll('.history-stages .stage-indicator');
  const stageNames = ['Extract', 'Normalize', 'Annotate', 'Database'];
  const stageKeys = ['extract', 'normalize', 'annotate', 'database'];
  stageEls.forEach((el, i) => {
    const stageKey = stageKeys[i];
    const stageStatus = run.stage_statuses && typeof run.stage_statuses === 'object'
      ? run.stage_statuses[stageKey]
      : null;
    const done = stageStatus === 'completed';
    el.className = done ? 'stage-indicator is-done' : 'stage-indicator';
    el.querySelector('.stage-indicator__label').textContent = stageNames[i];
  });

  /* Output tree */
  const treeEl = document.getElementById('history-output-tree');
  if (treeEl) {
    treeEl.textContent = Array.isArray(run.output_tree_lines) && run.output_tree_lines.length > 0
      ? run.output_tree_lines.join('\n')
      : '(No manifest artifact tree available)';
  }
}
