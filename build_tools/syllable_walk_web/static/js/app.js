/*
   app.js
   ─────────────────────────────────────────────────────────────────────────
   Client-side logic for the Pipe-Works Build Tools web application.
   Communicates with the Python HTTP server via JSON API.

   SECTIONS
   ────────
   1.  Theme Toggle
   2.  Tool Switcher (Pipeline / Walker)
   3.  Sub-screen Tab Navigation
   4.  Spinner Buttons
   5.  Slider Live Values
   6.  Profile Selection
   7.  Language Option Selection
   8.  Radio Option Selection
   9.  Seed Randomise
   10. Corpus Browser Modal (Walker) — API
   11. Directory Browser Modal (Pipeline) — API
   12. Generate Walks — API
   13. Generate Candidates — API
   14. Select Names — API
   15. Export TXT — API
   16. Render Screen — Combine Toggle
   17. Package Build — API
   18. Analysis Screen Population — API
   19. Pipeline Configure — Run Button Enable
   20. Pipeline Monitor — API Polling
   21. Pipeline History — API
   22. Status Bar
   23. Init
   ═══════════════════════════════════════════════════════════════════════════ */

'use strict';

/* ─────────────────────────────────────────────────────────────────────────
   Cached run data for history screen (populated from API)
   ───────────────────────────────────────────────────────────────────────── */

let _historyRuns = [];  /* populated by loadHistoryRuns() */

/* ─────────────────────────────────────────────────────────────────────────
   App state
   ───────────────────────────────────────────────────────────────────────── */

const state = {
  activeTool:   'pipeline',
  activeScreen: 'pipeline-configure',
  corpusA: null,
  corpusB: null,
  walksA:  [],
  walksB:  [],
  namesA:  [],
  namesB:  [],
  pipeSource: null,
  pipeOutput: null,
  pipeExtractor: 'pyphen',
  pipeJobRunning: false,
  pipeJobTimer: null,
};


/* ═══════════════════════════════════════════════════════════════════════════
   1. THEME TOGGLE
   ═══════════════════════════════════════════════════════════════════════════ */

function initTheme() {
  const btn = document.getElementById('theme-toggle');
  const saved = localStorage.getItem('pw-theme') || 'dark';
  applyTheme(saved);

  btn.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    applyTheme(next);
    localStorage.setItem('pw-theme', next);
  });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const btn = document.getElementById('theme-toggle');
  btn.textContent = theme === 'light' ? 'Dark Theme' : 'Light Theme';
}


/* ═══════════════════════════════════════════════════════════════════════════
   2. TOOL SWITCHER (Pipeline / Walker)
   ═══════════════════════════════════════════════════════════════════════════ */

function initToolSwitcher() {
  document.querySelectorAll('.tool-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      const tool = btn.dataset.tool;
      if (tool === state.activeTool) return;
      switchTool(tool);
    });
  });
}

function switchTool(tool) {
  state.activeTool = tool;

  /* Update tool tab active state */
  document.querySelectorAll('.tool-tab').forEach(b => {
    b.classList.toggle('is-active', b.dataset.tool === tool);
    b.setAttribute('aria-current', b.dataset.tool === tool ? 'true' : 'false');
  });

  /* Show / hide sub-navs */
  document.getElementById('sub-nav-pipeline').classList.toggle('hidden', tool !== 'pipeline');
  document.getElementById('sub-nav-walker').classList.toggle('hidden',   tool !== 'walker');

  /* Navigate to the first sub-screen of the selected tool */
  const firstTab = document.querySelector(`#sub-nav-${tool} .tab`);
  if (firstTab) {
    navigateToScreen(firstTab.dataset.screen);
  }

  /* Update status bar context */
  updateStatusBarContext(tool);
}

function updateStatusBarContext(tool) {
  document.querySelectorAll('.pipe-context').forEach(el => {
    el.classList.toggle('hidden', tool !== 'pipeline');
  });
  document.querySelectorAll('.walker-context').forEach(el => {
    el.classList.toggle('hidden', tool !== 'walker');
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   3. SUB-SCREEN TAB NAVIGATION
   ═══════════════════════════════════════════════════════════════════════════ */

function initTabNav() {
  document.querySelectorAll('.tab[data-screen]').forEach(btn => {
    btn.addEventListener('click', () => {
      navigateToScreen(btn.dataset.screen);
    });
  });
}

function navigateToScreen(screenId) {
  state.activeScreen = screenId;

  /* Hide all screens */
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.remove('is-visible');
    s.hidden = true;
  });

  /* Show target screen */
  const target = document.getElementById(`screen-${screenId}`);
  if (target) {
    target.classList.add('is-visible');
    target.hidden = false;
  }

  /* Update active tab within the current tool's sub-nav */
  const tool = state.activeTool;
  document.querySelectorAll(`#sub-nav-${tool} .tab`).forEach(t => {
    t.classList.toggle('is-active', t.dataset.screen === screenId);
  });

  /* Populate screens that need it */
  if (screenId === 'walker-blended') populateBlended();
  if (screenId === 'walker-render')   populateRender();
  if (screenId === 'walker-analysis') populateAnalysis();
  if (screenId === 'pipeline-monitor') syncMonitorFromConfig();
}


/* ═══════════════════════════════════════════════════════════════════════════
   4. SPINNER BUTTONS
   ═══════════════════════════════════════════════════════════════════════════ */

function initSpinners() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('.spinner-btn');
    if (!btn) return;
    const targetId = btn.dataset.target;
    const delta    = parseFloat(btn.dataset.delta);
    const input    = document.getElementById(targetId);
    if (!input) return;

    const min  = parseFloat(input.min);
    const max  = parseFloat(input.max);
    const step = parseFloat(input.step) || 1;
    let val = parseFloat(input.value) + delta;
    if (!isNaN(min)) val = Math.max(min, val);
    if (!isNaN(max)) val = Math.min(max, val);
    input.value = val;
    input.dispatchEvent(new Event('change'));

    /* Update walk steps suffix */
    if (targetId === 'walk-steps-a') {
      document.getElementById('walk-steps-a-suffix').textContent = `→ ${val + 1} syl`;
    }
    if (targetId === 'walk-steps-b') {
      document.getElementById('walk-steps-b-suffix').textContent = `→ ${val + 1} syl`;
    }

    /* Enable pipeline run button if source + output are set */
    checkPipelineReady();
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   5. SLIDER LIVE VALUES
   ═══════════════════════════════════════════════════════════════════════════ */

function initSliders() {
  document.querySelectorAll('input[type="range"]').forEach(slider => {
    const valEl = document.getElementById(`${slider.id}-val`);
    if (!valEl) return;
    slider.addEventListener('input', () => {
      valEl.textContent = parseFloat(slider.value).toFixed(1);
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   6. PROFILE SELECTION
   ═══════════════════════════════════════════════════════════════════════════ */

function initProfiles() {
  document.querySelectorAll('.profile-option').forEach(opt => {
    opt.addEventListener('click', () => {
      const patch = opt.dataset.patch;
      document.querySelectorAll(`.profile-option[data-patch="${patch}"]`)
        .forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   7. LANGUAGE OPTION SELECTION
   ═══════════════════════════════════════════════════════════════════════════ */

function initLangOptions() {
  document.querySelectorAll('.lang-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.lang-option').forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;
    });
  });

  /* Extractor type — disable lang grid when nltk selected */
  document.querySelectorAll('.profile-option[data-extractor]').forEach(opt => {
    opt.addEventListener('click', () => {
      const extractor = opt.dataset.extractor;
      state.pipeExtractor = extractor;
      document.querySelectorAll('.profile-option[data-extractor]')
        .forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;
      const langGrid = document.getElementById('lang-grid');
      langGrid.style.opacity = extractor === 'nltk' ? '0.4' : '1';
      langGrid.style.pointerEvents = extractor === 'nltk' ? 'none' : '';
      document.getElementById('sb-pipe-extractor').textContent = extractor;
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   8. RADIO OPTION SELECTION
   ═══════════════════════════════════════════════════════════════════════════ */

function initRadioOptions() {
  document.querySelectorAll('.radio-option').forEach(opt => {
    opt.addEventListener('click', () => {
      const name = opt.querySelector('input[type="radio"]')?.name;
      if (!name) return;
      document.querySelectorAll(`.radio-option input[name="${name}"]`).forEach(inp => {
        inp.closest('.radio-option').classList.remove('is-selected');
      });
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   9. SEED RANDOMISE
   ═══════════════════════════════════════════════════════════════════════════ */

function initSeedButtons() {
  /* Named buttons */
  ['seed-random-a', 'seed-random-b'].forEach(id => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const patch = id.endsWith('-a') ? 'a' : 'b';
      document.getElementById(`seed-${patch}`).value = Math.floor(Math.random() * 0xFFFFFF).toString(16);
    });
  });

  /* Generic data-random-seed buttons */
  document.addEventListener('click', e => {
    const btn = e.target.closest('[data-random-seed]');
    if (!btn) return;
    const targetId = btn.dataset.randomSeed;
    const input = document.getElementById(targetId);
    if (input) input.value = Math.floor(Math.random() * 0xFFFFFF).toString(16);
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   10. CORPUS BROWSER MODAL (Walker)
   ═══════════════════════════════════════════════════════════════════════════ */

let _corpusModalPatch = 'a';
let _corpusRuns = [];             /* cached run list from API */
let _walkerReadyPollers = {};     /* { a: intervalId, b: intervalId } */

function initCorpusModal() {
  const modal     = document.getElementById('corpus-modal');
  const backdrop  = document.getElementById('corpus-modal-backdrop');
  const closeBtn  = document.getElementById('corpus-modal-close');
  const cancelBtn = document.getElementById('corpus-modal-cancel');
  const selectBtn = document.getElementById('corpus-modal-select');

  /* Open — fetch runs every time */
  ['select-corpus-a', 'select-corpus-b'].forEach(id => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener('click', () => {
      _corpusModalPatch = id.endsWith('-a') ? 'a' : 'b';
      selectBtn.disabled = true;
      modal.classList.remove('hidden');
      refreshOutputBase();
      fetchCorpusRuns();
    });
  });

  /* Change output base — reuse the directory browser modal */
  document.getElementById('corpus-change-base')?.addEventListener('click', () => {
    /* Temporarily hide the corpus modal, open the dir modal to pick a folder */
    modal.classList.add('hidden');
    _changeOutputBaseActive = true;
    _dirModalTarget = 'output-base';
    _dirModalMode = 'directory';
    _dirModalSelectedFile = null;
    const dirModal = document.getElementById('dir-modal');
    const titleEl  = document.getElementById('dir-modal-title');
    titleEl.textContent = 'Select Run Discovery Directory';
    document.getElementById('dir-modal-select').disabled = true;
    dirModal.classList.remove('hidden');
    browseTo(_dirModalCurrentPath);
  });

  /* Confirm */
  selectBtn.addEventListener('click', () => {
    const selected = modal.querySelector('.corpus-browser__item.is-selected');
    if (!selected) return;
    const runId = selected.dataset.runId;
    const run   = _corpusRuns.find(r => r.path.split('/').pop() === runId);
    if (!run) return;

    modal.classList.add('hidden');
    loadCorpus(_corpusModalPatch, runId, run);
  });

  /* Close */
  [closeBtn, cancelBtn, backdrop].forEach(el => {
    el?.addEventListener('click', () => modal.classList.add('hidden'));
  });
}

let _changeOutputBaseActive = false;

/** Fetch the current output_base from the server and update the display. */
function refreshOutputBase() {
  fetch('/api/settings')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('corpus-output-base');
      if (el) el.textContent = data.output_base || '?';
    })
    .catch(() => {});
}

/** Fetch discovered runs from the API and populate the modal list. */
function fetchCorpusRuns() {
  const list    = document.getElementById('corpus-browser-list');
  const loading = document.getElementById('corpus-browser-loading');
  if (loading) loading.style.display = '';

  /* Also refresh the path display */
  refreshOutputBase();

  fetch('/api/pipeline/runs')
    .then(r => r.json())
    .then(data => {
      _corpusRuns = data.runs || [];
      if (loading) loading.style.display = 'none';
      list.querySelectorAll('.corpus-browser__item').forEach(el => el.remove());

      if (_corpusRuns.length === 0) {
        if (loading) {
          loading.style.display = '';
          loading.textContent = 'No pipeline runs found.';
        }
        return;
      }

      const selectBtn = document.getElementById('corpus-modal-select');

      _corpusRuns.forEach(run => {
        const runId = run.path.split('/').pop();
        const el = document.createElement('div');
        el.className = 'corpus-browser__item';
        el.dataset.runId = runId;
        el.innerHTML = `<span class="u-accent u-mono">${runId}/</span>`
          + `<span class="u-muted">${run.syllable_count.toLocaleString()} syllables`
          + `${run.selection_count ? ' · ' + run.selection_count + ' selections' : ''}`
          + ` · ${run.extractor_type}</span>`;

        el.addEventListener('click', () => {
          list.querySelectorAll('.corpus-browser__item').forEach(i => i.classList.remove('is-selected'));
          el.classList.add('is-selected');
          selectBtn.disabled = false;
        });

        list.appendChild(el);
      });
    })
    .catch(err => {
      if (loading) {
        loading.style.display = '';
        loading.textContent = `Error fetching runs: ${err.message}`;
      }
    });
}

/** Load a corpus into a patch via the API, then poll for walker readiness. */
function loadCorpus(patch, runId, run) {
  const P = patch.toUpperCase();
  const label = `${runId} · loading…`;

  document.getElementById(`corpus-status-${patch}`).textContent = label;
  document.getElementById(`corpus-status-${patch}`).classList.add('is-loaded');
  document.getElementById(`status-corpus-${patch}`).textContent = runId;
  state[`corpus${P}`] = runId;
  setStatus(`Patch ${P}: loading corpus ${runId}…`);

  fetch('/api/walker/load-corpus', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patch: patch, run_id: runId }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById(`corpus-status-${patch}`).textContent = `Error: ${data.error}`;
        setStatus(`Patch ${P}: ${data.error}`);
        return;
      }
      const syllCount = (data.syllable_count || 0).toLocaleString();
      document.getElementById(`corpus-status-${patch}`).textContent =
        `${runId} · ${syllCount} syllables · walker loading…`;
      setStatus(`Patch ${P}: ${syllCount} syllables loaded, walker initialising…`);

      /* Start polling for walker readiness */
      pollWalkerReady(patch);
    })
    .catch(err => {
      document.getElementById(`corpus-status-${patch}`).textContent = `Error: ${err.message}`;
      setStatus(`Patch ${P}: load failed — ${err.message}`);
    });
}

/** Poll /api/walker/stats until the walker for the given patch is ready. */
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
        if (info && info.walker_ready) {
          clearInterval(_walkerReadyPollers[patch]);
          _walkerReadyPollers[patch] = null;
          const runId = state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          document.getElementById(`corpus-status-${patch}`).textContent =
            `${runId} · ${count} syllables · walker ready ✓`;
          setStatus(`Patch ${P}: walker ready`);
        }
      })
      .catch(() => { /* ignore polling errors */ });
  }, 1000);
}


/* ═══════════════════════════════════════════════════════════════════════════
   11. DIRECTORY BROWSER MODAL (Pipeline) — API
   ═══════════════════════════════════════════════════════════════════════════ */

let _dirModalTarget = 'source';     /* 'source' or 'output' */
let _dirModalMode = 'directory';     /* 'directory' or 'file' */
let _dirModalCurrentPath = '.';
let _dirModalSelectedFile = null;    /* full path of selected file (file mode only) */

function initDirModal() {
  const modal     = document.getElementById('dir-modal');
  const backdrop  = document.getElementById('dir-modal-backdrop');
  const closeBtn  = document.getElementById('dir-modal-close');
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

    /* Special case: changing the output base for corpus discovery */
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
            setStatus(`Error: ${data.error}`);
            return;
          }
          setStatus(`Output base changed to ${data.output_base}`);
          /* Re-open the corpus modal with refreshed runs */
          const corpusModal = document.getElementById('corpus-modal');
          corpusModal.classList.remove('hidden');
          fetchCorpusRuns();
        })
        .catch(err => setStatus(`Error: ${err.message}`));
      _changeOutputBaseActive = false;
      return;
    }

    if (_dirModalTarget === 'source') {
      state.pipeSource = selected;
      const el = document.getElementById('pipe-source-path');
      el.textContent = selected;
      el.classList.add('is-set');
      document.getElementById('sb-pipe-source').textContent = selected.split('/').pop() || selected;
    } else {
      state.pipeOutput = selected;
      const el = document.getElementById('pipe-output-path');
      el.textContent = selected;
      el.classList.add('is-set');
    }

    checkPipelineReady();
    modal.classList.add('hidden');
  });

  [closeBtn, cancelBtn, backdrop].forEach(el => {
    el?.addEventListener('click', () => {
      modal.classList.add('hidden');
      /* If we were changing output base, re-open the corpus modal */
      if (_changeOutputBaseActive) {
        _changeOutputBaseActive = false;
        document.getElementById('corpus-modal')?.classList.remove('hidden');
      }
    });
  });
}

/** Fetch directory contents from API and render in the modal. */
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


/* ═══════════════════════════════════════════════════════════════════════════
   12. GENERATE WALKS (API)
   ═══════════════════════════════════════════════════════════════════════════ */

function initGenerateWalks() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      if (!state[`corpus${P}`]) {
        setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      const count = parseInt(document.getElementById(`walk-count-${patch}`).value) || 2;
      const steps = parseInt(document.getElementById(`walk-steps-${patch}`).value) || 5;

      /* Read profile */
      const profileEl = document.querySelector(`input[name="profile-${patch}"]:checked`);
      const profile = profileEl ? profileEl.value : 'custom';

      /* Read custom params */
      const temperature    = parseFloat(document.getElementById(`temp-${patch}`)?.value) || 0.7;
      const frequencyWeight = parseFloat(document.getElementById(`freq-${patch}`)?.value) || 0.0;
      const maxFlips       = parseInt(document.getElementById(`flips-${patch}`)?.value) || 2;

      /* Read seed */
      const seedStr = document.getElementById(`seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      const out = document.getElementById(`walks-output-${patch}`);
      out.innerHTML = '<span class="placeholder-text">Generating…</span>';
      btn.disabled = true;

      fetch('/api/walker/walk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patch: patch,
          count: count,
          steps: steps,
          profile: profile !== 'custom' ? profile : null,
          temperature: temperature,
          frequency_weight: frequencyWeight,
          max_flips: maxFlips,
          seed: seed,
        }),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            out.innerHTML = `<span class="placeholder-text">${data.error}</span>`;
            setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          const walks = (data.walks || []).map(w => w.formatted);
          state[`walks${P}`] = walks;

          out.innerHTML = walks.map(w => `<span class="walk-item">${w}</span>`).join('');
          setStatus(`Patch ${P}: ${walks.length} walk${walks.length !== 1 ? 's' : ''} generated`);
        })
        .catch(err => {
          btn.disabled = false;
          out.innerHTML = `<span class="placeholder-text">Error: ${err.message}</span>`;
          setStatus(`Patch ${P}: walk generation failed`);
        });
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   13. GENERATE CANDIDATES (API)
   ═══════════════════════════════════════════════════════════════════════════ */

function initGenerateCandidates() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-candidates-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      if (!state[`corpus${P}`]) {
        setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      const count = parseInt(document.getElementById(`comb-count-${patch}`).value) || 10000;
      const sylls = parseInt(document.getElementById(`comb-syllables-${patch}`).value) || 2;
      const seedStr = document.getElementById(`comb-seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      const out = document.getElementById(`comb-output-${patch}`);
      out.innerHTML = '<span class="placeholder-text">Generating candidates…</span>';
      btn.disabled = true;

      fetch('/api/walker/combine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patch: patch,
          count: count,
          syllables: sylls,
          seed: seed,
        }),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            out.innerHTML = `<span class="placeholder-text">${data.error}</span>`;
            setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          out.innerHTML = [
            `<span class="meta-key">generated  </span><span class="meta-val">${(data.generated || 0).toLocaleString()}</span>`,
            `<span class="meta-key">unique     </span><span class="meta-val">${(data.unique || 0).toLocaleString()}</span>`,
            `<span class="meta-key">duplicates </span><span class="meta-val">${(data.duplicates || 0).toLocaleString()}</span>`,
            `<span class="meta-key">syllables  </span><span class="meta-val">${data.syllables || sylls}</span>`,
            `<span class="meta-key">source     </span><span class="meta-path">${data.source || state[`corpus${P}`]}</span>`,
          ].join('<br/>');

          setStatus(`Patch ${P}: ${(data.unique || 0).toLocaleString()} unique candidates generated`);
        })
        .catch(err => {
          btn.disabled = false;
          out.innerHTML = `<span class="placeholder-text">Error: ${err.message}</span>`;
          setStatus(`Patch ${P}: combiner failed`);
        });
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   14. SELECT NAMES (API)
   ═══════════════════════════════════════════════════════════════════════════ */

function initSelectNames() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`select-names-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P     = patch.toUpperCase();
      const count = parseInt(document.getElementById(`sel-count-${patch}`).value) || 100;
      const cls   = document.getElementById(`sel-class-${patch}`)?.value || 'first_name';
      const seedStr = document.getElementById(`sel-seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      const metaEl = document.querySelector(`#sel-output-${patch} .selector-output__meta`);
      const listEl = document.getElementById(`sel-names-${patch}`);

      metaEl.innerHTML = '<span class="placeholder-text">Selecting…</span>';
      listEl.innerHTML = '';
      btn.disabled = true;

      fetch('/api/walker/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patch: patch,
          name_class: cls,
          count: count,
          seed: seed,
        }),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            metaEl.innerHTML = `<span class="placeholder-text">${data.error}</span>`;
            setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          const names = data.names || [];
          state[`names${P}`] = names;

          metaEl.innerHTML = [
            `<span class="meta-key">selected   </span><span class="meta-val">${data.count || names.length}</span>`,
            `<span class="meta-key">requested  </span><span class="meta-val">${data.requested || count}</span>`,
            `<span class="meta-key">class      </span><span class="meta-val">${data.name_class || cls}</span>`,
            `<span class="meta-key">patch      </span><span class="meta-path">${P}</span>`,
          ].join('<br/>');

          listEl.innerHTML = names.map(n => `<span class="name-item">${n}</span>`).join('');
          setStatus(`Patch ${P}: ${names.length} names selected`);
        })
        .catch(err => {
          btn.disabled = false;
          metaEl.innerHTML = `<span class="placeholder-text">Error: ${err.message}</span>`;
          setStatus(`Patch ${P}: selector failed`);
        });
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   15. EXPORT TXT (demo)
   ═══════════════════════════════════════════════════════════════════════════ */

function initExportTxt() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`export-txt-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P     = patch.toUpperCase();
      const names = state[`names${P}`];
      if (!names || !names.length) {
        setStatus(`Patch ${P}: no names to export — select names first`);
        return;
      }
      const blob = new Blob([names.join('\n') + '\n'], { type: 'text/plain' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `patch_${patch}_names.txt`;
      a.click();
      URL.revokeObjectURL(url);
      setStatus(`Patch ${P}: exported ${names.length} names`);
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   16. RENDER SCREEN — COMBINE TOGGLE
   ═══════════════════════════════════════════════════════════════════════════ */

function initRenderScreen() {
  const combineToggle = document.getElementById('render-combine');
  const styleSelect   = document.getElementById('render-style');
  const combinedCol   = document.getElementById('render-combined-col');

  combineToggle?.addEventListener('change', () => {
    combinedCol.style.display = combineToggle.checked ? '' : 'none';
    populateRender();
  });

  styleSelect?.addEventListener('change', populateRender);
}

function populateRender() {
  const style   = document.getElementById('render-style')?.value || 'title';
  const combine = document.getElementById('render-combine')?.checked || false;

  function applyStyle(name) {
    if (style === 'upper') return name.toUpperCase();
    if (style === 'lower') return name.toLowerCase();
    return name.charAt(0).toUpperCase() + name.slice(1);
  }

  ['a', 'b'].forEach(patch => {
    const P     = patch.toUpperCase();
    const names = state[`names${P}`];
    const el    = document.getElementById(`render-names-${patch}`);
    if (!el) return;
    if (!names || !names.length) {
      el.innerHTML = '<p class="placeholder-text">(Select names in the Walk screen first)</p>';
      return;
    }
    el.innerHTML = names.map(n => `<span class="render-name">${applyStyle(n)}</span>`).join('');
  });

  if (combine) {
    const el = document.getElementById('render-names-combined');
    if (!el) return;
    const A = state.namesA || [];
    const B = state.namesB || [];
    if (!A.length || !B.length) {
      el.innerHTML = '<p class="placeholder-text">(Select names for both patches first)</p>';
      return;
    }
    const combined = A.slice(0, Math.min(A.length, B.length))
      .map((a, i) => `${applyStyle(a)} ${applyStyle(B[i])}`);
    el.innerHTML = combined.map(n => `<span class="render-name">${n}</span>`).join('');
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   17. PACKAGE BUILD (API)
   ═══════════════════════════════════════════════════════════════════════════ */

function initPackageBuild() {
  const btn = document.getElementById('build-package');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const name    = document.getElementById('pkg-name').value || 'my-corpus-package';
    const version = document.getElementById('pkg-version').value || '0.1.0';
    const out     = document.getElementById('pkg-output');

    const body = {
      name,
      version,
      include_walks_a:    document.getElementById('pkg-walks-a')?.checked ?? true,
      include_walks_b:    document.getElementById('pkg-walks-b')?.checked ?? true,
      include_candidates: document.getElementById('pkg-candidates')?.checked ?? true,
      include_selections: document.getElementById('pkg-selections')?.checked ?? true,
    };

    out.innerHTML = '<span class="placeholder-text">Building package…</span>';
    btn.disabled = true;
    setStatus('Building package…');

    fetch('/api/walker/package', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(resp => {
        if (!resp.ok) {
          return resp.json().then(d => { throw new Error(d.error || 'Package build failed'); });
        }
        /* Trigger ZIP download */
        const filename = `${name}-${version}.zip`;
        return resp.blob().then(blob => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(url);

          /* Show contents summary */
          const kb = (blob.size / 1024).toFixed(1);
          const now = new Date().toISOString().slice(0, 19).replace('T', ' ');
          out.innerHTML = '';
          out.textContent = [
            `${filename}  (${kb} KB)`,
            ``,
            `built: ${now}`,
            `version: ${version}`,
          ].join('\n');
          setStatus(`Package "${filename}" downloaded`);
        });
      })
      .catch(err => {
        out.innerHTML = '';
        out.textContent = `Error: ${err.message}`;
        setStatus(`Package failed: ${err.message}`);
      })
      .finally(() => { btn.disabled = false; });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   18. ANALYSIS SCREEN POPULATION (API)
   ═══════════════════════════════════════════════════════════════════════════ */

function populateAnalysis() {
  ['a', 'b'].forEach(patch => {
    const P      = patch.toUpperCase();
    const corpus = state[`corpus${P}`];
    const hint   = document.getElementById(`analysis-hint-${patch}`);

    if (!corpus) {
      if (hint) hint.style.display = '';
      return;
    }
    if (hint) { hint.style.display = ''; hint.textContent = 'Loading analysis…'; }

    fetch(`/api/walker/analysis/${patch}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          if (hint) { hint.style.display = ''; hint.textContent = data.error; }
          return;
        }
        if (hint) hint.style.display = 'none';

        const d = data.analysis;

        /* Inventory */
        const setEl = (id, val) => {
          const el = document.getElementById(id);
          if (el) el.textContent = val;
        };
        setEl(`an-${patch}-total`,      d.total.toLocaleString());
        setEl(`an-${patch}-unique`,     d.unique.toLocaleString());
        setEl(`an-${patch}-hapax`,      d.hapax.toLocaleString());
        setEl(`an-${patch}-hapax-rate`, (d.hapax_rate * 100).toFixed(1) + '%');

        /* Length distribution */
        const lenKeys = ['2', '3', '4', '5+'];
        const lenIds  = ['2', '3', '4', '5'];
        lenKeys.forEach((k, i) => {
          const entry = d.length_distribution[k];
          if (entry) {
            setEl(`an-${patch}-len${lenIds[i]}-c`, entry[0].toLocaleString());
            setEl(`an-${patch}-len${lenIds[i]}-p`, entry[1].toFixed(1) + '%');
          }
        });

        /* Terrain */
        ['shape', 'craft', 'space'].forEach(axis => {
          const t = d.terrain[axis];
          if (!t) return;
          const sign = t.score >= 0 ? '+' : '';
          const barEl = document.getElementById(`an-${patch}-${axis}-bar`);
          if (barEl) barEl.style.width = `${t.pct}%`;
          const labelEl = document.getElementById(`an-${patch}-${axis}-label`);
          if (labelEl) labelEl.innerHTML = `${t.label} <span class="u-accent">${sign}${t.score.toFixed(3)}</span>`;
          const exEl = document.getElementById(`an-${patch}-${axis}-ex`);
          if (exEl && t.exemplars && t.exemplars.length) {
            exEl.textContent = t.exemplars.join(', ');
          }
        });
      })
      .catch(err => {
        if (hint) { hint.style.display = ''; hint.textContent = `Analysis error: ${err.message}`; }
      });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   19. PIPELINE CONFIGURE — RUN BUTTON ENABLE
   ═══════════════════════════════════════════════════════════════════════════ */

function checkPipelineReady() {
  const ready = !!(state.pipeSource && state.pipeOutput);
  const runBtn = document.getElementById('pipe-run-btn');
  if (runBtn) runBtn.disabled = !ready;
  if (ready) {
    document.getElementById('pipe-status-text').textContent =
      `Ready — ${state.pipeSource.split('/').pop()} → ${state.pipeOutput.split('/').pop()}`;
  }
}

function initPipelineConfigureRun() {
  document.getElementById('pipe-run-btn')?.addEventListener('click', () => {
    /* Switch to Monitor and start real pipeline run */
    switchTool('pipeline');
    navigateToScreen('pipeline-monitor');
    setTimeout(() => startPipelineRun(), 100);
  });

  document.getElementById('pipe-cancel-btn')?.addEventListener('click', cancelPipelineRun);
}


/* ═══════════════════════════════════════════════════════════════════════════
   20. PIPELINE MONITOR — REAL API POLLING
   ═══════════════════════════════════════════════════════════════════════════ */

let _pipelinePoller = null;
let _lastLogOffset = 0;

function syncMonitorFromConfig() {
  document.getElementById('monitor-job-source').textContent = state.pipeSource || '—';
  document.getElementById('monitor-job-output').textContent = state.pipeOutput || '—';
}

function initMonitorRun() {
  document.getElementById('monitor-run-btn')?.addEventListener('click', startPipelineRun);
  document.getElementById('monitor-cancel-btn')?.addEventListener('click', cancelPipelineRun);
}

function startPipelineRun() {
  if (state.pipeJobRunning) return;

  /* Read config from UI */
  const extractor = state.pipeExtractor || 'pyphen';
  const langEl = document.querySelector('.lang-option.is-selected input[type="radio"]');
  const language = langEl ? langEl.value : 'auto';

  if (!state.pipeSource) {
    setStatus('Pipeline: select a source directory first');
    return;
  }

  const logEl    = document.getElementById('monitor-log');
  const fillEl   = document.getElementById('monitor-progress-fill');
  const statusEl = document.getElementById('monitor-job-status');
  const stageEl  = document.getElementById('monitor-job-stage');
  const pctEl    = document.getElementById('monitor-job-pct');
  const badge    = document.getElementById('monitor-status-badge');
  const runBtn   = document.getElementById('monitor-run-btn');
  const cancelBtn = document.getElementById('monitor-cancel-btn');

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

  document.getElementById('monitor-job-source').textContent = state.pipeSource;
  document.getElementById('monitor-job-output').textContent = state.pipeOutput || '_working/output/';

  ['extract', 'normalize', 'annotate'].forEach(s => {
    const ind = document.getElementById(`stage-ind-${s}`);
    if (ind) ind.className = 'stage-indicator';
  });

  setStatus('Pipeline: starting…');
  document.getElementById('sb-pipe-job-status').textContent = 'starting';

  /* POST to start pipeline */
  fetch('/api/pipeline/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      extractor: extractor,
      language: language,
      source_path: state.pipeSource,
      output_dir: state.pipeOutput || null,
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
        setStatus(`Pipeline: ${data.error}`);
        return;
      }
      state.pipeJobRunning = true;
      _lastLogOffset = 0;
      startPipelinePolling();
    })
    .catch(err => {
      statusEl.textContent = 'error';
      runBtn.disabled = false;
      cancelBtn.disabled = true;
      setStatus(`Pipeline: ${err.message}`);
    });
}

function startPipelinePolling() {
  if (_pipelinePoller) clearInterval(_pipelinePoller);
  _pipelinePoller = setInterval(pollPipelineStatus, 500);
}

function pollPipelineStatus() {
  fetch('/api/pipeline/status')
    .then(r => r.json())
    .then(data => {
      const logEl    = document.getElementById('monitor-log');
      const fillEl   = document.getElementById('monitor-progress-fill');
      const statusEl = document.getElementById('monitor-job-status');
      const stageEl  = document.getElementById('monitor-job-stage');
      const pctEl    = document.getElementById('monitor-job-pct');
      const badge    = document.getElementById('monitor-status-badge');

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
      pctEl.textContent  = `${pct}%`;

      /* Update stage */
      if (data.current_stage) {
        stageEl.textContent = data.current_stage;
        updateStageIndicators(data.current_stage);
      }

      statusEl.textContent = data.status;
      document.getElementById('sb-pipe-job-status').textContent = data.status;

      /* Terminal states */
      if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
        state.pipeJobRunning = false;
        clearInterval(_pipelinePoller);
        _pipelinePoller = null;

        const runBtn    = document.getElementById('monitor-run-btn');
        const cancelBtn = document.getElementById('monitor-cancel-btn');
        runBtn.disabled = false;
        cancelBtn.disabled = true;

        if (data.status === 'completed') {
          statusEl.style.color = 'var(--col-ok)';
          badge.textContent = 'Completed';
          badge.className = 'badge is-done';
          setStatus('Pipeline: run complete');
        } else if (data.status === 'failed') {
          statusEl.style.color = 'var(--col-error, red)';
          badge.textContent = 'Failed';
          badge.className = 'badge is-error';
          setStatus(`Pipeline: failed — ${data.error_message || 'unknown error'}`);
        } else {
          statusEl.style.color = 'var(--col-text-muted)';
          badge.textContent = 'Cancelled';
          badge.className = 'badge badge--muted';
          setStatus('Pipeline: cancelled');
        }
      } else {
        statusEl.style.color = 'var(--col-warn)';
        badge.textContent = 'Running';
        badge.className = 'badge is-running';
        setStatus(`Pipeline: ${data.current_stage || 'running'}…`);
      }
    })
    .catch(() => { /* ignore polling errors */ });
}

function updateStageIndicators(currentStage) {
  const order = ['extract', 'normalize', 'annotate', 'database'];
  const idx   = order.indexOf(currentStage);

  order.forEach((s, i) => {
    const ind = document.getElementById(`stage-ind-${s}`);
    if (!ind) return;
    if (i < idx)        ind.className = 'stage-indicator is-done';
    else if (i === idx)  ind.className = 'stage-indicator is-running';
    /* leave future stages unchanged */
  });

  if (currentStage === 'complete') {
    order.forEach(s => {
      const ind = document.getElementById(`stage-ind-${s}`);
      if (ind) ind.className = 'stage-indicator is-done';
    });
  }
}

function setStageIndicator(stage, cls) {
  const ind = document.getElementById(`stage-ind-${stage}`);
  if (ind) ind.className = `stage-indicator ${cls}`;
}

function cancelPipelineRun() {
  if (!state.pipeJobRunning) return;

  fetch('/api/pipeline/cancel', { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      /* Polling will pick up the cancelled state */
    })
    .catch(() => { /* ignore */ });
}


/* ═══════════════════════════════════════════════════════════════════════════
   21. PIPELINE HISTORY — API
   ═══════════════════════════════════════════════════════════════════════════ */

function initHistorySelection() {
  loadHistoryRuns();
}

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
          ? `${ts.slice(0,4)}-${ts.slice(4,6)}-${ts.slice(6,8)} ${ts.slice(9,11)}:${ts.slice(11,13)}`
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

function populateHistoryDetail(run) {
  if (!run) return;

  const dirName = run.path.split('/').pop();
  const ts = run.timestamp || '';
  const dateStr = ts.length >= 13
    ? `${ts.slice(0,4)}-${ts.slice(4,6)}-${ts.slice(6,8)} ${ts.slice(9,11)}:${ts.slice(11,13)}:${ts.slice(13,15)}`
    : ts;

  document.getElementById('history-detail-name').textContent = dirName;
  document.getElementById('hd-status').textContent    = 'completed';
  document.getElementById('hd-started').textContent   = dateStr;
  document.getElementById('hd-duration').textContent  = '—';
  document.getElementById('hd-extractor').textContent = run.extractor_type;
  document.getElementById('hd-source').textContent    = '—';
  document.getElementById('hd-files').textContent     = '—';
  document.getElementById('hd-output').textContent    = run.path;
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


/* ═══════════════════════════════════════════════════════════════════════════
   22. STATUS BAR
   ═══════════════════════════════════════════════════════════════════════════ */

function setStatus(msg) {
  const el = document.getElementById('status-text');
  if (el) el.textContent = msg;
}

function populateBlended() {
  ['a', 'b'].forEach(patch => {
    const P   = patch.toUpperCase();
    const out = document.getElementById(`blended-${patch}-output`);
    if (!out) return;
    const walks = state[`walks${P}`];
    if (!walks || !walks.length) {
      out.innerHTML = '<p class="placeholder-text">(Generate walks in the Walk screen first)</p>';
      return;
    }
    out.innerHTML = walks.map(w => `<span class="walk-item">${w}</span>`).join('');
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   23. INIT
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initToolSwitcher();
  initTabNav();
  initSpinners();
  initSliders();
  initProfiles();
  initLangOptions();
  initRadioOptions();
  initSeedButtons();
  initCorpusModal();
  initDirModal();
  initGenerateWalks();
  initGenerateCandidates();
  initSelectNames();
  initExportTxt();
  initRenderScreen();
  initPackageBuild();
  initPipelineConfigureRun();
  initMonitorRun();
  initHistorySelection();

  /* Set initial screen */
  navigateToScreen('pipeline-configure');
  updateStatusBarContext('pipeline');

  /* Fetch initial walker stats from API */
  fetch('/api/walker/stats')
    .then(r => r.json())
    .then(data => {
      ['a', 'b'].forEach(patch => {
        const info = data[`patch_${patch}`];
        if (info && info.corpus) {
          document.getElementById(`status-corpus-${patch}`).textContent = info.corpus;
        }
      });
    })
    .catch(() => { /* ignore */ });

  setStatus('Ready');
});
