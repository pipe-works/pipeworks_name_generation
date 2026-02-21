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
   23. Parameter Info (3-Tier Progressive Disclosure)
   24. Init
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
  if (screenId === 'walker-render')   populateRender();
  if (screenId === 'walker-analysis') populateAnalysis();
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

/* Profile presets mirroring WALK_PROFILES from profiles.py */
const PROFILE_PRESETS = {
  clerical: { max_flips: 1, temperature: 0.3, frequency_weight: 1.0 },
  dialect:  { max_flips: 2, temperature: 0.7, frequency_weight: 0.0 },
  goblin:   { max_flips: 2, temperature: 1.5, frequency_weight: -0.5 },
  ritual:   { max_flips: 3, temperature: 2.5, frequency_weight: -1.0 },
};

function applyProfileToSliders(patch, profileName) {
  const preset = PROFILE_PRESETS[profileName];
  if (!preset) return;  /* custom — leave sliders as-is */

  /* Temperature slider */
  const tempEl = document.getElementById(`temperature-${patch}`);
  if (tempEl) {
    tempEl.value = preset.temperature;
    const tempVal = document.getElementById(`temperature-${patch}-val`);
    if (tempVal) tempVal.textContent = preset.temperature.toFixed(1);
  }

  /* Frequency weight slider */
  const freqEl = document.getElementById(`freq-weight-${patch}`);
  if (freqEl) {
    freqEl.value = preset.frequency_weight;
    const freqVal = document.getElementById(`freq-weight-${patch}-val`);
    if (freqVal) freqVal.textContent = preset.frequency_weight.toFixed(1);
  }

  /* Max flips spinner */
  const flipsEl = document.getElementById(`max-flips-${patch}`);
  if (flipsEl) {
    flipsEl.value = preset.max_flips;
  }
}

function initProfiles() {
  document.querySelectorAll('.profile-option').forEach(opt => {
    opt.addEventListener('click', () => {
      const patch = opt.dataset.patch;
      document.querySelectorAll(`.profile-option[data-patch="${patch}"]`)
        .forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;

      const profileName = opt.querySelector('input[type="radio"]').value;
      applyProfileToSliders(patch, profileName);
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
   10. CORPUS DROPDOWN SELECTORS (Walker)
   ═══════════════════════════════════════════════════════════════════════════
   One-step corpus loading: selecting a run from the <select> dropdown
   immediately loads the corpus into the corresponding patch — no modal,
   no extra confirmation click required.

   Each patch (A / B) has:
     - A <select> dropdown populated with discovered pipeline runs
     - A refresh button (⟳) to re-fetch the run list on demand
     - A status label showing load progress and walker readiness

   Auto-refresh: After a pipeline run completes, the dropdowns are
   automatically repopulated so the new corpus appears immediately.
   ═══════════════════════════════════════════════════════════════════════════ */

let _corpusRunsByPatch = { a: [], b: [] }; /* per-patch run lists from /api/pipeline/runs */
let _walkerReadyPollers = {};     /* { a: intervalId, b: intervalId } — per-patch polling timers */

/**
 * Initialise the one-step corpus dropdown selectors for Patch A and Patch B.
 *
 * Wires up:
 *   1. Initial fetch — populates both dropdowns on page load
 *   2. Change listeners — selecting a run triggers loadCorpus() immediately
 *   3. Refresh buttons — re-fetch the run list without reloading the page
 */
function initCorpusDropdowns() {
  /* ── 1. Populate dropdowns on page load ─────────────────────────────── */
  populateCorpusDropdowns();

  /* ── 2. Wire up change events for both patches ─────────────────────── */
  ['a', 'b'].forEach(patch => {
    const select = document.getElementById(`corpus-select-${patch}`);
    if (!select) return;

    /*
     * When the user picks a run from the dropdown, immediately load the
     * corpus into the patch.  The empty-string sentinel ("-- Select corpus --")
     * is ignored so re-selecting the placeholder is a no-op.
     */
    select.addEventListener('change', () => {
      const runId = select.value;
      if (!runId) return;                /* placeholder selected — nothing to do */

      /* Look up the full run object for metadata (syllable count, etc.) */
      const run = (_corpusRunsByPatch[patch] || []).find(r => r.path.split('/').pop() === runId);
      if (!run) return;

      loadCorpus(patch, runId, run);
    });

    /* ── 3. Refresh button ──────────────────────────────────────────── */
    const refreshBtn = document.getElementById(`corpus-refresh-${patch}`);
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => populateCorpusDropdowns());
    }
  });
}

/**
 * Fetch discovered runs from the API and populate both Patch A and Patch B
 * <select> dropdowns.
 *
 * If either dropdown already has a selected run that still exists in the
 * refreshed list, that selection is preserved so the user doesn't lose
 * context when the list refreshes (e.g. after a pipeline run completes).
 */
function populateCorpusDropdowns() {
  /* Fetch runs separately for each patch so per-patch corpus directories
   * (configured via INI) are respected.  The ?patch= query parameter
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
        if (!info) return;

        if (info.walker_ready) {
          clearInterval(_walkerReadyPollers[patch]);
          _walkerReadyPollers[patch] = null;
          const runId = state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          document.getElementById(`corpus-status-${patch}`).textContent =
            `${runId} · ${count} syllables · walker ready \u2713`;
          setStatus(`Patch ${P}: walker ready`);

          /* Update profile reach values once available in the stats response. */
          if (info.reaches) {
            updateReachValues(patch, info.reaches);
          }
        } else if (info.loading_stage) {
          /* Show loading stage progress while walker is building. */
          const runId = state[`corpus${P}`];
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          document.getElementById(`corpus-status-${patch}`).textContent =
            `${runId} \u00b7 ${count} syllables \u00b7 ${info.loading_stage}\u2026`;
          setStatus(`Patch ${P}: ${info.loading_stage}\u2026`);
        }
      })
      .catch(() => { /* ignore polling errors */ });
  }, 1000);
}


/* ═══════════════════════════════════════════════════════════════════════════
   10b. REACH DISPLAY — Profile Field Micro Signal
   ═══════════════════════════════════════════════════════════════════════════ */

/* Per-profile reach data cache for tooltips. Keyed by "a-dialect", "b-goblin", etc.
   Populated by updateReachValues() and read by the tooltip on hover. */
const _reachData = {};

/**
 * Update the reach value spans for a given patch with data from the stats API.
 *
 * For each profile in the reaches dict, finds the corresponding
 * ``reach-{patch}-{profile}`` span and sets its text content to
 * ``reach ≈N``. Also wires up the Level 2 tooltip (JS-positioned)
 * and the Level 3 info button that opens the modal.
 *
 * @param {string} patch - "a" or "b"
 * @param {Object} reaches - Dict mapping profile name to {reach, total, threshold, computation_ms}
 */
function updateReachValues(patch, reaches) {
  for (const [name, info] of Object.entries(reaches)) {
    const el = document.getElementById(`reach-${patch}-${name}`);
    if (!el) continue;

    /* Cache per-profile reach data for tooltip display. */
    _reachData[`${patch}-${name}`] = info;

    /* Level 1: inline micro signal — muted, monospace, right-aligned */
    el.textContent = `reach \u2248${info.reach.toLocaleString()}`;

    /* Level 2: tooltip on hover (JS-positioned floating panel).
       Only wire up once — check for marker attribute. */
    if (!el.dataset.reachWired) {
      el.dataset.reachWired = '1';
      el.addEventListener('mouseenter', () => showReachTooltip(el, `${patch}-${name}`));
      el.addEventListener('mouseleave', hideReachTooltip);
    }

    /* Level 3: info button to open the deep-dive modal */
    if (!el.querySelector('.reach-info-btn')) {
      const btn = document.createElement('span');
      btn.className = 'reach-info-btn';
      btn.textContent = '?';
      btn.setAttribute('aria-label', 'Traversal reach details');
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        openReachModal();
      });
      el.appendChild(btn);
    }
  }

  /* Update combine tab placeholder with a summary of all reaches. */
  updateCombineReachBar(patch, reaches);
}

/**
 * Show the reach tooltip anchored to the given element.
 *
 * Populates the shared ``#reach-tooltip`` element with the profile name,
 * a description, and a parameter grid (max_flips, temperature, etc.),
 * then positions it above the target element.
 *
 * @param {HTMLElement} anchor - The .profile-reach span being hovered
 * @param {string} key - Cache key like "a-dialect"
 */
function showReachTooltip(anchor, key) {
  const info = _reachData[key];
  if (!info) return;

  const tooltip = document.getElementById('reach-tooltip');
  const titleEl = document.getElementById('reach-tooltip-title');
  const bodyEl = document.getElementById('reach-tooltip-body');
  const paramsEl = document.getElementById('reach-tooltip-params');

  /* Extract profile name from the key ("a-dialect" → "dialect") */
  const profileName = key.split('-').slice(1).join('-');

  titleEl.textContent = `${profileName} profile`;
  bodyEl.textContent =
    'Mean effective vocabulary per step \u2014 the average number of ' +
    'syllables reachable from any starting position. Deterministic ' +
    'and seed-independent.';

  /* Parameter grid */
  paramsEl.innerHTML =
    `<dt>reach</dt><dd>\u2248${info.reach.toLocaleString()} / ${info.total.toLocaleString()}</dd>` +
    `<dt>threshold</dt><dd>${info.threshold}</dd>` +
    `<dt>computed in</dt><dd>${info.computation_ms.toFixed(0)} ms</dd>`;

  /* Position above the anchor element */
  const rect = anchor.getBoundingClientRect();
  tooltip.style.left = `${Math.max(8, rect.left - 160)}px`;
  tooltip.style.top = `${rect.top - 8}px`;
  tooltip.style.transform = 'translateY(-100%)';

  tooltip.classList.add('is-visible');
}

/** Hide the reach tooltip. */
function hideReachTooltip() {
  const tooltip = document.getElementById('reach-tooltip');
  tooltip.classList.remove('is-visible');
}

/* Cached per-patch reach summary lines for the combine bar.
   Both lines are displayed when both patches have data. */
const _combineReachLines = { a: null, b: null };

/**
 * Update the combine tab reach placeholder bar with a summary.
 *
 * Stores each patch's reach line and renders both when available:
 *   "Patch A — clerical ≈4 · dialect ≈32 · goblin ≈58 · ritual ≈147
 *    Patch B — clerical ≈100 · dialect ≈364 · goblin ≈370 · ritual ≈80"
 *
 * @param {string} patch - "a" or "b"
 * @param {Object} reaches - Dict mapping profile name to {reach, total}
 */
function updateCombineReachBar(patch, reaches) {
  const textEl = document.getElementById('combine-reach-text');
  if (!textEl) return;

  const P = patch.toUpperCase();
  const parts = Object.entries(reaches)
    .map(([name, info]) => `${name} \u2248${info.reach.toLocaleString()}`)
    .join(' \u00b7 ');

  _combineReachLines[patch] = `Patch ${P} \u2014 ${parts}`;

  /* Render all available patch lines. */
  const lines = [];
  if (_combineReachLines.a) lines.push(_combineReachLines.a);
  if (_combineReachLines.b) lines.push(_combineReachLines.b);
  textEl.textContent = lines.join('  \u2502  ');
}

/**
 * Open the reach deep-dive modal (Level 3).
 *
 * Follows the same open/close pattern as the directory browser modal.
 */
function openReachModal() {
  const modal = document.getElementById('reach-modal');
  if (modal) modal.classList.remove('hidden');
}

/** Initialise reach modal close handlers. */
function initReachModal() {
  const modal    = document.getElementById('reach-modal');
  const backdrop = document.getElementById('reach-modal-backdrop');
  const closeBtn = document.getElementById('reach-modal-close');

  if (!modal) return;

  /* Close via backdrop click or close button. */
  [backdrop, closeBtn].forEach(el => {
    el?.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  });

  /* Close on Escape key. */
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      modal.classList.add('hidden');
    }
  });
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
            setStatus(`Error: ${data.error}`);
            return;
          }
          setStatus(`Output base changed to ${data.output_base}`);
          /* Repopulate corpus dropdowns with runs from the new base */
          populateCorpusDropdowns();
        })
        .catch(err => setStatus(`Error: ${err.message}`));
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

  /* Close / Cancel / Backdrop — just hide the directory browser modal.
   * No special handling needed; the corpus dropdowns remain in place. */
  [closeBtn, cancelBtn, backdrop].forEach(el => {
    el?.addEventListener('click', () => {
      modal.classList.add('hidden');
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
      const temperature    = parseFloat(document.getElementById(`temperature-${patch}`)?.value) || 0.7;
      const frequencyWeight = parseFloat(document.getElementById(`freq-weight-${patch}`)?.value) || 0.0;
      const maxFlips       = parseInt(document.getElementById(`max-flips-${patch}`)?.value) || 2;

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

          const walkData = data.walks || [];
          const walks = walkData.map(w => w.formatted);
          state[`walks${P}`] = walks;
          state[`walkData${P}`] = walkData;

          out.innerHTML = renderWalksTable(walkData);
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
   12b. WALKS TABLE RENDERER
   ═══════════════════════════════════════════════════════════════════════════ */

function renderWalksTable(walkData) {
  if (!walkData || !walkData.length) return '';
  const rows = walkData.map((w, i) => {
    const sylCount = w.syllables ? w.syllables.length : 0;
    return `<tr><td>${i + 1}</td><td>${w.formatted}</td><td>${sylCount}</td></tr>`;
  }).join('');
  return `<table><thead><tr><th>#</th><th>Walk</th><th>Syl</th></tr></thead><tbody>${rows}</tbody></table>`;
}


/* ═══════════════════════════════════════════════════════════════════════════
   12c. WALKS EXPORT / COPY (TXT / MD)
   ═══════════════════════════════════════════════════════════════════════════ */

function walksToTxt(walks) {
  return walks.map((w, i) => `${i + 1}\t${w}`).join('\n') + '\n';
}

function walksToMd(walkData) {
  const header = '| # | Walk | Syl |\n| ---: | --- | ---: |';
  const rows = walkData.map((w, i) => {
    const sylCount = w.syllables ? w.syllables.length : 0;
    return `| ${i + 1} | ${w.formatted} | ${sylCount} |`;
  });
  return [header, ...rows].join('\n') + '\n';
}

function downloadBlob(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function initExportWalks() {
  ['a', 'b'].forEach(patch => {
    const P = patch.toUpperCase();

    /* Copy TXT to clipboard */
    document.getElementById(`copy-walks-txt-${patch}`)?.addEventListener('click', () => {
      const walks = state[`walks${P}`];
      if (!walks || !walks.length) {
        setStatus(`Patch ${P}: no walks to copy — generate walks first`);
        return;
      }
      navigator.clipboard.writeText(walksToTxt(walks)).then(() => {
        setStatus(`Patch ${P}: copied ${walks.length} walks as TXT`);
      });
    });

    /* Copy MD to clipboard */
    document.getElementById(`copy-walks-md-${patch}`)?.addEventListener('click', () => {
      const walkData = state[`walkData${P}`];
      if (!walkData || !walkData.length) {
        setStatus(`Patch ${P}: no walks to copy — generate walks first`);
        return;
      }
      navigator.clipboard.writeText(walksToMd(walkData)).then(() => {
        setStatus(`Patch ${P}: copied ${walkData.length} walks as Markdown`);
      });
    });

    /* Export TXT file */
    document.getElementById(`export-walks-txt-${patch}`)?.addEventListener('click', () => {
      const walks = state[`walks${P}`];
      if (!walks || !walks.length) {
        setStatus(`Patch ${P}: no walks to export — generate walks first`);
        return;
      }
      downloadBlob(walksToTxt(walks), `patch_${patch}_walks.txt`, 'text/plain');
      setStatus(`Patch ${P}: exported ${walks.length} walks as TXT`);
    });

    /* Export MD file */
    document.getElementById(`export-walks-md-${patch}`)?.addEventListener('click', () => {
      const walkData = state[`walkData${P}`];
      if (!walkData || !walkData.length) {
        setStatus(`Patch ${P}: no walks to export — generate walks first`);
        return;
      }
      downloadBlob(walksToMd(walkData), `patch_${patch}_walks.md`, 'text/markdown');
      setStatus(`Patch ${P}: exported ${walkData.length} walks as Markdown`);
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
      const syllsExact = parseInt(document.getElementById(`comb-syllables-${patch}`).value) || 2;
      const seedStr = document.getElementById(`comb-seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;
      const freqWeight = parseFloat(document.getElementById(`comb-freq-${patch}`)?.value) || 1.0;

      /* Read syllable mode: "exact" uses the spinner value, "all" generates 2-4 */
      const combMode = document.querySelector(`input[name="comb-mode-${patch}"]:checked`)?.value || 'exact';
      const sylls = combMode === 'all' ? [2, 3, 4] : syllsExact;

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
          frequency_weight: freqWeight,
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

          /* Store unique count so the selector can use it in "unique" count mode */
          state[`uniqueCandidates${P}`] = data.unique || 0;

          out.innerHTML = [
            `<span class="meta-key">generated  </span><span class="meta-val">${(data.generated || 0).toLocaleString()}</span>`,
            `<span class="meta-key">unique     </span><span class="meta-val">${(data.unique || 0).toLocaleString()}</span>`,
            `<span class="meta-key">duplicates </span><span class="meta-val">${(data.duplicates || 0).toLocaleString()}</span>`,
            `<span class="meta-key">syllables  </span><span class="meta-val">${Array.isArray(data.syllables) ? data.syllables.join(', ') : (data.syllables || sylls)}</span>`,
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
      const cls   = document.getElementById(`sel-class-${patch}`)?.value || 'first_name';
      const seedStr = document.getElementById(`sel-seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      /* Read radio selections */
      const countMode = document.querySelector(`input[name="sel-count-mode-${patch}"]:checked`)?.value || 'manual';
      const mode      = document.querySelector(`input[name="sel-mode-${patch}"]:checked`)?.value || 'hard';
      const order     = document.querySelector(`input[name="sel-order-${patch}"]:checked`)?.value || 'alphabetical';

      /* Resolve count: "unique" uses the unique candidate count from the
       * last combiner run; "manual" uses the spinner value. */
      let count;
      if (countMode === 'unique') {
        count = state[`uniqueCandidates${P}`] || parseInt(document.getElementById(`sel-count-${patch}`).value) || 100;
      } else {
        count = parseInt(document.getElementById(`sel-count-${patch}`).value) || 100;
      }

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
          mode: mode,
          order: order,
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
  document.getElementById('pipe-run-btn')?.addEventListener('click', startPipelineRun);
  document.getElementById('pipe-cancel-btn')?.addEventListener('click', cancelPipelineRun);
}


/* ═══════════════════════════════════════════════════════════════════════════
   20. PIPELINE MONITOR — REAL API POLLING
   ═══════════════════════════════════════════════════════════════════════════ */

let _pipelinePoller = null;
let _lastLogOffset = 0;

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
  const runBtn   = document.getElementById('pipe-run-btn');
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

        const runBtn    = document.getElementById('pipe-run-btn');
        const cancelBtn = document.getElementById('pipe-cancel-btn');
        runBtn.disabled = false;
        cancelBtn.disabled = true;

        if (data.status === 'completed') {
          statusEl.style.color = 'var(--col-ok)';
          badge.textContent = 'Completed';
          badge.className = 'badge is-done';
          setStatus('Pipeline: run complete');
          /* Auto-refresh corpus dropdowns so the new run appears immediately
           * in the Walker tab without requiring a manual refresh click. */
          populateCorpusDropdowns();
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



/* ═══════════════════════════════════════════════════════════════════════════
   23. PARAMETER INFO — 3-Tier Progressive Disclosure
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Static content for the 3-tier information layer on each walker parameter.
 *
 * Keyed by parameter ID prefix (e.g. "min-length" matches both
 * "min-length-a" and "min-length-b" in the DOM).
 *
 * Each entry contains:
 *   - signal:  Level 1 inline micro label (structural role)
 *   - tooltip: Level 2 one-sentence explanation
 *   - modal:   Level 3 deep-dive { title, rows: [[heading, html], ...] }
 *
 * Content source: _working/syllable_walker_three_tier_information_model.md
 */
const PARAM_INFO = {
  'min-length': {
    signal: 'min chars',
    tooltip: 'Minimum syllable length included in traversal. Filters input terrain before walking.',
    modal: {
      title: 'Min Length (chars)',
      rows: [
        ['Definition',
         'Minimum character length for syllables included in the active field.'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Removes shorter syllables from the graph.</li>' +
         '<li>Can reduce graph connectivity.</li>' +
         '<li>May increase compression and reduce drift.</li>' +
         '</ul>'],
        ['Interpretation',
         '<ul>' +
         '<li>Lower min length \u2192 more connective \u201cglue\u201d syllables.</li>' +
         '<li>Higher min length \u2192 more fragmented terrain.</li>' +
         '</ul>'],
        ['Not a Quality Control',
         'This does not improve syllable \u201cquality.\u201d It reshapes terrain topology.'],
      ],
    },
  },
  'max-length': {
    signal: 'max chars',
    tooltip: 'Maximum syllable length included in traversal. Trims longer structural units.',
    modal: {
      title: 'Max Length (chars)',
      rows: [
        ['Definition',
         'Upper bound on syllable character length for inclusion in the field.'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Removes long structural anchors.</li>' +
         '<li>Can reduce morphological stability.</li>' +
         '<li>May increase uniformity.</li>' +
         '</ul>'],
        ['Interpretation',
         '<ul>' +
         '<li>Lower max length \u2192 tighter rhythmic control.</li>' +
         '<li>Higher max length \u2192 broader morphological variation.</li>' +
         '</ul>'],
        ['Structural Role',
         'Acts as terrain pruning, not aesthetic tuning.'],
      ],
    },
  },
  'walk-steps': {
    signal: 'path depth',
    tooltip: 'Number of transitions per walk. Controls name length via traversal depth.',
    modal: {
      title: 'Walk Steps',
      rows: [
        ['Definition',
         'Number of graph transitions performed per generated walk.'],
        ['Effect on Behaviour',
         '<ul>' +
         '<li>Higher steps \u2192 longer constructions.</li>' +
         '<li>Increases cumulative drift.</li>' +
         '<li>Amplifies temperature effects.</li>' +
         '</ul>'],
        ['Not Influencing Reach',
         'Does not change traversal reach. Only affects how far within reach the walker travels.'],
      ],
    },
  },
  'max-flips': {
    signal: 'edge tolerance',
    tooltip: 'Maximum allowed feature deviations per transition.',
    modal: {
      title: 'Max Flips (per step)',
      rows: [
        ['Definition',
         'Maximum number of feature mismatches allowed between connected syllables.'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Higher flips increase structural connectivity.</li>' +
         '<li>Lower flips compress traversal field.</li>' +
         '<li>Strongly influences reach.</li>' +
         '</ul>'],
        ['Graph Impact',
         'Changes edge existence, not probability weighting.'],
        ['Interpretation',
         'Flips alter topology, not randomness.'],
      ],
    },
  },
  'temperature': {
    signal: 'entropy',
    tooltip: 'Controls probability distribution shape across neighbours. Higher values increase exploration.',
    modal: {
      title: 'Temperature',
      rows: [
        ['Definition',
         'Softmax scaling factor applied to neighbour transition probabilities.'],
        ['Effect on Behaviour',
         '<ul>' +
         '<li>Higher temperature \u2192 flatter probability distribution.</li>' +
         '<li>Lower temperature \u2192 sharper preference for high-similarity edges.</li>' +
         '</ul>'],
        ['Does Not Change Structural Connectivity',
         'Temperature reshapes probability mass, not graph edges.'],
        ['Thermodynamic Role',
         'Influences effective reach (probability thresholded), not pure graph reach.'],
      ],
    },
  },
  'freq-weight': {
    signal: 'rarity bias',
    tooltip: 'Biases transition probability by syllable frequency. Positive favours common, negative favours rare.',
    modal: {
      title: 'Frequency Weight (bias)',
      rows: [
        ['Definition',
         'Bias applied to syllable frequency distribution.'],
        ['Effect on Behaviour',
         '<ul>' +
         '<li>Positive \u2192 favours common syllables.</li>' +
         '<li>Negative \u2192 favours rare syllables.</li>' +
         '</ul>'],
        ['When Hapax Rate = 100%',
         'Frequency weighting has minimal effect.'],
        ['Structural Role',
         'Alters probability weighting, not graph connectivity.'],
      ],
    },
  },
  'neighbors': {
    signal: 'branch cap',
    tooltip: 'Maximum number of adjacent syllables considered at each step.',
    modal: {
      title: 'Neighbors (max)',
      rows: [
        ['Definition',
         'Caps the number of outgoing edges evaluated per node.'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Lower cap reduces traversal branching.</li>' +
         '<li>Can significantly reduce reach.</li>' +
         '<li>Alters effective topology under constraint.</li>' +
         '</ul>'],
        ['Interpretation',
         'Acts as local pruning of the adjacency graph.'],
      ],
    },
  },
  'seed': {
    signal: 'rng seed',
    tooltip: 'Controls reproducibility of stochastic transitions.',
    modal: {
      title: 'Seed',
      rows: [
        ['Definition',
         'Initial value for pseudo-random number generator.'],
        ['Effect',
         '<ul>' +
         '<li>Same seed + same parameters \u2192 identical walks.</li>' +
         '<li>Does not influence reach calculation.</li>' +
         '<li>Does not alter structural field.</li>' +
         '</ul>'],
        ['Philosophical Note',
         'Seed enables determinism within stochastic systems.'],
      ],
    },
  },
  'walk-count': {
    signal: 'sample size',
    tooltip: 'Number of walks generated in this batch.',
    modal: {
      title: 'Walk Count',
      rows: [
        ['Definition',
         'Number of independent traversal executions.'],
        ['Effect',
         '<ul>' +
         '<li>Does not alter reach.</li>' +
         '<li>Does not alter topology.</li>' +
         '<li>Increases empirical coverage.</li>' +
         '</ul>'],
        ['Interpretation',
         'Sample size influences observed diversity, not structural possibility.'],
      ],
    },
  },
};

/**
 * Show the parameter tooltip anchored to the given element.
 *
 * Populates the shared ``#param-tooltip`` element with the parameter
 * title and a one-sentence tooltip, then positions it above the anchor.
 *
 * @param {HTMLElement} anchor - The element being hovered
 * @param {string} key - Parameter key (e.g. "min-length")
 */
function showParamTooltip(anchor, key) {
  const info = PARAM_INFO[key];
  if (!info) return;

  const tooltip = document.getElementById('param-tooltip');
  const titleEl = document.getElementById('param-tooltip-title');
  const bodyEl  = document.getElementById('param-tooltip-body');

  titleEl.textContent = info.modal.title;
  bodyEl.textContent  = info.tooltip;

  /* Position above the anchor element. */
  const rect = anchor.getBoundingClientRect();
  tooltip.style.left = `${Math.max(8, rect.left)}px`;
  tooltip.style.top  = `${rect.top - 8}px`;
  tooltip.style.transform = 'translateY(-100%)';

  tooltip.classList.add('is-visible');
}

/** Hide the parameter tooltip. */
function hideParamTooltip() {
  const tooltip = document.getElementById('param-tooltip');
  tooltip.classList.remove('is-visible');
}

/**
 * Open the parameter deep-dive modal with content for the given key.
 *
 * Dynamically populates ``#param-modal-tbody`` with rows from
 * ``PARAM_INFO[key].modal.rows``.
 *
 * @param {string} key - Parameter key (e.g. "temperature")
 */
function openParamModal(key) {
  const info = PARAM_INFO[key];
  if (!info) return;

  const modal   = document.getElementById('param-modal');
  const titleEl = document.getElementById('param-modal-title');
  const tbody   = document.getElementById('param-modal-tbody');

  titleEl.textContent = info.modal.title;

  /* Build table rows from the modal data. */
  tbody.innerHTML = info.modal.rows.map(([heading, content]) =>
    `<tr><th>${heading}</th><td>${content}</td></tr>`
  ).join('');

  modal.classList.remove('hidden');
}

/**
 * Initialise the parameter info 3-tier progressive disclosure system.
 *
 * Wires up:
 *   1. Tooltip hover on .param-signal and .control-label elements (Level 2)
 *   2. Click on .param-info-btn elements to open modal (Level 3)
 *   3. Modal close handlers (backdrop, close button, Escape key)
 */
function initParamInfo() {
  /* ── Level 2: Tooltip on hover of signal spans ── */
  document.querySelectorAll('.param-signal').forEach(el => {
    const key = el.dataset.param;
    if (!key || !PARAM_INFO[key]) return;

    el.style.cursor = 'help';
    el.addEventListener('mouseenter', () => showParamTooltip(el, key));
    el.addEventListener('mouseleave', hideParamTooltip);
  });

  /* Also wire tooltips on the control-label text inside .control-label-row
     wrappers, so hovering the label name shows the tooltip too. */
  document.querySelectorAll('.control-label-row .control-label').forEach(label => {
    const row = label.closest('.control-label-row');
    const signal = row?.querySelector('.param-signal');
    if (!signal) return;
    const key = signal.dataset.param;
    if (!key || !PARAM_INFO[key]) return;

    label.style.cursor = 'help';
    label.addEventListener('mouseenter', () => showParamTooltip(label, key));
    label.addEventListener('mouseleave', hideParamTooltip);
  });

  /* For slider headers (Temperature, Freq Weight), the label lives inside
     .slider-control__header alongside a sibling .param-signal. Wire tooltip
     on the label there too. */
  document.querySelectorAll('.slider-control__header .param-signal').forEach(signal => {
    const key = signal.dataset.param;
    if (!key || !PARAM_INFO[key]) return;

    const header = signal.closest('.slider-control__header');
    const label  = header?.querySelector('.control-label');
    if (!label) return;

    label.style.cursor = 'help';
    label.addEventListener('mouseenter', () => showParamTooltip(label, key));
    label.addEventListener('mouseleave', hideParamTooltip);
  });

  /* ── Level 3: Info button click opens modal ── */
  document.querySelectorAll('.param-info-btn').forEach(btn => {
    const key = btn.dataset.param;
    if (!key || !PARAM_INFO[key]) return;

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      openParamModal(key);
    });
  });

  /* ── Modal close handlers ── */
  const modal    = document.getElementById('param-modal');
  const backdrop = document.getElementById('param-modal-backdrop');
  const closeBtn = document.getElementById('param-modal-close');

  if (modal) {
    [backdrop, closeBtn].forEach(el => {
      el?.addEventListener('click', () => modal.classList.add('hidden'));
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        modal.classList.add('hidden');
      }
    });
  }

  /* ── Structural Summary modal ── */
  const summaryModal    = document.getElementById('summary-modal');
  const summaryBackdrop = document.getElementById('summary-modal-backdrop');
  const summaryClose    = document.getElementById('summary-modal-close');

  document.querySelectorAll('.summary-info-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (summaryModal) summaryModal.classList.remove('hidden');
    });
  });

  if (summaryModal) {
    [summaryBackdrop, summaryClose].forEach(el => {
      el?.addEventListener('click', () => summaryModal.classList.add('hidden'));
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !summaryModal.classList.contains('hidden')) {
        summaryModal.classList.add('hidden');
      }
    });
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   24. INIT
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
  initCorpusDropdowns();
  initDirModal();
  initReachModal();
  initParamInfo();
  initGenerateWalks();
  initExportWalks();
  initGenerateCandidates();
  initSelectNames();
  initExportTxt();
  initRenderScreen();
  initPackageBuild();
  initPipelineConfigureRun();
  initHistorySelection();

  /* Set initial screen */
  navigateToScreen('pipeline-configure');
  updateStatusBarContext('pipeline');

  /* Populate header version from the package's __version__. */
  fetch('/api/version')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('app-version');
      if (el && data.version) {
        el.textContent = `build tools \u00b7 v${data.version}`;
      }
    })
    .catch(() => { /* keep fallback text */ });

  /* Fetch initial walker stats from API.
     If the server already has a walker ready (e.g. after a page refresh),
     we need to populate the corpus status, reach values, and combine bar
     immediately rather than waiting for a new corpus load to trigger
     pollWalkerReady(). */
  fetch('/api/walker/stats')
    .then(r => r.json())
    .then(data => {
      ['a', 'b'].forEach(patch => {
        const P = patch.toUpperCase();
        const info = data[`patch_${patch}`];
        if (!info || !info.corpus) return;

        document.getElementById(`status-corpus-${patch}`).textContent = info.corpus;

        /* If the walker is already ready, update the full status line
           and populate reach values (same logic as pollWalkerReady). */
        if (info.walker_ready) {
          const count = info.syllable_count
            ? info.syllable_count.toLocaleString() : '?';
          const statusEl = document.getElementById(`corpus-status-${patch}`);
          if (statusEl) {
            statusEl.textContent =
              `${info.corpus} \u00b7 ${count} syllables \u00b7 walker ready \u2713`;
          }
          if (info.reaches) {
            updateReachValues(patch, info.reaches);
          }
        }
      });
    })
    .catch(() => { /* ignore */ });

  setStatus('Ready');
});
