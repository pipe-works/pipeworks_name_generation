/* ═══════════════════════════════════════════════════════════════════════════
   syllable-walk.js
   ─────────────────────────────────────────────────────────────────────────
   Pseudo-interactive demo script for Syllable Walker web UI.
   No backend wiring — all state is local, all outputs are simulated.

   SECTIONS
   ────────
   1. Theme Toggle
   2. Screen / Tab Navigation
   3. Spinner Buttons
   4. Slider Live Values
   5. Profile Selection
   6. Radio Option Selection
   7. Seed Randomise
   8. Corpus Browser Modal
   9. Generate Walks (demo)
   10. Generate Candidates (demo)
   11. Select Names (demo)
   12. Export TXT (demo)
   13. Render Screen — Combine Toggle
   14. Status Bar
   15. Init
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
      shape:  { val: 0.08,  label: 'NEUTRAL', pct: 55, ex: ['melo', 'sira', 'vendra', 'lorist'] },
      craft:  { val: -0.04, label: 'NEUTRAL', pct: 46, ex: ['thal', 'ven', 'bravendol', 'ormis'] },
      space:  { val: 0.12,  label: 'OPEN',    pct: 61, ex: ['alo', 'ive', 'thrix', 'skorn'] },
    },
  },
  nordic_roots: {
    total: 892, unique: 601, hapax: 198, hapaxRate: 0.222,
    len: { 2: [89, 10.0], 3: [401, 45.0], 4: [312, 35.0], '5+': [90, 10.1] },
    terrain: {
      shape:  { val: 0.18,  label: 'JAGGED', pct: 68, ex: ['skr', 'ulf', 'bjorn', 'vik'] },
      craft:  { val: 0.22,  label: 'WORKED', pct: 71, ex: ['stein', 'borg', 'fjord', 'helm'] },
      space:  { val: -0.08, label: 'OPEN',   pct: 40, ex: ['alf', 'ulf', 'stig', 'orm'] },
    },
  },
  latin_fragments: {
    total: 2105, unique: 1432, hapax: 621, hapaxRate: 0.295,
    len: { 2: [210, 10.0], 3: [631, 30.0], 4: [842, 40.0], '5+': [422, 20.0] },
    terrain: {
      shape:  { val: -0.12, label: 'ROUND',  pct: 35, ex: ['aur', 'ora', 'lius', 'ius'] },
      craft:  { val: -0.18, label: 'FLOWING', pct: 30, ex: ['us', 'ium', 'ia', 'alis'] },
      space:  { val: 0.24,  label: 'DENSE',  pct: 74, ex: ['str', 'ct', 'nstr', 'mpl'] },
    },
  },
  goblin_tongue: {
    total: 567, unique: 389, hapax: 178, hapaxRate: 0.314,
    len: { 2: [113, 19.9], 3: [227, 40.0], 4: [170, 30.0], '5+': [57, 10.1] },
    terrain: {
      shape:  { val: 0.31,  label: 'JAGGED', pct: 80, ex: ['krix', 'skr', 'thrax', 'brak'] },
      craft:  { val: 0.19,  label: 'WORKED', pct: 69, ex: ['grix', 'vorn', 'skorn', 'theld'] },
      space:  { val: -0.22, label: 'OPEN',   pct: 28, ex: ['rix', 'ax', 'orn', 'eld'] },
    },
  },
};

/* State */
const state = {
  corpusA: null,
  corpusB: null,
  walksA: [],
  walksB: [],
  namesA: [],
  namesB: [],
  pendingCorpusPatch: null,
  pendingCorpusItem: null,
};


/* ─────────────────────────────────────────────────────────────────────────
   1. THEME TOGGLE
   ───────────────────────────────────────────────────────────────────────── */

function initThemeToggle() {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;

  const savedTheme = localStorage.getItem('pw-theme') || 'dark';
  applyTheme(savedTheme);

  btn.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    applyTheme(next);
    localStorage.setItem('pw-theme', next);
  });
}

function applyTheme(theme) {
  const btn = document.getElementById('theme-toggle');
  if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    if (btn) btn.textContent = 'Dark Theme';
  } else {
    document.documentElement.removeAttribute('data-theme');
    if (btn) btn.textContent = 'Light Theme';
  }
}


/* ─────────────────────────────────────────────────────────────────────────
   2. SCREEN / TAB NAVIGATION
   ───────────────────────────────────────────────────────────────────────── */

function initTabs() {
  const tabs = document.querySelectorAll('.tab[data-screen]');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const screenId = 'screen-' + tab.dataset.screen;

      // Deactivate all tabs
      tabs.forEach(t => {
        t.classList.remove('is-active');
        t.removeAttribute('aria-current');
      });

      // Hide all screens
      document.querySelectorAll('.screen').forEach(s => {
        s.classList.remove('is-visible');
        s.hidden = true;
      });

      // Activate selected tab + screen
      tab.classList.add('is-active');
      tab.setAttribute('aria-current', 'page');
      const screen = document.getElementById(screenId);
      if (screen) {
        screen.hidden = false;
        screen.classList.add('is-visible');
        // Sync screens when switching to them
        if (tab.dataset.screen === 'blended')  syncBlendedScreen();
        if (tab.dataset.screen === 'render')   syncRenderScreen();
        if (tab.dataset.screen === 'analysis') syncAnalysisScreen();
      }
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   3. SPINNER BUTTONS
   ───────────────────────────────────────────────────────────────────────── */

function initSpinners() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('.spinner-btn');
    if (!btn) return;

    const targetId = btn.dataset.target;
    const delta    = parseFloat(btn.dataset.delta);
    const input    = document.getElementById(targetId);
    if (!input) return;

    const min  = parseFloat(input.min)  || -Infinity;
    const max  = parseFloat(input.max)  ||  Infinity;
    const step = parseFloat(input.step) || 1;
    let   val  = parseFloat(input.value) || 0;

    val = Math.min(max, Math.max(min, val + delta));

    // Round to avoid floating point drift
    const decimals = (step.toString().split('.')[1] || '').length;
    val = parseFloat(val.toFixed(decimals));

    input.value = val;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  // Walk steps suffix update
  ['a', 'b'].forEach(patch => {
    const stepsInput = document.getElementById(`walk-steps-${patch}`);
    if (!stepsInput) return;
    stepsInput.addEventListener('input', () => {
      const suffix = document.getElementById(`walk-steps-${patch}-suffix`);
      if (suffix) suffix.textContent = `→ ${parseInt(stepsInput.value, 10) + 1} syl`;
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   4. SLIDER LIVE VALUES
   ───────────────────────────────────────────────────────────────────────── */

function initSliders() {
  const sliderPairs = [
    ['temperature-a',  'temperature-a-val'],
    ['freq-weight-a',  'freq-weight-a-val'],
    ['temperature-b',  'temperature-b-val'],
    ['freq-weight-b',  'freq-weight-b-val'],
    ['comb-freq-a',    'comb-freq-a-val'],
    ['comb-freq-b',    'comb-freq-b-val'],
  ];

  sliderPairs.forEach(([sliderId, valId]) => {
    const slider = document.getElementById(sliderId);
    const valEl  = document.getElementById(valId);
    if (!slider || !valEl) return;

    const update = () => {
      valEl.textContent = parseFloat(slider.value).toFixed(1);
    };
    slider.addEventListener('input', update);
    update();
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   5. PROFILE SELECTION
   ───────────────────────────────────────────────────────────────────────── */

function initProfiles() {
  document.querySelectorAll('.profile-option').forEach(option => {
    option.addEventListener('click', () => {
      const patch = option.dataset.patch;
      // Deselect all in same patch
      document.querySelectorAll(`.profile-option[data-patch="${patch}"]`).forEach(o => {
        o.classList.remove('is-selected');
      });
      option.classList.add('is-selected');
      const radio = option.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   6. RADIO OPTION SELECTION
   ───────────────────────────────────────────────────────────────────────── */

function initRadioOptions() {
  document.querySelectorAll('.radio-option').forEach(option => {
    option.addEventListener('click', () => {
      const radio = option.querySelector('input[type="radio"]');
      if (!radio) return;
      const name = radio.name;
      // Deselect siblings
      document.querySelectorAll(`.radio-option input[name="${name}"]`).forEach(r => {
        r.closest('.radio-option').classList.remove('is-selected');
      });
      option.classList.add('is-selected');
      radio.checked = true;
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   7. SEED RANDOMISE
   ───────────────────────────────────────────────────────────────────────── */

function initSeedButtons() {
  // Named seed buttons
  ['seed-random-a', 'seed-random-b'].forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    const patch = btnId.endsWith('-a') ? 'a' : 'b';
    btn.addEventListener('click', () => {
      const input = document.getElementById(`seed-${patch}`);
      if (input) input.value = Math.floor(Math.random() * 0xFFFFFF).toString(16).padStart(6, '0');
    });
  });

  // Generic random seed buttons via data-random-seed
  document.querySelectorAll('[data-random-seed]').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.randomSeed);
      if (input) input.value = Math.floor(Math.random() * 0xFFFFFF).toString(16).padStart(6, '0');
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   8. CORPUS BROWSER MODAL
   ───────────────────────────────────────────────────────────────────────── */

function initCorpusModal() {
  const modal      = document.getElementById('corpus-modal');
  const closeBtn   = document.getElementById('corpus-modal-close');
  const cancelBtn  = document.getElementById('corpus-modal-cancel');
  const selectBtn  = document.getElementById('corpus-modal-select');
  const backdrop   = document.getElementById('corpus-modal-backdrop');
  if (!modal) return;

  // Open modal from patch buttons
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`select-corpus-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      state.pendingCorpusPatch = patch;
      state.pendingCorpusItem  = null;
      selectBtn.disabled = true;
      document.querySelectorAll('.corpus-browser__item').forEach(i => i.classList.remove('is-selected'));
      modal.classList.remove('hidden');
    });
  });

  // Item selection
  document.querySelectorAll('.corpus-browser__item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.corpus-browser__item').forEach(i => i.classList.remove('is-selected'));
      item.classList.add('is-selected');
      state.pendingCorpusItem = item.dataset.corpus;
      selectBtn.disabled = false;
    });
  });

  // Confirm
  selectBtn.addEventListener('click', () => {
    if (!state.pendingCorpusItem || !state.pendingCorpusPatch) return;
    const patch  = state.pendingCorpusPatch;
    const corpus = state.pendingCorpusItem;
    const meta   = CORPUS_META[corpus];

    if (patch === 'a') state.corpusA = corpus;
    else               state.corpusB = corpus;

    const statusEl = document.getElementById(`corpus-status-${patch}`);
    if (statusEl) {
      statusEl.textContent = `${corpus}/ · ${meta.syllables.toLocaleString()} syllables`;
      statusEl.classList.add('is-loaded');
      statusEl.classList.remove('u-muted');
    }

    const statusBarEl = document.getElementById(`status-corpus-${patch}`);
    if (statusBarEl) statusBarEl.textContent = corpus;

    setStatus(`Corpus loaded: ${corpus}`);
    modal.classList.add('hidden');
  });

  // Close / cancel
  [closeBtn, cancelBtn, backdrop].forEach(el => {
    if (!el) return;
    el.addEventListener('click', () => modal.classList.add('hidden'));
  });

  // ESC key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
      modal.classList.add('hidden');
    }
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   9. GENERATE WALKS (demo)
   ───────────────────────────────────────────────────────────────────────── */

function initGenerateWalks() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-${patch}`);
    if (!btn) return;

    btn.addEventListener('click', () => {
      const corpus = patch === 'a' ? state.corpusA : state.corpusB;
      if (!corpus) {
        setStatus(`Patch ${patch.toUpperCase()}: No corpus loaded — select a corpus first`, 'warn');
        return;
      }

      const countInput = document.getElementById(`walk-count-${patch}`);
      const count = Math.min(parseInt(countInput?.value || 2, 10), DEMO_WALKS[patch.toUpperCase()].length);
      const walks = DEMO_WALKS[patch.toUpperCase()].slice(0, count);

      if (patch === 'a') state.walksA = walks;
      else               state.walksB = walks;

      const outputEl = document.getElementById(`walks-output-${patch}`);
      if (outputEl) {
        outputEl.innerHTML = walks.map(w => `<span class="walk-item">${w}</span>`).join('');
      }

      setStatus(`Patch ${patch.toUpperCase()}: Generated ${walks.length} walk${walks.length !== 1 ? 's' : ''}`);
      btn.textContent = 'Regenerate Walks';
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   10. GENERATE CANDIDATES (demo)
   ───────────────────────────────────────────────────────────────────────── */

function initGenerateCandidates() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-candidates-${patch}`);
    if (!btn) return;

    btn.addEventListener('click', () => {
      const corpus = patch === 'a' ? state.corpusA : state.corpusB;
      if (!corpus) {
        setStatus(`Patch ${patch.toUpperCase()}: No corpus loaded`, 'warn');
        return;
      }

      const syllables = document.getElementById(`comb-syllables-${patch}`)?.value || 2;
      const count     = document.getElementById(`comb-count-${patch}`)?.value     || 10000;
      const freqW     = document.getElementById(`comb-freq-${patch}`)?.value      || 1.0;

      const generated = parseInt(count, 10);
      const unique    = Math.floor(generated * 0.73);
      const uniquePct = ((unique / generated) * 100).toFixed(1);

      const outputEl = document.getElementById(`comb-output-${patch}`);
      if (outputEl) {
        outputEl.innerHTML = [
          `<span class="meta-key">Syllables:</span> <span class="meta-val">${syllables}</span>`,
          `<span class="meta-key">Count:</span>     <span class="meta-val">${parseInt(count).toLocaleString()}</span>`,
          `<span class="meta-key">Freq Weight:</span> <span class="meta-val">${parseFloat(freqW).toFixed(1)}</span>`,
          ``,
          `<span class="meta-key">Generated:</span> <span class="meta-val">${generated.toLocaleString()} candidates</span>`,
          `<span class="meta-key">Unique:</span>    <span class="meta-val">${unique.toLocaleString()} (${uniquePct}%)</span>`,
          `<span class="meta-path">→ candidates/${corpus}_${syllables}syl.json</span>`,
        ].join('\n');
      }

      setStatus(`Patch ${patch.toUpperCase()}: Generated ${generated.toLocaleString()} candidates (${unique.toLocaleString()} unique)`);
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   11. SELECT NAMES (demo)
   ───────────────────────────────────────────────────────────────────────── */

function initSelectNames() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`select-names-${patch}`);
    if (!btn) return;

    btn.addEventListener('click', () => {
      const corpus = patch === 'a' ? state.corpusA : state.corpusB;
      if (!corpus) {
        setStatus(`Patch ${patch.toUpperCase()}: No corpus loaded`, 'warn');
        return;
      }

      const nameClass = document.getElementById(`sel-class-${patch}`)?.value || 'first_name';
      const count     = parseInt(document.getElementById(`sel-count-${patch}`)?.value || 100, 10);
      const mode      = document.querySelector(`input[name="sel-mode-${patch}"]:checked`)?.value || 'hard';
      const order     = document.querySelector(`input[name="sel-order-${patch}"]:checked`)?.value || 'random';

      const allNames  = DEMO_NAMES[patch.toUpperCase()];
      const selected  = allNames.slice(0, Math.min(count, allNames.length));

      if (patch === 'a') state.namesA = selected;
      else               state.namesB = selected;

      const total     = allNames.length * 10;
      const admitted  = Math.floor(total * 0.68);
      const admPct    = ((admitted / total) * 100).toFixed(1);
      const rejected  = total - admitted;

      // Meta
      const metaEl = document.querySelector(`#sel-output-${patch} .selector-output__meta`);
      if (metaEl) {
        metaEl.innerHTML = [
          `<span class="meta-key">Name Class:</span> ${nameClass.replace('_', ' ')}`,
          `<span class="meta-key">Count:</span>      ${count}`,
          `<span class="meta-key">Mode:</span>       ${mode}`,
          `<span class="meta-key">Order:</span>      ${order}`,
          ``,
          `<span class="meta-key">Evaluated:</span> ${total.toLocaleString()}`,
          `<span class="meta-key">Admitted:</span>  <span class="meta-val">${admitted.toLocaleString()} (${admPct}%)</span>`,
          `<span class="meta-key">Rejected:</span>  ${rejected.toLocaleString()}`,
          ``,
          `<span class="meta-key">Selected:</span>  <span class="meta-val">${selected.length}</span>`,
          `<span class="meta-path">→ selections/${corpus}_${nameClass}.json</span>`,
        ].join('\n');
      }

      // Names list
      const namesEl = document.getElementById(`sel-names-${patch}`);
      if (namesEl) {
        namesEl.innerHTML = selected.map(n => `<span class="name-item">${n}</span>`).join('');
      }

      setStatus(`Patch ${patch.toUpperCase()}: Selected ${selected.length} names`);
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   12. EXPORT TXT (demo)
   ───────────────────────────────────────────────────────────────────────── */

function initExport() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`export-txt-${patch}`);
    if (!btn) return;

    btn.addEventListener('click', () => {
      const names = patch === 'a' ? state.namesA : state.namesB;
      if (!names.length) {
        setStatus(`Patch ${patch.toUpperCase()}: No names selected yet`, 'warn');
        return;
      }

      const blob     = new Blob([names.join('\n')], { type: 'text/plain' });
      const url      = URL.createObjectURL(blob);
      const anchor   = document.createElement('a');
      anchor.href    = url;
      anchor.download = `patch_${patch}_names.txt`;
      anchor.click();
      URL.revokeObjectURL(url);

      setStatus(`Patch ${patch.toUpperCase()}: Exported ${names.length} names to TXT`);
    });
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   13. RENDER SCREEN — COMBINE TOGGLE
   ───────────────────────────────────────────────────────────────────────── */

function initRenderScreen() {
  const combineToggle = document.getElementById('render-combine');
  const combinedCol   = document.getElementById('render-combined-col');
  const styleSelect   = document.getElementById('render-style');

  if (combineToggle && combinedCol) {
    combineToggle.addEventListener('change', () => {
      combinedCol.style.display = combineToggle.checked ? 'flex' : 'none';
      // Adjust grid
      const cols = document.querySelector('.render-columns');
      if (cols) {
        cols.style.gridTemplateColumns = combineToggle.checked ? '1fr 1fr 1fr' : '1fr 1fr';
      }
      syncRenderScreen();
    });
  }

  if (styleSelect) {
    styleSelect.addEventListener('change', syncRenderScreen);
  }
}

function applyStyle(name, style) {
  switch (style) {
    case 'upper': return name.toUpperCase();
    case 'lower': return name.toLowerCase();
    default:      return name.charAt(0).toUpperCase() + name.slice(1);
  }
}

function syncRenderScreen() {
  const style = document.getElementById('render-style')?.value || 'title';

  ['a', 'b'].forEach(patch => {
    const names   = patch === 'a' ? state.namesA : state.namesB;
    const listEl  = document.getElementById(`render-names-${patch}`);
    if (!listEl) return;

    if (!names.length) {
      listEl.innerHTML = '<p class="placeholder-text">(Select names in the Walk screen first)</p>';
      return;
    }

    listEl.innerHTML = names
      .map(n => `<span class="render-name">${applyStyle(n, style)}</span>`)
      .join('');
  });

  // Combined
  const combinedEl = document.getElementById('render-names-combined');
  if (combinedEl) {
    if (!state.namesA.length || !state.namesB.length) {
      combinedEl.innerHTML = '<p class="placeholder-text">(Need names from both patches)</p>';
      return;
    }
    const len = Math.min(state.namesA.length, state.namesB.length);
    const combined = [];
    for (let i = 0; i < len; i++) {
      combined.push(`${applyStyle(state.namesA[i], style)} ${applyStyle(state.namesB[i], style)}`);
    }
    combinedEl.innerHTML = combined
      .map(n => `<span class="render-name">${n}</span>`)
      .join('');
  }
}


/* ─────────────────────────────────────────────────────────────────────────
   Analysis screen population
   ───────────────────────────────────────────────────────────────────────── */

function populateAnalysis(patch) {
  const corpus = patch === 'a' ? state.corpusA : state.corpusB;
  const p = patch.toUpperCase();
  const hint = document.getElementById(`analysis-hint-${patch}`);

  if (!corpus || !CORPUS_ANALYSIS[corpus]) {
    if (hint) hint.textContent = 'Load a corpus in the Walk screen to populate metrics.';
    return;
  }

  const data = CORPUS_ANALYSIS[corpus];
  if (hint) hint.textContent = `Showing analysis for: ${corpus}/`;

  // Inventory
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set(`an-${patch}-total`,      data.total.toLocaleString());
  set(`an-${patch}-unique`,     data.unique.toLocaleString());
  set(`an-${patch}-hapax`,      data.hapax.toLocaleString());
  set(`an-${patch}-hapax-rate`, (data.hapaxRate * 100).toFixed(1) + '%');

  // Length distribution
  const lenKeys = ['2', '3', '4', '5+'];
  lenKeys.forEach(k => {
    const key = k === '5+' ? '5+' : k;
    const row = data.len[key];
    if (!row) return;
    set(`an-${patch}-len${k.replace('+', '5')}`,  row[0].toLocaleString());
    set(`an-${patch}-len${k.replace('+', '5')}p`, row[1].toFixed(1) + '%');
  });

  // Terrain bars
  ['shape', 'craft', 'space'].forEach(axis => {
    const t = data.terrain[axis];
    const bar   = document.getElementById(`an-${patch}-${axis}-bar`);
    const label = document.getElementById(`an-${patch}-${axis}-label`);
    const ex    = document.getElementById(`an-${patch}-${axis}-ex`);
    if (bar)   bar.style.width = t.pct + '%';
    if (label) label.innerHTML = `${t.label} <span class="u-accent">${t.val >= 0 ? '+' : ''}${t.val.toFixed(3)}</span>`;
    if (ex && t.ex.length >= 2) {
      const mid = Math.floor(t.ex.length / 2);
      const left  = t.ex.slice(0, mid).join(', ');
      const right = t.ex.slice(mid).join(', ');
      const axisLabels = { shape: ['round', 'jagged'], craft: ['flowing', 'worked'], space: ['open', 'dense'] };
      const [lbl1, lbl2] = axisLabels[axis];
      ex.textContent = `${lbl1}: ${left} · ${lbl2}: ${right}`;
    }
  });
}

function syncAnalysisScreen() {
  populateAnalysis('a');
  populateAnalysis('b');
}


/* ─────────────────────────────────────────────────────────────────────────
   Package build (demo)
   ───────────────────────────────────────────────────────────────────────── */

function initPackageScreen() {
  const btn = document.getElementById('build-package');
  const output = document.getElementById('pkg-output');
  if (!btn || !output) return;

  btn.addEventListener('click', () => {
    const name    = document.getElementById('pkg-name')?.value || 'my-corpus-package';
    const version = document.getElementById('pkg-version')?.value || '0.1.0';
    const corpusA = state.corpusA || '(none)';
    const corpusB = state.corpusB || '(none)';
    const walksA  = state.walksA.length;
    const walksB  = state.walksB.length;
    const namesA  = state.namesA.length;
    const namesB  = state.namesB.length;

    const now = new Date().toISOString().replace('T', ' ').slice(0, 19);

    const lines = [
      `${name}-${version}/`,
      `├── manifest.json`,
      `├── patch_a/`,
      `│   ├── corpus/       ${corpusA}`,
      walksA  ? `│   ├── walks/        ${walksA} walk file${walksA !== 1 ? 's' : ''}` : null,
      namesA  ? `│   └── selections/   ${namesA} name${namesA !== 1 ? 's' : ''} selected` : null,
      `├── patch_b/`,
      `│   ├── corpus/       ${corpusB}`,
      walksB  ? `│   ├── walks/        ${walksB} walk file${walksB !== 1 ? 's' : ''}` : null,
      namesB  ? `│   └── selections/   ${namesB} name${namesB !== 1 ? 's' : ''} selected` : null,
      `└── README.md`,
      ``,
      `Built: ${now}`,
      `Total names: ${namesA + namesB}`,
    ].filter(l => l !== null).join('\n');

    output.textContent = lines;
    setStatus(`Package built: ${name}-${version}`);
    btn.textContent = 'Rebuild Package';
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   Sync blended screen
   ───────────────────────────────────────────────────────────────────────── */

function syncBlendedScreen() {
  ['a', 'b'].forEach(patch => {
    const walks  = patch === 'a' ? state.walksA : state.walksB;
    const outEl  = document.getElementById(`blended-${patch}-output`);
    if (!outEl) return;

    if (!walks.length) {
      outEl.innerHTML = '<p class="placeholder-text">(Generate walks in the Walk screen first)</p>';
      return;
    }

    outEl.innerHTML = walks.map(w => `<span class="walk-item">${w}</span>`).join('');
  });
}


/* ─────────────────────────────────────────────────────────────────────────
   14. STATUS BAR
   ───────────────────────────────────────────────────────────────────────── */

let statusTimer = null;

function setStatus(message, level = 'ok') {
  const el = document.getElementById('status-text');
  if (!el) return;

  el.textContent = message;
  el.className = 'status-bar__text';

  if (level === 'warn') el.classList.add('u-warn');
  else if (level === 'err') el.classList.add('u-err');
  else el.classList.add('u-ok');

  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => {
    el.textContent = 'Ready';
    el.className   = 'status-bar__text';
  }, 4000);
}


/* ─────────────────────────────────────────────────────────────────────────
   15. INIT
   ───────────────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initTabs();
  initSpinners();
  initSliders();
  initProfiles();
  initRadioOptions();
  initSeedButtons();
  initCorpusModal();
  initGenerateWalks();
  initGenerateCandidates();
  initSelectNames();
  initExport();
  initRenderScreen();
  initPackageScreen();
});
