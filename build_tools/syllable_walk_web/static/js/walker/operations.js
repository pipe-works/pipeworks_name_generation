/*
   walker/operations.js
   Sections 12-18:
   walk generation, candidate generation, selection, exports, rendering,
   package build, and analysis screen population.
*/

'use strict';

import { downloadBlob } from '../core/files.js';
import { getWalkerSessionLockHolderId } from './corpus.js';

/** @type {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void
 * } | null} */
let _ctx = null;

/**
 * Replace container contents with placeholder text.
 *
 * @param {HTMLElement | null} el - Target container.
 * @param {string} message - Placeholder message.
 * @returns {void}
 */
function setPlaceholder(el, message) {
  if (!el) return;
  el.replaceChildren();
  const span = document.createElement('span');
  span.className = 'placeholder-text';
  span.textContent = message;
  el.appendChild(span);
}

/**
 * Create one meta-line block with key/value spans.
 *
 * @param {string} key - Left label.
 * @param {string} value - Right text value.
 * @param {'meta-val'|'meta-path'} [valueClass='meta-val'] - Value class.
 * @returns {HTMLDivElement}
 */
function createMetaLine(key, value, valueClass = 'meta-val') {
  const row = document.createElement('div');
  const keyEl = document.createElement('span');
  keyEl.className = 'meta-key';
  keyEl.textContent = key;
  const valueEl = document.createElement('span');
  valueEl.className = valueClass;
  valueEl.textContent = value;
  row.append(keyEl, valueEl);
  return row;
}

/**
 * Render a compact walk table as DOM nodes (safe text rendering).
 *
 * @param {Array<{formatted: string, syllables?: string[]}>} walkData - Walk payload.
 * @returns {HTMLTableElement}
 */
function renderWalksTable(walkData) {
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['#', 'Walk', 'Syl'].forEach(label => {
    const th = document.createElement('th');
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  walkData.forEach((w, i) => {
    const tr = document.createElement('tr');
    const indexTd = document.createElement('td');
    indexTd.textContent = String(i + 1);
    const walkTd = document.createElement('td');
    walkTd.textContent = w.formatted || '';
    const sylTd = document.createElement('td');
    sylTd.textContent = String(w.syllables ? w.syllables.length : 0);
    tr.append(indexTd, walkTd, sylTd);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

/**
 * Humanise one API name-class key for selector option labels.
 *
 * @param {string} key - API name class key (e.g. ``first_name``).
 * @returns {string}
 */
function humanizeNameClass(key) {
  return key
    .split('_')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * Initialise all walker operation controls and handlers.
 *
 * @param {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void
 * }} ctx - Shared state and status writer.
 * @returns {void}
 */
export function initOperations(ctx) {
  _ctx = ctx;
  initNameClassOptions();
  initGenerateWalks();
  initExportWalks();
  initGenerateCandidates();
  initSelectNames();
  initExportTxt();
  initRenderScreen();
  initPackageBuild();
}

/**
 * Populate selector class dropdowns from API authority endpoint.
 *
 * @returns {void}
 */
function initNameClassOptions() {
  fetch('/api/walker/name-classes')
    .then(r => r.json())
    .then(data => {
      const classes = Array.isArray(data.classes) ? data.classes : [];
      if (!classes.length) return;

      ['a', 'b'].forEach(patch => {
        const select = document.getElementById(`sel-class-${patch}`);
        if (!select) return;

        const previous = select.value;
        select.replaceChildren();

        classes.forEach(cls => {
          if (!cls || typeof cls.name !== 'string') return;
          const option = document.createElement('option');
          option.value = cls.name;
          option.textContent = humanizeNameClass(cls.name);
          if (typeof cls.description === 'string' && cls.description.length > 0) {
            option.title = cls.description;
          }
          select.appendChild(option);
        });

        const hasPrevious = Array.from(select.options).some(o => o.value === previous);
        if (hasPrevious) {
          select.value = previous;
        } else if (Array.from(select.options).some(o => o.value === 'first_name')) {
          select.value = 'first_name';
        }
      });
    })
    .catch(() => { /* keep existing fallback options */ });
}

/**
 * Wire walk generation buttons.
 *
 * @returns {void}
 */
function initGenerateWalks() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      if (!_ctx.state[`corpus${P}`]) {
        _ctx.setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      const count = parseInt(document.getElementById(`walk-count-${patch}`).value) || 2;
      const steps = parseInt(document.getElementById(`walk-steps-${patch}`).value) || 5;

      /* Read profile */
      const profileEl = document.querySelector(`input[name="profile-${patch}"]:checked`);
      const profile = profileEl ? profileEl.value : 'custom';

      /* Read custom params */
      const temperature = parseFloat(document.getElementById(`temperature-${patch}`)?.value) || 0.7;
      const frequencyWeight = parseFloat(document.getElementById(`freq-weight-${patch}`)?.value) || 0.0;
      const maxFlips = parseInt(document.getElementById(`max-flips-${patch}`)?.value) || 2;
      const minEnabled = document.getElementById(`toggle-min-length-${patch}`)?.checked ?? true;
      const maxEnabled = document.getElementById(`toggle-max-length-${patch}`)?.checked ?? true;
      const neighborsEnabled = document.getElementById(`toggle-neighbors-${patch}`)?.checked ?? true;
      const minParsed = parseInt(document.getElementById(`min-length-${patch}`)?.value, 10);
      const maxParsed = parseInt(document.getElementById(`max-length-${patch}`)?.value, 10);
      const neighborsParsed = parseInt(document.getElementById(`neighbors-${patch}`)?.value, 10);
      const minLength = minEnabled ? (Number.isNaN(minParsed) ? 2 : minParsed) : null;
      const maxLength = maxEnabled ? (Number.isNaN(maxParsed) ? 5 : maxParsed) : null;
      const neighborLimit = neighborsEnabled ? (Number.isNaN(neighborsParsed) ? 10 : neighborsParsed) : null;

      /* Read seed */
      const seedStr = document.getElementById(`seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      if (minLength !== null && minLength < 1) {
        _ctx.setStatus(`Patch ${P}: min length must be >= 1`);
        return;
      }
      if (maxLength !== null && maxLength < 1) {
        _ctx.setStatus(`Patch ${P}: max length must be >= 1`);
        return;
      }
      if (minLength !== null && maxLength !== null && minLength > maxLength) {
        _ctx.setStatus(`Patch ${P}: min length must be <= max length`);
        return;
      }
      if (neighborLimit !== null && neighborLimit < 1) {
        _ctx.setStatus(`Patch ${P}: neighbors must be >= 1`);
        return;
      }

      const out = document.getElementById(`walks-output-${patch}`);
      setPlaceholder(out, 'Generating…');
      btn.disabled = true;
      const holderId = getWalkerSessionLockHolderId();

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
          min_length: minLength,
          max_length: maxLength,
          neighbor_limit: neighborLimit,
          seed: seed,
          lock_holder_id: holderId,
        }),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            setPlaceholder(out, String(data.error));
            _ctx.setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          const walkData = data.walks || [];
          const walks = walkData.map(w => w.formatted);
          _ctx.state[`walks${P}`] = walks;
          _ctx.state[`walkData${P}`] = walkData;

          out.replaceChildren();
          if (!walkData.length) {
            setPlaceholder(out, '(No walks generated)');
          } else {
            out.appendChild(renderWalksTable(walkData));
          }
          _ctx.setStatus(`Patch ${P}: ${walks.length} walk${walks.length !== 1 ? 's' : ''} generated`);
        })
        .catch(err => {
          btn.disabled = false;
          setPlaceholder(out, `Error: ${err.message}`);
          _ctx.setStatus(`Patch ${P}: walk generation failed`);
        });
    });
  });
}

/**
 * Convert walks to a plain-text list.
 *
 * @param {string[]} walks - Formatted walk strings.
 * @returns {string}
 */
function walksToTxt(walks) {
  return walks.map((w, i) => `${i + 1}\t${w}`).join('\n') + '\n';
}

/**
 * Convert walk data to a Markdown table.
 *
 * @param {Array<{formatted: string, syllables?: string[]}>} walkData - Walk payload.
 * @returns {string}
 */
function walksToMd(walkData) {
  const header = '| # | Walk | Syl |\n| ---: | --- | ---: |';
  const rows = walkData.map((w, i) => {
    const sylCount = w.syllables ? w.syllables.length : 0;
    return `| ${i + 1} | ${w.formatted} | ${sylCount} |`;
  });
  return [header, ...rows].join('\n') + '\n';
}

/**
 * Wire walk export/copy buttons.
 *
 * @returns {void}
 */
function initExportWalks() {
  ['a', 'b'].forEach(patch => {
    const P = patch.toUpperCase();

    /* Copy TXT to clipboard */
    document.getElementById(`copy-walks-txt-${patch}`)?.addEventListener('click', () => {
      const walks = _ctx.state[`walks${P}`];
      if (!walks || !walks.length) {
        _ctx.setStatus(`Patch ${P}: no walks to copy — generate walks first`);
        return;
      }
      navigator.clipboard.writeText(walksToTxt(walks)).then(() => {
        _ctx.setStatus(`Patch ${P}: copied ${walks.length} walks as TXT`);
      });
    });

    /* Copy MD to clipboard */
    document.getElementById(`copy-walks-md-${patch}`)?.addEventListener('click', () => {
      const walkData = _ctx.state[`walkData${P}`];
      if (!walkData || !walkData.length) {
        _ctx.setStatus(`Patch ${P}: no walks to copy — generate walks first`);
        return;
      }
      navigator.clipboard.writeText(walksToMd(walkData)).then(() => {
        _ctx.setStatus(`Patch ${P}: copied ${walkData.length} walks as Markdown`);
      });
    });

    /* Export TXT file */
    document.getElementById(`export-walks-txt-${patch}`)?.addEventListener('click', () => {
      const walks = _ctx.state[`walks${P}`];
      if (!walks || !walks.length) {
        _ctx.setStatus(`Patch ${P}: no walks to export — generate walks first`);
        return;
      }
      downloadBlob(walksToTxt(walks), `patch_${patch}_walks.txt`, 'text/plain');
      _ctx.setStatus(`Patch ${P}: exported ${walks.length} walks as TXT`);
    });

    /* Export MD file */
    document.getElementById(`export-walks-md-${patch}`)?.addEventListener('click', () => {
      const walkData = _ctx.state[`walkData${P}`];
      if (!walkData || !walkData.length) {
        _ctx.setStatus(`Patch ${P}: no walks to export — generate walks first`);
        return;
      }
      downloadBlob(walksToMd(walkData), `patch_${patch}_walks.md`, 'text/markdown');
      _ctx.setStatus(`Patch ${P}: exported ${walkData.length} walks as Markdown`);
    });
  });
}

/**
 * Wire candidate generation buttons.
 *
 * @returns {void}
 */
function initGenerateCandidates() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`generate-candidates-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      if (!_ctx.state[`corpus${P}`]) {
        _ctx.setStatus(`Patch ${P}: load a corpus first`);
        return;
      }

      const count = parseInt(document.getElementById(`comb-count-${patch}`).value) || 10000;
      const syllsExact = parseInt(document.getElementById(`comb-syllables-${patch}`).value) || 2;
      const seedStr = document.getElementById(`comb-seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      /* Read selected combiner profile */
      const profileEl = document.querySelector(`input[name="comb-profile-${patch}"]:checked`);
      const profile = profileEl ? profileEl.value : 'flat';

      /* Read syllable mode: "exact" uses the spinner value, "all" generates 2-4 */
      const combMode = document.querySelector(`input[name="comb-mode-${patch}"]:checked`)?.value || 'exact';
      const sylls = combMode === 'all' ? [2, 3, 4] : syllsExact;

      /* Build request body based on profile selection */
      const reqBody = { patch: patch, count: count, syllables: sylls, seed: seed };

      if (profile === 'flat') {
        /* Flat mode: use the flat freq weight slider */
        reqBody.frequency_weight = parseFloat(document.getElementById(`comb-freq-${patch}`)?.value) || 1.0;
      } else if (profile === 'custom') {
        /* Custom mode: send explicit walk parameters */
        reqBody.profile = 'custom';
        reqBody.max_flips = parseInt(document.getElementById(`comb-max-flips-${patch}`)?.value) || 2;
        reqBody.temperature = parseFloat(document.getElementById(`comb-temperature-${patch}`)?.value) || 0.7;
        reqBody.frequency_weight = parseFloat(document.getElementById(`comb-cust-freq-${patch}`)?.value) || 0.0;
      } else {
        /* Named profile: just send the profile name */
        reqBody.profile = profile;
      }

      const out = document.getElementById(`comb-output-${patch}`);
      setPlaceholder(out, 'Generating candidates…');
      btn.disabled = true;
      reqBody.lock_holder_id = getWalkerSessionLockHolderId();

      fetch('/api/walker/combine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            setPlaceholder(out, String(data.error));
            _ctx.setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          /* Store unique count so the selector can use it in "unique" count mode */
          _ctx.state[`uniqueCandidates${P}`] = data.unique || 0;

          out.replaceChildren();
          const syllableSummary = Array.isArray(data.syllables)
            ? data.syllables.join(', ')
            : String(data.syllables || sylls);
          out.appendChild(createMetaLine('generated  ', (data.generated || 0).toLocaleString()));
          out.appendChild(createMetaLine('unique     ', (data.unique || 0).toLocaleString()));
          out.appendChild(createMetaLine('duplicates ', (data.duplicates || 0).toLocaleString()));
          out.appendChild(createMetaLine('syllables  ', syllableSummary));
          out.appendChild(createMetaLine('source     ', String(data.source || _ctx.state[`corpus${P}`]), 'meta-path'));

          _ctx.setStatus(`Patch ${P}: ${(data.unique || 0).toLocaleString()} unique candidates generated`);
        })
        .catch(err => {
          btn.disabled = false;
          setPlaceholder(out, `Error: ${err.message}`);
          _ctx.setStatus(`Patch ${P}: combiner failed`);
        });
    });
  });
}

/**
 * Wire selector execution buttons.
 *
 * @returns {void}
 */
function initSelectNames() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`select-names-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      const cls = document.getElementById(`sel-class-${patch}`)?.value || 'first_name';
      const seedStr = document.getElementById(`sel-seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      /* Read radio selections */
      const countMode = document.querySelector(`input[name="sel-count-mode-${patch}"]:checked`)?.value || 'manual';
      const mode = document.querySelector(`input[name="sel-mode-${patch}"]:checked`)?.value || 'hard';
      const order = document.querySelector(`input[name="sel-order-${patch}"]:checked`)?.value || 'alphabetical';

      /* Resolve count: "unique" uses the unique candidate count from the
       * last combiner run; "manual" uses the spinner value. */
      let count;
      if (countMode === 'unique') {
        count = _ctx.state[`uniqueCandidates${P}`] || parseInt(document.getElementById(`sel-count-${patch}`).value) || 100;
      } else {
        count = parseInt(document.getElementById(`sel-count-${patch}`).value) || 100;
      }

      const metaEl = document.querySelector(`#sel-output-${patch} .selector-output__meta`);
      const listEl = document.getElementById(`sel-names-${patch}`);

      setPlaceholder(metaEl, 'Selecting…');
      listEl.replaceChildren();
      btn.disabled = true;
      const holderId = getWalkerSessionLockHolderId();

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
          lock_holder_id: holderId,
        }),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            setPlaceholder(metaEl, String(data.error));
            _ctx.setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          const names = data.names || [];
          _ctx.state[`names${P}`] = names;

          metaEl.replaceChildren();
          metaEl.appendChild(createMetaLine('selected   ', String(data.count || names.length)));
          metaEl.appendChild(createMetaLine('requested  ', String(data.requested || count)));
          metaEl.appendChild(createMetaLine('class      ', String(data.name_class || cls)));
          metaEl.appendChild(createMetaLine('patch      ', P, 'meta-path'));

          listEl.replaceChildren();
          names.forEach(name => {
            const nameEl = document.createElement('span');
            nameEl.className = 'name-item';
            nameEl.textContent = name;
            listEl.appendChild(nameEl);
          });
          _ctx.setStatus(`Patch ${P}: ${names.length} names selected`);
        })
        .catch(err => {
          btn.disabled = false;
          setPlaceholder(metaEl, `Error: ${err.message}`);
          _ctx.setStatus(`Patch ${P}: selector failed`);
        });
    });
  });
}

/**
 * Wire simple TXT export buttons for selected names.
 *
 * @returns {void}
 */
function initExportTxt() {
  ['a', 'b'].forEach(patch => {
    const btn = document.getElementById(`export-txt-${patch}`);
    if (!btn) return;
    btn.addEventListener('click', () => {
      const P = patch.toUpperCase();
      const names = _ctx.state[`names${P}`];
      if (!names || !names.length) {
        _ctx.setStatus(`Patch ${P}: no names to export — select names first`);
        return;
      }
      const blob = new Blob([names.join('\n') + '\n'], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `patch_${patch}_names.txt`;
      a.click();
      URL.revokeObjectURL(url);
      _ctx.setStatus(`Patch ${P}: exported ${names.length} names`);
    });
  });
}

/**
 * Initialise render-screen controls.
 *
 * @returns {void}
 */
function initRenderScreen() {
  const combineToggle = document.getElementById('render-combine');
  const styleSelect = document.getElementById('render-style');
  const combinedCol = document.getElementById('render-combined-col');

  combineToggle?.addEventListener('change', () => {
    combinedCol.style.display = combineToggle.checked ? '' : 'none';
    populateRender();
  });

  styleSelect?.addEventListener('change', populateRender);
}

/**
 * Render selected names into the Render screen.
 *
 * @returns {void}
 */
export function populateRender() {
  const style = document.getElementById('render-style')?.value || 'title';
  const combine = document.getElementById('render-combine')?.checked || false;

  function applyStyle(name) {
    if (style === 'upper') return name.toUpperCase();
    if (style === 'lower') return name.toLowerCase();
    return name.charAt(0).toUpperCase() + name.slice(1);
  }

  ['a', 'b'].forEach(patch => {
    const P = patch.toUpperCase();
    const names = _ctx.state[`names${P}`];
    const el = document.getElementById(`render-names-${patch}`);
    if (!el) return;
    if (!names || !names.length) {
      setPlaceholder(el, '(Select names in the Walk screen first)');
      return;
    }
    el.replaceChildren();
    names.forEach(name => {
      const nameEl = document.createElement('span');
      nameEl.className = 'render-name';
      nameEl.textContent = applyStyle(name);
      el.appendChild(nameEl);
    });
  });

  if (combine) {
    const el = document.getElementById('render-names-combined');
    if (!el) return;
    const A = _ctx.state.namesA || [];
    const B = _ctx.state.namesB || [];
    if (!A.length || !B.length) {
      setPlaceholder(el, '(Select names for both patches first)');
      return;
    }
    const combined = A.slice(0, Math.min(A.length, B.length))
      .map((a, i) => `${applyStyle(a)} ${applyStyle(B[i])}`);
    el.replaceChildren();
    combined.forEach(name => {
      const nameEl = document.createElement('span');
      nameEl.className = 'render-name';
      nameEl.textContent = name;
      el.appendChild(nameEl);
    });
  }
}

/**
 * Wire package build/download action.
 *
 * @returns {void}
 */
function initPackageBuild() {
  const btn = document.getElementById('build-package');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const name = document.getElementById('pkg-name').value || 'my-corpus-package';
    const version = document.getElementById('pkg-version').value || '0.1.0';
    const out = document.getElementById('pkg-output');

    const body = {
      name,
      version,
      include_walks_a: document.getElementById('pkg-walks-a')?.checked ?? true,
      include_walks_b: document.getElementById('pkg-walks-b')?.checked ?? true,
      include_candidates: document.getElementById('pkg-candidates')?.checked ?? true,
      include_selections: document.getElementById('pkg-selections')?.checked ?? true,
      lock_holder_id: getWalkerSessionLockHolderId(),
    };

    setPlaceholder(out, 'Building package…');
    btn.disabled = true;
    _ctx.setStatus('Building package…');

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
          out.replaceChildren();
          out.textContent = [
            `${filename}  (${kb} KB)`,
            ``,
            `built: ${now}`,
            `version: ${version}`,
          ].join('\n');
          _ctx.setStatus(`Package "${filename}" downloaded`);
        });
      })
      .catch(err => {
        out.replaceChildren();
        out.textContent = `Error: ${err.message}`;
        _ctx.setStatus(`Package failed: ${err.message}`);
      })
      .finally(() => { btn.disabled = false; });
  });
}

/**
 * Populate the analysis screen for loaded patch corpora.
 *
 * @returns {void}
 */
export function populateAnalysis() {
  ['a', 'b'].forEach(patch => {
    const P = patch.toUpperCase();
    const corpus = _ctx.state[`corpus${P}`];
    const hint = document.getElementById(`analysis-hint-${patch}`);

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
        const lenIds = ['2', '3', '4', '5'];
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
          if (labelEl) {
            labelEl.replaceChildren();
            const labelText = document.createElement('span');
            labelText.textContent = `${t.label} `;
            const scoreText = document.createElement('span');
            scoreText.className = 'u-accent';
            scoreText.textContent = `${sign}${t.score.toFixed(3)}`;
            labelEl.append(labelText, scoreText);
          }
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
