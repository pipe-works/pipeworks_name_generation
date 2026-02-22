/*
   walker/reach.js
   Sections 6a and 10b:
   - profile tabs with reach-syllable lazy loading/export
   - reach micro-signal, tooltip, and deep-dive modal
*/

'use strict';

/** @type {{
 *   setStatus: (msg: string) => void,
 *   downloadBlob: (content: string, filename: string, type: string) => void
 * } | null} */
let _ctx = null;

/* Cache for lazy-loaded syllable data. Keyed by "{patch}-{profile}". */
const _reachSyllables = {};

/* Per-profile reach data cache for tooltips. Keyed by "a-dialect", "b-goblin", etc.
   Populated by updateReachValues() and read by the tooltip on hover. */
const _reachData = {};

/* Cached per-patch reach summary lines for the combine bar.
   Both lines are displayed when both patches have data. */
const _combineReachLines = { a: null, b: null };

/**
 * Replace container contents with placeholder text.
 *
 * @param {HTMLElement | null} el - Target container.
 * @param {string} message - Placeholder text.
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
 * Initialise reach-related UI systems.
 *
 * @param {{
 *   setStatus: (msg: string) => void,
 *   downloadBlob: (content: string, filename: string, type: string) => void
 * }} ctx - Cross-cutting helpers used by reach/profile-tab flows.
 * @returns {void}
 * Side effects:
 * - Registers profile-tab and modal close/open listeners.
 */
export function initReachModule(ctx) {
  _ctx = ctx;
  initProfileTabs();
  initReachModal();
}

/**
 * Initialise the profile tab group for both Patch A and Patch B.
 *
 * Each profile section has a tab bar: "Profiles" (radio list) plus one
 * tab per named profile (clerical, dialect, goblin, ritual) that shows
 * a table of reachable syllables, fetched on demand from the API.
 *
 * @returns {void}
 */
function initProfileTabs() {
  document.querySelectorAll('.profile-tabs__tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const patch = tab.dataset.patch;
      const target = tab.dataset.profileTab;

      /* Toggle active tab within this patch's tab group */
      tab.closest('.profile-tabs').querySelectorAll('.profile-tabs__tab')
        .forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');

      /* Show/hide panels */
      tab.closest('.profile-tabs').querySelectorAll('.profile-tabs__panel')
        .forEach(p => p.hidden = true);
      const panel = document.getElementById(`profile-panel-${patch}-${target}`);
      if (panel) panel.hidden = false;

      /* Lazy-load syllable data for named profile tabs */
      if (target !== 'list') {
        loadReachSyllables(patch, target);
      }
    });
  });
}

/**
 * Fetch and render the reachable syllables for a given patch and profile.
 *
 * Cached after first fetch — subsequent tab switches reuse the cached data.
 *
 * @param {string} patch - "a" or "b"
 * @param {string} profile - "clerical", "dialect", "goblin", or "ritual"
 * @returns {void}
 */
function loadReachSyllables(patch, profile) {
  const key = `${patch}-${profile}`;
  const container = document.getElementById(`reach-syllables-${patch}-${profile}`);
  if (!container) return;

  /* Already loaded — skip. */
  if (_reachSyllables[key]) return;

  /* Check if reach data is available. */
  if (!_reachData[key]) {
    setPlaceholder(container, '(Load a corpus to view reachable syllables)');
    return;
  }

  setPlaceholder(container, 'Loading syllables…');

  fetch('/api/walker/reach-syllables', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patch: patch, profile: profile }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        setPlaceholder(container, String(data.error));
        return;
      }

      _reachSyllables[key] = data;
      renderReachSyllables(container, data);
    })
    .catch(err => {
      setPlaceholder(container, `Error: ${err.message}`);
    });
}

/**
 * Convert reach-syllable payload to plain text export format.
 *
 * @param {{syllables: Array<{syllable: string}>}} data - Reach payload.
 * @returns {string}
 */
function reachSyllablesToTxt(data) {
  const lines = data.syllables.map(s => s.syllable);
  return lines.join('\n') + '\n';
}

/**
 * Convert reach-syllable payload to Markdown table format.
 *
 * @param {{profile: string, total: number, syllables: Array<{syllable: string, frequency: number, reachability: number}>}} data - Reach payload.
 * @returns {string}
 */
function reachSyllablesToMd(data) {
  const header = '| # | Syllable | Freq | Nodes |\n| ---: | --- | ---: | ---: |';
  const rows = data.syllables.map((s, i) =>
    `| ${i + 1} | ${s.syllable} | ${s.frequency.toLocaleString()} | ${s.reachability.toLocaleString()} |`
  );
  return `## ${data.profile} — top ${data.syllables.length} / ${data.total} syllables by reachability\n\n` +
    [header, ...rows].join('\n') + '\n';
}

/**
 * Flash a button with temporary confirmation text.
 *
 * @param {HTMLElement} btn - Button element to animate.
 * @param {string} msg - Temporary label text.
 * @returns {void}
 */
function flashBtn(btn, msg) {
  const orig = btn.textContent;
  btn.textContent = msg;
  btn.classList.add('btn--flash');
  setTimeout(() => { btn.textContent = orig; btn.classList.remove('btn--flash'); }, 1200);
}

/**
 * Render one reach-syllables table and wire export/copy actions.
 *
 * @param {HTMLElement} container - The .reach-syllables div.
 * @param {{profile: string, total: number, syllables: Array<{syllable: string, frequency: number, reachability: number}>}} data - API response payload.
 * @returns {void}
 */
function renderReachSyllables(container, data) {
  const syllables = data.syllables || [];
  const count = syllables.length;
  const patch = container.id.split('-')[2];   /* reach-syllables-{patch}-{profile} */
  const profile = data.profile;
  const pfx = `reach-${patch}-${profile}`;

  container.replaceChildren();

  const header = document.createElement('div');
  header.className = 'reach-syllables__header';
  const profileEl = document.createElement('span');
  profileEl.className = 'u-accent';
  profileEl.textContent = profile;
  const summaryEl = document.createElement('span');
  summaryEl.className = 'u-muted';
  summaryEl.textContent = `— top ${count.toLocaleString()} / ${data.total.toLocaleString()} syllables by reachability`;
  header.append(profileEl, summaryEl);
  container.appendChild(header);

  const exportBar = document.createElement('div');
  exportBar.className = 'reach-syllables__export-bar';
  const buttonDefs = [
    { id: `${pfx}-copy-txt`, label: 'Copy TXT' },
    { id: `${pfx}-copy-md`, label: 'Copy MD' },
    { id: `${pfx}-export-txt`, label: 'Export TXT' },
    { id: `${pfx}-export-md`, label: 'Export MD' },
  ];
  buttonDefs.forEach(def => {
    const btn = document.createElement('button');
    btn.className = 'btn btn--secondary btn--sm';
    btn.id = def.id;
    btn.textContent = def.label;
    exportBar.appendChild(btn);
  });
  container.appendChild(exportBar);

  const scrollWrap = document.createElement('div');
  scrollWrap.className = 'reach-syllables__scroll';
  const table = document.createElement('table');
  table.className = 'reach-syllables__table';
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['#', 'Syllable', 'Freq', 'Nodes'].forEach(label => {
    const th = document.createElement('th');
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  syllables.forEach((s, i) => {
    const row = document.createElement('tr');
    const indexTd = document.createElement('td');
    indexTd.textContent = String(i + 1);
    const syllableTd = document.createElement('td');
    syllableTd.textContent = s.syllable;
    const freqTd = document.createElement('td');
    freqTd.textContent = s.frequency.toLocaleString();
    const reachTd = document.createElement('td');
    reachTd.textContent = s.reachability.toLocaleString();
    row.append(indexTd, syllableTd, freqTd, reachTd);
    tbody.appendChild(row);
  });
  table.appendChild(tbody);
  scrollWrap.appendChild(table);
  container.appendChild(scrollWrap);

  /* Wire button handlers with visual feedback */
  document.getElementById(`${pfx}-copy-txt`)?.addEventListener('click', function () {
    navigator.clipboard.writeText(reachSyllablesToTxt(data)).then(() => {
      flashBtn(this, 'Copied!');
      _ctx.setStatus(`Patch ${patch.toUpperCase()}: copied ${count} ${profile} reach syllables as TXT`);
    });
  });
  document.getElementById(`${pfx}-copy-md`)?.addEventListener('click', function () {
    navigator.clipboard.writeText(reachSyllablesToMd(data)).then(() => {
      flashBtn(this, 'Copied!');
      _ctx.setStatus(`Patch ${patch.toUpperCase()}: copied ${count} ${profile} reach syllables as Markdown`);
    });
  });
  document.getElementById(`${pfx}-export-txt`)?.addEventListener('click', function () {
    _ctx.downloadBlob(reachSyllablesToTxt(data), `patch_${patch}_${profile}_reach.txt`, 'text/plain');
    flashBtn(this, 'Saved!');
    _ctx.setStatus(`Patch ${patch.toUpperCase()}: exported ${count} ${profile} reach syllables as TXT`);
  });
  document.getElementById(`${pfx}-export-md`)?.addEventListener('click', function () {
    _ctx.downloadBlob(reachSyllablesToMd(data), `patch_${patch}_${profile}_reach.md`, 'text/markdown');
    flashBtn(this, 'Saved!');
    _ctx.setStatus(`Patch ${patch.toUpperCase()}: exported ${count} ${profile} reach syllables as Markdown`);
  });
}

/**
 * Update reach value displays for one patch and refresh dependent caches/views.
 *
 * @param {'a'|'b'|string} patch - Patch id whose reach results changed.
 * @param {Record<string, {reach: number, total: number, threshold: number, computation_ms: number}>} reaches - Per-profile reach results.
 * @returns {void}
 * Side effects:
 * - Invalidates profile reach-syllables cache for that patch.
 * - Updates inline reach micro-signals and tooltip wiring.
 * - Updates combine reach summary bar.
 */
export function updateReachValues(patch, reaches) {
  /* Invalidate cached syllable tables — new corpus means new reach data. */
  for (const name of Object.keys(reaches)) {
    delete _reachSyllables[`${patch}-${name}`];
  }

  for (const [name, info] of Object.entries(reaches)) {
    /* Cache per-profile reach data for tooltip display. */
    _reachData[`${patch}-${name}`] = info;

    /* Populate reach spans for both the Walk tab and the Combiner tab.
       Walk tab uses "reach-{patch}-{name}", Combiner uses "comb-reach-{patch}-{name}". */
    const ids = [`reach-${patch}-${name}`, `comb-reach-${patch}-${name}`];

    for (const elId of ids) {
      const el = document.getElementById(elId);
      if (!el) continue;

      /* Level 1: inline micro signal — muted, monospace, right-aligned */
      el.textContent = `reach ≈${info.reach.toLocaleString()}`;

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
 * @param {HTMLElement} anchor - The .profile-reach span being hovered.
 * @param {string} key - Cache key like "a-dialect".
 * @returns {void}
 */
function showReachTooltip(anchor, key) {
  const info = _reachData[key];
  if (!info) return;

  const tooltip = document.getElementById('reach-tooltip');
  const titleEl = document.getElementById('reach-tooltip-title');
  const bodyEl = document.getElementById('reach-tooltip-body');
  const paramsEl = document.getElementById('reach-tooltip-params');

  /* Extract profile name from the key ("a-dialect" -> "dialect") */
  const profileName = key.split('-').slice(1).join('-');

  titleEl.textContent = `${profileName} profile`;
  bodyEl.textContent =
    'Mean effective vocabulary per step - the average number of ' +
    'syllables reachable from any starting position. Deterministic ' +
    'and seed-independent.';

  /* Parameter grid */
  paramsEl.replaceChildren();
  const rows = [
    ['reach', `≈${info.reach.toLocaleString()} / ${info.total.toLocaleString()}`],
    ['threshold', String(info.threshold)],
    ['computed in', `${info.computation_ms.toFixed(0)} ms`],
  ];
  rows.forEach(([term, value]) => {
    const dt = document.createElement('dt');
    dt.textContent = term;
    const dd = document.createElement('dd');
    dd.textContent = value;
    paramsEl.append(dt, dd);
  });

  /* Position above the anchor element */
  const rect = anchor.getBoundingClientRect();
  tooltip.style.left = `${Math.max(8, rect.left - 160)}px`;
  tooltip.style.top = `${rect.top - 8}px`;
  tooltip.style.transform = 'translateY(-100%)';

  tooltip.classList.add('is-visible');
}

/**
 * Hide the reach tooltip.
 *
 * @returns {void}
 */
function hideReachTooltip() {
  const tooltip = document.getElementById('reach-tooltip');
  tooltip.classList.remove('is-visible');
}

/**
 * Update the combine-tab reach summary bar for one patch.
 *
 * @param {'a'|'b'|string} patch - Patch key being updated.
 * @param {Record<string, {reach: number}>} reaches - Per-profile reach values.
 * @returns {void}
 */
function updateCombineReachBar(patch, reaches) {
  const textEl = document.getElementById('combine-reach-text');
  if (!textEl) return;

  const P = patch.toUpperCase();
  const parts = Object.entries(reaches)
    .map(([name, info]) => `${name} ≈${info.reach.toLocaleString()}`)
    .join(' · ');

  _combineReachLines[patch] = `Patch ${P} — ${parts}`;

  /* Render all available patch lines. */
  const lines = [];
  if (_combineReachLines.a) lines.push(_combineReachLines.a);
  if (_combineReachLines.b) lines.push(_combineReachLines.b);
  textEl.textContent = lines.join('  │  ');
}

/**
 * Open the reach deep-dive modal (Level 3).
 *
 * @returns {void}
 */
function openReachModal() {
  const modal = document.getElementById('reach-modal');
  if (modal) modal.classList.remove('hidden');
}

/**
 * Initialise reach modal close handlers.
 *
 * @returns {void}
 */
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
