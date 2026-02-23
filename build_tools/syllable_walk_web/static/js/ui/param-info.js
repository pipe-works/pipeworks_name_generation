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
    tooltip: 'ON enforces a minimum start/transition syllable length; OFF removes this runtime bound (null).',
    modal: {
      title: 'Min Length (chars)',
      rows: [
        ['Definition',
         'Minimum character length accepted during random start pick and each transition.'],
        ['Toggle (ON/OFF)',
         '<ul>' +
         '<li>ON: sends numeric <code>min_length</code> to the API.</li>' +
         '<li>OFF: sends <code>min_length = null</code> (constraint disabled).</li>' +
         '</ul>'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Filters out short syllables at runtime.</li>' +
         '<li>Can narrow available transitions.</li>' +
         '<li>May increase repetition when options are sparse.</li>' +
         '</ul>'],
        ['Deterministic vs Stochastic',
         '<ul>' +
         '<li>Toggle state deterministically changes the allowed candidate space.</li>' +
         '<li>Sampling within that space is still stochastic unless seed is fixed.</li>' +
         '</ul>'],
        ['Interpretation',
         '<ul>' +
         '<li>Lower min length \u2192 broader candidate pool.</li>' +
         '<li>Higher min length \u2192 stricter lexical floor.</li>' +
         '</ul>'],
        ['Scope',
         'This is a runtime candidate filter, not a corpus rewrite step.'],
      ],
    },
  },
  'max-length': {
    signal: 'max chars',
    tooltip: 'ON enforces a maximum start/transition syllable length; OFF removes this runtime bound (null).',
    modal: {
      title: 'Max Length (chars)',
      rows: [
        ['Definition',
         'Upper character-length bound applied during start pick and each walk step.'],
        ['Toggle (ON/OFF)',
         '<ul>' +
         '<li>ON: sends numeric <code>max_length</code> to the API.</li>' +
         '<li>OFF: sends <code>max_length = null</code> (constraint disabled).</li>' +
         '</ul>'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Excludes longer syllables from candidate selection.</li>' +
         '<li>Can simplify walk output rhythm.</li>' +
         '<li>May reduce transition diversity when set low.</li>' +
         '</ul>'],
        ['Deterministic vs Stochastic',
         '<ul>' +
         '<li>Toggle state deterministically reshapes the reachable candidate set per step.</li>' +
         '<li>Transition choice remains probabilistic unless seed is fixed.</li>' +
         '</ul>'],
        ['Interpretation',
         '<ul>' +
         '<li>Lower max length \u2192 tighter brevity constraints.</li>' +
         '<li>Higher max length \u2192 broader candidate pool.</li>' +
         '</ul>'],
        ['Scope',
         'Constraint is enforced at walk-time, not by rebuilding the corpus graph.'],
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
    tooltip: 'ON applies a per-step neighbour cap; OFF removes the cap and evaluates the full precomputed list.',
    modal: {
      title: 'Neighbors (max)',
      rows: [
        ['Definition',
         'Limits per-step neighbor evaluation to the first N entries from the precomputed list.'],
        ['Toggle (ON/OFF)',
         '<ul>' +
         '<li>ON: sends numeric <code>neighbor_limit</code> to the API.</li>' +
         '<li>OFF: sends <code>neighbor_limit = null</code> (no cap).</li>' +
         '</ul>'],
        ['Effect on Structure',
         '<ul>' +
         '<li>Lower cap narrows branching during sampling.</li>' +
         '<li>Higher cap exposes more transition options.</li>' +
         '<li>Can materially change walk outcomes and diversity.</li>' +
         '</ul>'],
        ['Deterministic vs Stochastic',
         '<ul>' +
         '<li>Cap setting deterministically constrains the branch surface.</li>' +
         '<li>Actual next-step selection is stochastic probability sampling.</li>' +
         '<li>With fixed seed + same settings, walk output is reproducible.</li>' +
         '</ul>'],
      ],
    },
  },
  'rebuild-reach-cache': {
    signal: 'cache health',
    tooltip: 'Use when Reach Cache IPC is mismatch/missing/error, or after manual run-directory edits. Rebuild recomputes reaches and rewrites IPC sidecar hashes.',
    modal: {
      title: 'Rebuild Reach Cache',
      rows: [
        ['Definition',
         'Recomputes all profile reach tables (clerical/dialect/goblin/ritual) for the currently loaded patch corpus and rewrites the run-local cache artifact.'],
        ['When to Rebuild',
         '<ul>' +
         '<li>Reach Cache IPC badge is <code>mismatch</code>, <code>missing</code>, or <code>error</code>.</li>' +
         '<li>Run directory artifacts were edited manually.</li>' +
         '<li>You want to repair/refresh cache integrity before comparing Patch A and B outputs.</li>' +
         '</ul>'],
        ['When Not Needed',
         '<ul>' +
         '<li>Reach Cache IPC is <code>verified</code> and corpus content has not changed.</li>' +
         '<li>You only changed runtime walk controls (seed, walk count, temperature, etc.).</li>' +
         '</ul>'],
        ['IPC Effects',
         '<ul>' +
         '<li>Writes <code>&lt;run_dir&gt;/ipc/walker_profile_reaches.v1.json</code>.</li>' +
         '<li>Refreshes cache <code>ipc.input_hash</code> and <code>ipc.output_hash</code> in UI/API.</li>' +
         '<li>Does not mutate corpus syllables or manifest payload; it updates reach-cache sidecar provenance.</li>' +
         '</ul>'],
        ['Deterministic vs Stochastic',
         '<ul>' +
         '<li>Rebuild is deterministic for a fixed corpus + walker graph/reach settings.</li>' +
         '<li>Walk generation remains stochastic unless seed is fixed.</li>' +
         '</ul>'],
        ['Operational Note',
         'Rebuild is patch-local. Rebuild Patch A and Patch B independently if both show non-verified cache states.'],
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
