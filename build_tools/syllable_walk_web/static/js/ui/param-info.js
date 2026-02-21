/*
   ui/param-info.js
   Section 23: parameter information tooltips and modals.
*/

'use strict';

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
export function initParamInfo() {
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
