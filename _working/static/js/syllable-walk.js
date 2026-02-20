/*
   syllable-walk.js
   ─────────────────────────────────────────────────────────────────────────
   Pseudo-interactive demo script for Pipe-Works Build Tools web UI.
   No backend wiring — all state is local, all outputs are simulated.

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
   10. Corpus Browser Modal (Walker)
   11. Directory Browser Modal (Pipeline)
   12. Generate Walks (demo)
   13. Generate Candidates (demo)
   14. Select Names (demo)
   15. Export TXT (demo)
   16. Render Screen — Combine Toggle
   17. Package Build (demo)
   18. Analysis Screen Population
   19. Pipeline Configure — Run Button Enable
   20. Pipeline Monitor — Demo Run Simulation
   21. Pipeline History — Run Selection
   22. Status Bar
   23. Init
   ═══════════════════════════════════════════════════════════════════════════ */

'use strict';

/* ─────────────────────────────────────────────────────────────────────────
   Shared demo data
   ───────────────────────────────────────────────────────────────────────── */

const DEMO_WALKS = {
  A: [
    'ma·lo·ren·di·vel',
    'si·na·tho·kel',
    'bra·ven·do·lis·ta·ren',
    'or·mi·vel',
    'ta·kel·si·ven·dra',
    'lo·ma·ris',
    'ven·dra·sol·ith',
  ],
  B: [
    'krask·thrix·vorn',
    'grul·brak·sketh·orn',
    'thrax·veld·krix',
    'skorn·brul·thex·vrak',
    'grix·threld·vorn·skath',
    'brak·krix·theld',
    'vorn·skrul·thrax·beld',
  ],
};

const DEMO_NAMES = {
  A: [
    'maloren', 'sinatho', 'bravendol', 'ormivel', 'takelsi',
    'lomarist', 'vendrasol', 'malovel', 'sinathor', 'bravendo',
    'ormis', 'takelven', 'lomaren', 'vendrath', 'malosith',
  ],
  B: [
    'kraskthrix', 'grulbrak', 'thraxveld', 'skornbrul', 'grixtheld',
    'brakorn', 'vornthex', 'skrulvrak', 'thraxxeld', 'grulskorn',
    'krixbrak', 'vorntheld', 'skathgrix', 'brakthrix', 'thraxvorn',
  ],
};

const CORPUS_META = {
  fantasy_names:   { syllables: 1240, walks: 3 },
  nordic_roots:    { syllables: 892,  walks: 2 },
  latin_fragments: { syllables: 2105, walks: 5 },
  goblin_tongue:   { syllables: 567,  walks: 1 },
};

/* Demo analysis data per corpus */
const CORPUS_ANALYSIS = {
  fantasy_names: {
    total: 1240, unique: 847, hapax: 312, hapaxRate: 0.252,
    len: { 2: [186, 15.0], 3: [558, 45.0], 4: [372, 30.0], '5+': [124, 10.0] },
    terrain: {
      shape: { val: 0.08,  label: 'NEUTRAL', pct: 55, ex: ['melo', 'sira', 'vendra', 'lorist'] },
      craft: { val: -0.04, label: 'NEUTRAL', pct: 46, ex: ['thal', 'ven', 'bravendol', 'ormis'] },
      space: { val: 0.21,  label: 'OPEN',    pct: 62, ex: ['ma', 'lo', 'si', 'ven'] },
    },
  },
  nordic_roots: {
    total: 892, unique: 601, hapax: 198, hapaxRate: 0.222,
    len: { 2: [89, 10.0], 3: [312, 35.0], 4: [357, 40.0], '5+': [134, 15.0] },
    terrain: {
      shape: { val: 0.42,  label: 'JAGGED',  pct: 72, ex: ['skr', 'thrix', 'vorn', 'krix'] },
      craft: { val: 0.35,  label: 'WORKED',  pct: 68, ex: ['thrix', 'skorn', 'brak', 'veld'] },
      space: { val: -0.18, label: 'DENSE',   pct: 38, ex: ['skr', 'thrix', 'krix', 'vrak'] },
    },
  },
  latin_fragments: {
    total: 2105, unique: 1342, hapax: 487, hapaxRate: 0.231,
    len: { 2: [421, 20.0], 3: [842, 40.0], 4: [631, 30.0], '5+': [211, 10.0] },
    terrain: {
      shape: { val: -0.15, label: 'ROUND',   pct: 42, ex: ['us', 'um', 'ia', 'ae'] },
      craft: { val: -0.22, label: 'FLOWING',  pct: 39, ex: ['us', 'ia', 'um', 'or'] },
      space: { val: 0.08,  label: 'NEUTRAL',  pct: 52, ex: ['tion', 'us', 'ia', 'um'] },
    },
  },
  goblin_tongue: {
    total: 567, unique: 312, hapax: 89, hapaxRate: 0.157,
    len: { 2: [113, 20.0], 3: [198, 35.0], 4: [170, 30.0], '5+': [86, 15.0] },
    terrain: {
      shape: { val: 0.61,  label: 'JAGGED',  pct: 81, ex: ['grk', 'skrz', 'vrkh', 'bzt'] },
      craft: { val: 0.55,  label: 'WORKED',  pct: 78, ex: ['grk', 'skrz', 'bzt', 'khrn'] },
      space: { val: -0.32, label: 'DENSE',   pct: 32, ex: ['grk', 'skrz', 'vrkh', 'bzt'] },
    },
  },
};

/* Pipeline demo log lines */
const PIPELINE_LOG_LINES = [
  { cls: 'log-line--info',   text: '[pipeline] starting run…' },
  { cls: 'log-line--info',   text: '[config]   extractor: pyphen · language: en_US' },
  { cls: 'log-line--info',   text: '[config]   stages: extract → normalize → annotate' },
  { cls: 'log-line--accent', text: '[extract]  scanning source directory…' },
  { cls: 'log-line--info',   text: '[extract]  found 12 .txt files' },
  { cls: 'log-line--info',   text: '[extract]  processing file 1/12: names_01.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 2/12: names_02.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 3/12: names_03.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 4/12: names_04.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 5/12: names_05.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 6/12: names_06.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 7/12: names_07.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 8/12: names_08.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 9/12: names_09.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 10/12: names_10.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 11/12: names_11.txt' },
  { cls: 'log-line--info',   text: '[extract]  processing file 12/12: names_12.txt' },
  { cls: 'log-line--ok',     text: '[extract]  complete — 1,240 syllables extracted' },
  { cls: 'log-line--accent', text: '[normalize] deduplicating and cleaning…' },
  { cls: 'log-line--info',   text: '[normalize] removed 393 duplicates' },
  { cls: 'log-line--ok',     text: '[normalize] complete — 847 unique syllables' },
  { cls: 'log-line--accent', text: '[annotate]  computing phonetic features…' },
  { cls: 'log-line--info',   text: '[annotate]  shape axis: round ↔ jagged' },
  { cls: 'log-line--info',   text: '[annotate]  craft axis: flowing ↔ worked' },
  { cls: 'log-line--info',   text: '[annotate]  space axis: open ↔ dense' },
  { cls: 'log-line--ok',     text: '[annotate]  complete — 847 syllables annotated' },
  { cls: 'log-line--ok',     text: '[pipeline]  run complete ✓' },
  { cls: 'log-line--info',   text: '[output]    corpus.syllables  1,240 entries' },
  { cls: 'log-line--info',   text: '[output]    corpus.normalized 847 unique' },
  { cls: 'log-line--info',   text: '[output]    corpus.annotated  847 annotated' },
  { cls: 'log-line--info',   text: '[output]    corpus.meta       run metadata' },
  { cls: 'log-line--info',   text: '[output]    corpus.db         SQLite index' },
];

/* History run detail data */
const HISTORY_RUNS = {
  'run-001': {
    name: 'fantasy_corpus_v1',
    status: 'completed',
    started: '2026-02-20 09:14:03',
    duration: '4m 22s',
    extractor: 'pyphen · en_US',
    source: '~/projects/fantasy_corpus/raw/',
    files: '12 .txt files',
    output: '_working/output/run_20260220_091403/',
    syllables: '1,240 extracted · 847 unique',
    stages: ['done', 'done', 'done'],
    stageTime: ['1m 14s', '0m 48s', '2m 20s'],
    tree: `run_20260220_091403/
├── corpus.syllables        1,240 entries
├── corpus.normalized       847 unique
├── corpus.annotated        847 annotated
├── corpus.meta             run metadata
└── corpus.db               SQLite index`,
  },
  'run-002': {
    name: 'nordic_source_raw',
    status: 'completed',
    started: '2026-02-19 16:42:11',
    duration: '2m 58s',
    extractor: 'pyphen · de_DE',
    source: '~/projects/nordic_source/',
    files: '8 .txt files',
    output: '_working/output/run_20260219_164211/',
    syllables: '892 extracted · 601 unique',
    stages: ['done', 'done', 'done'],
    stageTime: ['0m 52s', '0m 31s', '1m 35s'],
    tree: `run_20260219_164211/
├── corpus.syllables        892 entries
├── corpus.normalized       601 unique
├── corpus.annotated        601 annotated
├── corpus.meta             run metadata
└── corpus.db               SQLite index`,
  },
  'run-003': {
    name: 'latin_fragments_test',
    status: 'failed',
    started: '2026-02-19 11:05:44',
    duration: '0m 47s',
    extractor: 'pyphen · auto',
    source: '~/projects/latin_fragments/src/',
    files: '31 .txt files',
    output: '—',
    syllables: '—',
    stages: ['done', 'error', 'skip'],
    stageTime: ['0m 32s', 'failed', '—'],
    tree: `run_20260219_110544/
├── corpus.syllables        2,105 entries (partial)
└── error.log               UnicodeDecodeError: 'utf-8' codec…`,
  },
  'run-004': {
    name: 'goblin_dialect_raw',
    status: 'completed',
    started: '2026-02-18 14:30:22',
    duration: '1m 12s',
    extractor: 'pyphen · en_US',
    source: '~/projects/goblin_dialect/raw/',
    files: '5 .txt files',
    output: '_working/output/run_20260218_143022/',
    syllables: '567 extracted · 312 unique',
    stages: ['done', 'done', 'done'],
    stageTime: ['0m 18s', '0m 12s', '0m 42s'],
    tree: `run_20260218_143022/
├── corpus.syllables        567 entries
├── corpus.normalized       312 unique
├── corpus.annotated        312 annotated
├── corpus.meta             run metadata
└── corpus.db               SQLite index`,
  },
  'run-005': {
    name: 'elvish_source_v2',
    status: 'cancelled',
    started: '2026-02-17 10:18:05',
    duration: '0m 23s',
    extractor: 'nltk',
    source: '~/projects/elvish_source/v2/',
    files: '19 .txt files',
    output: '—',
    syllables: '—',
    stages: ['running', 'skip', 'skip'],
    stageTime: ['cancelled', '—', '—'],
    tree: `run_20260217_101805/
└── (cancelled — no output written)`,
  },
};

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

function initCorpusModal() {
  const modal     = document.getElementById('corpus-modal');
  const backdrop  = document.getElementById('corpus-modal-backdrop');
  const closeBtn  = document.getElementById('corpus-modal-close');
  const cancelBtn = document.getElementById('corpus-modal-cancel');
  const selectBtn = document.getElementById('corpus-modal-select');
  const items     = modal.querySelectorAll('.corpus-browser__item');

  /* Open */
  ['select-corpus-a', 'select-corpus-b'].forEach(id => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener('click', () => {
      _corpusModalPatch = id.endsWith('-a') ? 'a' : 'b';
      items.forEach(i => i.classList.remove('is-selected'));
      selectBtn.disabled = true;
      modal.classList.remove('hidden');
    });
  });

  /* Item selection */
  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('is-selected'));
      item.classList.add('is-selected');
      selectBtn.disabled = false;
    });
  });

  /* Confirm */
  selectBtn.addEventListener('click', () => {
    const selected = modal.querySelector('.corpus-browser__item.is-selected');
    if (!selected) return;
    const corpus = selected.dataset.corpus;
    const meta   = CORPUS_META[corpus];
    const label  = `${corpus}/ · ${meta.syllables.toLocaleString()} syllables`;

    if (_corpusModalPatch === 'a') {
      state.corpusA = corpus;
      document.getElementById('corpus-status-a').textContent = label;
      document.getElementById('corpus-status-a').classList.add('is-loaded');
      document.getElementById('status-corpus-a').textContent = corpus;
    } else {
      state.corpusB = corpus;
      document.getElementById('corpus-status-b').textContent = label;
      document.getElementById('corpus-status-b').classList.add('is-loaded');
      document.getElementById('status-corpus-b').textContent = corpus;
    }

    setStatus(`Corpus loaded: ${corpus}`);
    modal.classList.add('hidden');
  });

  /* Close */
  [closeBtn, cancelBtn, backdrop].forEach(el => {
    el?.addEventListener('click', () => modal.classList.add('hidden'));
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   11. DIRECTORY BROWSER MODAL (Pipeline)
   ═══════════════════════════════════════════════════════════════════════════ */

let _dirModalTarget = 'source';

function initDirModal() {
  const modal     = document.getElementById('dir-modal');
  const backdrop  = document.getElementById('dir-modal-backdrop');
  const closeBtn  = document.getElementById('dir-modal-close');
  const cancelBtn = document.getElementById('dir-modal-cancel');
  const selectBtn = document.getElementById('dir-modal-select');
  const items     = modal.querySelectorAll('.corpus-browser__item');

  function openModal(target) {
    _dirModalTarget = target;
    const titleEl = document.getElementById('dir-modal-title');
    titleEl.textContent = target === 'source' ? 'Select Source Directory' : 'Select Output Directory';
    items.forEach(i => i.classList.remove('is-selected'));
    selectBtn.disabled = true;
    modal.classList.remove('hidden');
  }

  document.getElementById('pipe-browse-source')?.addEventListener('click', () => openModal('source'));
  document.getElementById('pipe-browse-output')?.addEventListener('click', () => openModal('output'));
  document.getElementById('pipe-select-files')?.addEventListener('click',  () => openModal('source'));

  items.forEach(item => {
    item.addEventListener('click', () => {
      items.forEach(i => i.classList.remove('is-selected'));
      item.classList.add('is-selected');
      selectBtn.disabled = false;
    });
  });

  selectBtn.addEventListener('click', () => {
    const selected = modal.querySelector('.corpus-browser__item.is-selected');
    if (!selected) return;
    const dir = selected.dataset.dir;

    if (_dirModalTarget === 'source') {
      state.pipeSource = dir;
      const el = document.getElementById('pipe-source-path');
      el.textContent = dir;
      el.classList.add('is-set');
      document.getElementById('sb-pipe-source').textContent = dir.split('/').pop() || dir;
    } else {
      state.pipeOutput = dir;
      const el = document.getElementById('pipe-output-path');
      el.textContent = dir;
      el.classList.add('is-set');
    }

    checkPipelineReady();
    modal.classList.add('hidden');
  });

  [closeBtn, cancelBtn, backdrop].forEach(el => {
    el?.addEventListener('click', () => modal.classList.add('hidden'));
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   12. GENERATE WALKS (demo)
   ═══════════════════════════════════════════════════════════════════════════ */

function initGenerateWalks() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      const count = parseInt(document.getElementById(`walk-count-${patch}`).value) || 2;
      const walks = DEMO_WALKS[P].slice(0, Math.min(count, DEMO_WALKS[P].length));
      state[`walks${P}`] = walks;

      const out = document.getElementById(`walks-output-${patch}`);
      out.innerHTML = walks.map(w => `<span class="walk-item">${w}</span>`).join('');
      setStatus(`Patch ${P}: ${walks.length} walk${walks.length !== 1 ? 's' : ''} generated`);
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   13. GENERATE CANDIDATES (demo)
   ═══════════════════════════════════════════════════════════════════════════ */

function initGenerateCandidates() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-candidates-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      const count  = parseInt(document.getElementById(`comb-count-${patch}`).value) || 10000;
      const sylls  = parseInt(document.getElementById(`comb-syllables-${patch}`).value) || 2;
      const unique = Math.floor(count * 0.82);
      const dupes  = count - unique;

      const out = document.getElementById(`comb-output-${patch}`);
      out.innerHTML = [
        `<span class="meta-key">generated  </span><span class="meta-val">${count.toLocaleString()}</span>`,
        `<span class="meta-key">unique     </span><span class="meta-val">${unique.toLocaleString()}</span>`,
        `<span class="meta-key">duplicates </span><span class="meta-val">${dupes.toLocaleString()}</span>`,
        `<span class="meta-key">syllables  </span><span class="meta-val">${sylls}</span>`,
        `<span class="meta-key">source     </span><span class="meta-path">${state[`corpus${P}`] || 'no corpus'}</span>`,
      ].join('<br/>');

      setStatus(`Patch ${P}: ${unique.toLocaleString()} unique candidates generated`);
    });
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   14. SELECT NAMES (demo)
   ═══════════════════════════════════════════════════════════════════════════ */

function initSelectNames() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`select-names-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P     = patch.toUpperCase();
      const count = parseInt(document.getElementById(`sel-count-${patch}`).value) || 100;
      const cls   = document.getElementById(`sel-class-${patch}`).value;
      const names = DEMO_NAMES[P].slice(0, Math.min(15, DEMO_NAMES[P].length));
      state[`names${P}`] = names;

      const metaEl = document.querySelector(`#sel-output-${patch} .selector-output__meta`);
      metaEl.innerHTML = [
        `<span class="meta-key">selected   </span><span class="meta-val">${names.length}</span>`,
        `<span class="meta-key">requested  </span><span class="meta-val">${count}</span>`,
        `<span class="meta-key">class      </span><span class="meta-val">${cls}</span>`,
        `<span class="meta-key">patch      </span><span class="meta-path">${P}</span>`,
      ].join('<br/>');

      const listEl = document.getElementById(`sel-names-${patch}`);
      listEl.innerHTML = names.map(n => `<span class="name-item">${n}</span>`).join('');

      setStatus(`Patch ${P}: ${names.length} names selected`);
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
   17. PACKAGE BUILD (demo)
   ═══════════════════════════════════════════════════════════════════════════ */

function initPackageBuild() {
  const btn = document.getElementById('build-package');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const name    = document.getElementById('pkg-name').value || 'my-corpus-package';
    const version = document.getElementById('pkg-version').value || '0.1.0';
    const out     = document.getElementById('pkg-output');

    const now = new Date().toISOString().slice(0, 19).replace('T', ' ');
    out.innerHTML = '';
    out.textContent = [
      `${name}-${version}/`,
      `├── patch_a/`,
      `│   ├── walks.json           ${state.walksA.length} walks`,
      `│   ├── candidates.json      ${state.namesA.length ? '10,000 entries' : '(not generated)'}`,
      `│   └── selections.txt       ${state.namesA.length} names`,
      `├── patch_b/`,
      `│   ├── walks.json           ${state.walksB.length} walks`,
      `│   ├── candidates.json      ${state.namesB.length ? '10,000 entries' : '(not generated)'}`,
      `│   └── selections.txt       ${state.namesB.length} names`,
      `├── manifest.json`,
      `└── README.md`,
      ``,
      `built: ${now}`,
      `version: ${version}`,
    ].join('\n');

    setStatus(`Package "${name}-${version}" built`);
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   18. ANALYSIS SCREEN POPULATION
   ═══════════════════════════════════════════════════════════════════════════ */

function populateAnalysis() {
  ['a', 'b'].forEach(patch => {
    const P      = patch.toUpperCase();
    const corpus = state[`corpus${patch}`];
    const hint   = document.getElementById(`analysis-hint-${patch}`);

    if (!corpus || !CORPUS_ANALYSIS[corpus]) {
      if (hint) hint.style.display = '';
      return;
    }
    if (hint) hint.style.display = 'none';

    const d = CORPUS_ANALYSIS[corpus];

    /* Inventory */
    document.getElementById(`an-${patch}-total`).textContent      = d.total.toLocaleString();
    document.getElementById(`an-${patch}-unique`).textContent     = d.unique.toLocaleString();
    document.getElementById(`an-${patch}-hapax`).textContent      = d.hapax.toLocaleString();
    document.getElementById(`an-${patch}-hapax-rate`).textContent = (d.hapaxRate * 100).toFixed(1) + '%';

    /* Length distribution */
    const lenKeys = ['2', '3', '4', '5+'];
    const lenIds  = ['2', '3', '4', '5'];
    lenKeys.forEach((k, i) => {
      const [count, pct] = d.len[k];
      document.getElementById(`an-${patch}-len${lenIds[i]}-c`).textContent = count.toLocaleString();
      document.getElementById(`an-${patch}-len${lenIds[i]}-p`).textContent = pct.toFixed(1) + '%';
    });

    /* Terrain */
    ['shape', 'craft', 'space'].forEach(axis => {
      const t    = d.terrain[axis];
      const sign = t.val >= 0 ? '+' : '';
      document.getElementById(`an-${patch}-${axis}-bar`).style.width   = `${t.pct}%`;
      document.getElementById(`an-${patch}-${axis}-label`).innerHTML   =
        `${t.label} <span class="u-accent">${sign}${t.val.toFixed(3)}</span>`;
      const exParts = axis === 'shape'
        ? [`round: ${t.ex[0]}, ${t.ex[1]}`, `jagged: ${t.ex[2]}, ${t.ex[3]}`]
        : axis === 'craft'
        ? [`flowing: ${t.ex[0]}, ${t.ex[1]}`, `worked: ${t.ex[2]}, ${t.ex[3]}`]
        : [`open: ${t.ex[0]}, ${t.ex[1]}`, `dense: ${t.ex[2]}, ${t.ex[3]}`];
      document.getElementById(`an-${patch}-${axis}-ex`).textContent = exParts.join(' · ');
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
    /* Switch to Monitor and start demo run */
    switchTool('pipeline');
    navigateToScreen('pipeline-monitor');
    setTimeout(() => startPipelineDemoRun(), 100);
  });

  document.getElementById('pipe-cancel-btn')?.addEventListener('click', cancelPipelineDemoRun);
}


/* ═══════════════════════════════════════════════════════════════════════════
   20. PIPELINE MONITOR — DEMO RUN SIMULATION
   ═══════════════════════════════════════════════════════════════════════════ */

function syncMonitorFromConfig() {
  document.getElementById('monitor-job-source').textContent = state.pipeSource || '—';
  document.getElementById('monitor-job-output').textContent = state.pipeOutput || '—';
}

function initMonitorRun() {
  document.getElementById('monitor-run-btn')?.addEventListener('click', startPipelineDemoRun);
  document.getElementById('monitor-cancel-btn')?.addEventListener('click', cancelPipelineDemoRun);
}

function startPipelineDemoRun() {
  if (state.pipeJobRunning) return;
  state.pipeJobRunning = true;

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
  statusEl.textContent = 'running';
  statusEl.style.color = 'var(--col-warn)';
  badge.textContent = 'Running';
  badge.className = 'badge is-running';
  runBtn.disabled = true;
  cancelBtn.disabled = false;

  document.getElementById('monitor-job-source').textContent = state.pipeSource || '~/projects/demo_source/';
  document.getElementById('monitor-job-output').textContent = state.pipeOutput || '_working/output/demo/';

  /* Reset stage indicators */
  ['extract', 'normalize', 'annotate'].forEach(s => {
    const ind = document.getElementById(`stage-ind-${s}`);
    if (ind) ind.className = 'stage-indicator';
  });

  setStatus('Pipeline: running…');
  document.getElementById('sb-pipe-job-status').textContent = 'running';

  /* Simulate log lines with staggered timing */
  const totalLines = PIPELINE_LOG_LINES.length;
  let lineIdx = 0;

  function appendNextLine() {
    if (!state.pipeJobRunning) return;
    if (lineIdx >= totalLines) {
      finishPipelineDemoRun();
      return;
    }

    const line = PIPELINE_LOG_LINES[lineIdx];
    const span = document.createElement('span');
    span.className = `log-line ${line.cls}`;
    span.textContent = line.text;
    logEl.appendChild(span);
    logEl.scrollTop = logEl.scrollHeight;

    /* Update progress */
    const pct = Math.round((lineIdx / totalLines) * 100);
    fillEl.style.width = `${pct}%`;
    pctEl.textContent  = `${pct}%`;

    /* Update stage indicators */
    if (lineIdx === 3)  { setStageIndicator('extract',   'is-running'); stageEl.textContent = 'extract'; }
    if (lineIdx === 18) { setStageIndicator('extract',   'is-done');    setStageIndicator('normalize', 'is-running'); stageEl.textContent = 'normalize'; }
    if (lineIdx === 20) { setStageIndicator('normalize', 'is-done');    setStageIndicator('annotate',  'is-running'); stageEl.textContent = 'annotate'; }
    if (lineIdx === 24) { setStageIndicator('annotate',  'is-done');    stageEl.textContent = 'complete'; }

    lineIdx++;
    state.pipeJobTimer = setTimeout(appendNextLine, 80 + Math.random() * 60);
  }

  state.pipeJobTimer = setTimeout(appendNextLine, 200);
}

function setStageIndicator(stage, cls) {
  const ind = document.getElementById(`stage-ind-${stage}`);
  if (ind) ind.className = `stage-indicator ${cls}`;
}

function finishPipelineDemoRun() {
  state.pipeJobRunning = false;
  state.pipeJobTimer = null;

  const fillEl    = document.getElementById('monitor-progress-fill');
  const statusEl  = document.getElementById('monitor-job-status');
  const pctEl     = document.getElementById('monitor-job-pct');
  const badge     = document.getElementById('monitor-status-badge');
  const runBtn    = document.getElementById('monitor-run-btn');
  const cancelBtn = document.getElementById('monitor-cancel-btn');

  fillEl.style.width = '100%';
  pctEl.textContent  = '100%';
  statusEl.textContent = 'completed';
  statusEl.style.color = 'var(--col-ok)';
  badge.textContent = 'Completed';
  badge.className = 'badge is-done';
  runBtn.disabled = false;
  cancelBtn.disabled = true;

  document.getElementById('sb-pipe-job-status').textContent = 'completed';
  setStatus('Pipeline: run complete');
}

function cancelPipelineDemoRun() {
  if (!state.pipeJobRunning) return;
  state.pipeJobRunning = false;
  if (state.pipeJobTimer) clearTimeout(state.pipeJobTimer);

  const statusEl  = document.getElementById('monitor-job-status');
  const badge     = document.getElementById('monitor-status-badge');
  const runBtn    = document.getElementById('monitor-run-btn');
  const cancelBtn = document.getElementById('monitor-cancel-btn');

  statusEl.textContent = 'cancelled';
  statusEl.style.color = 'var(--col-text-muted)';
  badge.textContent = 'Cancelled';
  badge.className = 'badge badge--muted';
  runBtn.disabled = false;
  cancelBtn.disabled = true;

  const logEl = document.getElementById('monitor-log');
  const span = document.createElement('span');
  span.className = 'log-line log-line--warn';
  span.textContent = '[pipeline] run cancelled by user';
  logEl.appendChild(span);
  logEl.scrollTop = logEl.scrollHeight;

  document.getElementById('sb-pipe-job-status').textContent = 'cancelled';
  setStatus('Pipeline: cancelled');
}


/* ═══════════════════════════════════════════════════════════════════════════
   21. PIPELINE HISTORY — RUN SELECTION
   ═══════════════════════════════════════════════════════════════════════════ */

function initHistorySelection() {
  document.querySelectorAll('.history-run').forEach(row => {
    row.addEventListener('click', () => {
      document.querySelectorAll('.history-run').forEach(r => r.classList.remove('is-selected'));
      row.classList.add('is-selected');
      const runId = row.dataset.run;
      populateHistoryDetail(runId);
    });
  });

  document.getElementById('history-rerun-btn')?.addEventListener('click', () => {
    switchTool('pipeline');
    navigateToScreen('pipeline-monitor');
    setTimeout(() => startPipelineDemoRun(), 100);
  });
}

function populateHistoryDetail(runId) {
  const run = HISTORY_RUNS[runId];
  if (!run) return;

  document.getElementById('history-detail-name').textContent = run.name;
  document.getElementById('hd-status').textContent    = run.status;
  document.getElementById('hd-started').textContent   = run.started;
  document.getElementById('hd-duration').textContent  = run.duration;
  document.getElementById('hd-extractor').textContent = run.extractor;
  document.getElementById('hd-source').textContent    = run.source;
  document.getElementById('hd-files').textContent     = run.files;
  document.getElementById('hd-output').textContent    = run.output;
  document.getElementById('hd-syllables').textContent = run.syllables;

  /* Stage indicators */
  const stageNames = ['Extract', 'Normalize', 'Annotate'];
  const stageEls   = document.querySelectorAll('.history-stages .stage-indicator');
  stageEls.forEach((el, i) => {
    const s = run.stages[i];
    el.className = `stage-indicator${s === 'done' ? ' is-done' : s === 'error' ? ' is-error' : s === 'running' ? ' is-running' : ''}`;
    el.querySelector('.stage-indicator__label').innerHTML =
      `${stageNames[i]} <span class="u-muted">(${run.stageTime[i]})</span>`;
  });

  /* Output tree */
  const treeEl = document.querySelector('.history-outputs .output-box');
  if (treeEl) treeEl.textContent = run.tree;
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

  /* Populate history detail for first run */
  populateHistoryDetail('run-001');

  setStatus('Ready');
});
