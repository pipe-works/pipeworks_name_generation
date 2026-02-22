/*
   walker/controls.js
   Sections 4, 5, 6, 6b, 7, 8, 9:
   spinner/slider controls, profiles, language/radio options, and seed randomizers.
*/

'use strict';

/** @type {{
 *   state: Record<string, any>,
 *   checkPipelineReady: () => void
 * } | null} */
let _ctx = null;

/* Profile presets mirroring WALK_PROFILES from profiles.py */
const PROFILE_PRESETS = {
  clerical: { max_flips: 1, temperature: 0.3, frequency_weight: 1.0 },
  dialect:  { max_flips: 2, temperature: 0.7, frequency_weight: 0.0 },
  goblin:   { max_flips: 2, temperature: 1.5, frequency_weight: -0.5 },
  ritual:   { max_flips: 3, temperature: 2.5, frequency_weight: -1.0 },
};

/**
 * Initialise walker and pipeline form controls.
 *
 * @param {{
 *   state: Record<string, any>,
 *   checkPipelineReady: () => void
 * }} ctx - Shared state and cross-module callbacks.
 * @returns {void}
 */
export function initControls(ctx) {
  _ctx = ctx;
  initSpinners();
  initSliders();
  initWalkConstraintToggles();
  initProfiles();
  initCombinerProfiles();
  initLangOptions();
  initRadioOptions();
  initSeedButtons();
}

/**
 * Apply one on/off toggle state to one spinner-backed constraint input.
 *
 * @param {string} toggleId - Checkbox id that controls the constraint.
 * @param {string} inputId - Numeric input id to enable/disable.
 * @returns {void}
 */
function syncConstraintToggle(toggleId, inputId) {
  const toggle = document.getElementById(toggleId);
  const input = document.getElementById(inputId);
  if (!toggle || !input) return;

  const enabled = !!toggle.checked;
  input.disabled = !enabled;

  /* Disable plus/minus controls for this spinner target when constraint is off. */
  document.querySelectorAll(`.spinner-btn[data-target="${inputId}"]`).forEach(btn => {
    btn.disabled = !enabled;
  });

  const control = input.closest('.spinner-control');
  if (control) control.classList.toggle('is-disabled', !enabled);

  const toggleText = toggle.closest('.constraint-toggle')?.querySelector('.toggle-text');
  if (toggleText) toggleText.textContent = enabled ? 'on' : 'off';
}

/**
 * Wire walk constraint toggles for min/max length and neighbor cap.
 *
 * Disabled state means the corresponding API field is sent as ``null``
 * by the walk operation handler (no runtime constraint).
 *
 * @returns {void}
 */
function initWalkConstraintToggles() {
  const mappings = [
    ['toggle-min-length-a', 'min-length-a'],
    ['toggle-max-length-a', 'max-length-a'],
    ['toggle-neighbors-a', 'neighbors-a'],
    ['toggle-min-length-b', 'min-length-b'],
    ['toggle-max-length-b', 'max-length-b'],
    ['toggle-neighbors-b', 'neighbors-b'],
  ];

  mappings.forEach(([toggleId, inputId]) => {
    const toggle = document.getElementById(toggleId);
    if (!toggle) return;
    toggle.addEventListener('change', () => syncConstraintToggle(toggleId, inputId));
    syncConstraintToggle(toggleId, inputId);
  });
}

/**
 * Wire plus/minus spinner buttons to numeric inputs.
 *
 * @returns {void}
 * Side effects:
 * - Dispatches ``change`` events for target inputs.
 * - Updates walk-step suffix labels.
 * - Re-evaluates pipeline run-button readiness.
 */
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
      document.getElementById('walk-steps-a-suffix').textContent = `-> ${val + 1} syl`;
    }
    if (targetId === 'walk-steps-b') {
      document.getElementById('walk-steps-b-suffix').textContent = `-> ${val + 1} syl`;
    }

    /* Enable pipeline run button if source + output are set */
    _ctx.checkPipelineReady();
  });
}

/**
 * Keep slider readouts synchronized with slider values.
 *
 * @returns {void}
 */
function initSliders() {
  document.querySelectorAll('input[type="range"]').forEach(slider => {
    const valEl = document.getElementById(`${slider.id}-val`);
    if (!valEl) return;
    slider.addEventListener('input', () => {
      valEl.textContent = parseFloat(slider.value).toFixed(1);
    });
  });
}

/**
 * Apply one named profile's parameters to one patch's controls.
 *
 * @param {'a'|'b'|string} patch - Patch key suffix used in control ids.
 * @param {string} profileName - Profile name key from ``PROFILE_PRESETS``.
 * @returns {void}
 */
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

/**
 * Wire walker profile tile selection behavior.
 *
 * @returns {void}
 */
function initProfiles() {
  // Scope strictly to Walk tab profile cards. Combiner uses
  // [data-comb-profile], and pipeline extractor uses [data-extractor].
  document.querySelectorAll('.profile-option[data-profile][data-patch]').forEach(opt => {
    opt.addEventListener('click', () => {
      const patch = opt.dataset.patch;
      if (!patch) return;

      document.querySelectorAll(`.profile-option[data-profile][data-patch="${patch}"]`)
        .forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      const radio = opt.querySelector('input[type="radio"]');
      if (!radio) return;
      radio.checked = true;

      const profileName = radio.value;
      applyProfileToSliders(patch, profileName);
    });
  });
}

/**
 * Initialise combiner profile selection for both Patch A and Patch B.
 *
 * Handles click events on the combiner profile options and toggles visibility
 * of the flat/custom parameter panes based on the selected profile mode.
 *
 * @returns {void}
 */
function initCombinerProfiles() {
  document.querySelectorAll('[data-comb-profile]').forEach(opt => {
    opt.addEventListener('click', () => {
      const patch = opt.dataset.patch;
      const profile = opt.querySelector('input[type="radio"]').value;

      /* Toggle is-selected on sibling profile options */
      document.querySelectorAll(`[data-comb-profile][data-patch="${patch}"]`)
        .forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;

      /* Toggle parameter panel visibility */
      const flatParams   = document.getElementById(`comb-flat-params-${patch}`);
      const customParams = document.getElementById(`comb-custom-params-${patch}`);

      if (profile === 'flat') {
        if (flatParams) flatParams.hidden = false;
        if (customParams) customParams.hidden = true;
      } else if (profile === 'custom') {
        if (flatParams) flatParams.hidden = true;
        if (customParams) customParams.hidden = false;
      } else {
        /* Named profile — hide both panels */
        if (flatParams) flatParams.hidden = true;
        if (customParams) customParams.hidden = true;
      }
    });
  });
}

/**
 * Wire language-selector and extractor-selector controls.
 *
 * @returns {void}
 * Side effects:
 * - Mutates ``state.pipeExtractor``.
 * - Updates extractor badge and language-grid enabled state.
 */
function initLangOptions() {
  document.querySelectorAll('.lang-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.lang-option').forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;
    });
  });

  const syncExtractorUi = extractor => {
    const langGrid = document.getElementById('lang-grid');
    const customLang = document.getElementById('custom-lang');
    if (langGrid) {
      langGrid.style.opacity = extractor === 'nltk' ? '0.4' : '1';
      langGrid.style.pointerEvents = extractor === 'nltk' ? 'none' : '';
    }
    if (customLang) {
      customLang.disabled = extractor === 'nltk';
      if (extractor === 'nltk') {
        customLang.placeholder = 'Disabled for nltk (language is auto)';
      } else {
        customLang.placeholder = 'e.g. sv_SE';
      }
    }
    const badge = document.getElementById('sb-pipe-extractor');
    if (badge) badge.textContent = extractor;
  };

  /* Extractor type — disable lang grid when nltk selected */
  document.querySelectorAll('.profile-option[data-extractor]').forEach(opt => {
    opt.addEventListener('click', () => {
      const extractor = opt.dataset.extractor;
      _ctx.state.pipeExtractor = extractor;
      document.querySelectorAll('.profile-option[data-extractor]')
        .forEach(o => o.classList.remove('is-selected'));
      opt.classList.add('is-selected');
      opt.querySelector('input[type="radio"]').checked = true;
      syncExtractorUi(extractor);
    });
  });

  syncExtractorUi(_ctx.state.pipeExtractor || 'pyphen');
}

/**
 * Wire generic selectable radio-card options.
 *
 * @returns {void}
 */
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

/**
 * Wire seed-randomization controls for walker/combine/selector forms.
 *
 * @returns {void}
 */
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
