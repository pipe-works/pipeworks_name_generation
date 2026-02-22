/*
   walker/operations.js
   Sections 12-18:
   walk generation, candidate generation, selection, exports, rendering,
   package build, and analysis screen population.
*/

'use strict';

import { downloadBlob } from '../core/files.js';

/** @type {{
 *   state: Record<string, any>,
 *   setStatus: (msg: string) => void
 * } | null} */
let _ctx = null;

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
  initGenerateWalks();
  initExportWalks();
  initGenerateCandidates();
  initSelectNames();
  initExportTxt();
  initRenderScreen();
  initPackageBuild();
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
      const minLength = parseInt(document.getElementById(`min-length-${patch}`)?.value) || 2;
      const maxLength = parseInt(document.getElementById(`max-length-${patch}`)?.value) || 5;
      const neighborLimit = parseInt(document.getElementById(`neighbors-${patch}`)?.value) || 10;

      /* Read seed */
      const seedStr = document.getElementById(`seed-${patch}`)?.value;
      const seed = seedStr ? parseInt(seedStr, 16) : null;

      if (minLength < 1 || maxLength < 1) {
        _ctx.setStatus(`Patch ${P}: min/max length must be >= 1`);
        return;
      }
      if (minLength > maxLength) {
        _ctx.setStatus(`Patch ${P}: min length must be <= max length`);
        return;
      }
      if (neighborLimit < 1) {
        _ctx.setStatus(`Patch ${P}: neighbors must be >= 1`);
        return;
      }

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
          min_length: minLength,
          max_length: maxLength,
          neighbor_limit: neighborLimit,
          seed: seed,
        }),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            out.innerHTML = `<span class="placeholder-text">${data.error}</span>`;
            _ctx.setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          const walkData = data.walks || [];
          const walks = walkData.map(w => w.formatted);
          _ctx.state[`walks${P}`] = walks;
          _ctx.state[`walkData${P}`] = walkData;

          out.innerHTML = renderWalksTable(walkData);
          _ctx.setStatus(`Patch ${P}: ${walks.length} walk${walks.length !== 1 ? 's' : ''} generated`);
        })
        .catch(err => {
          btn.disabled = false;
          out.innerHTML = `<span class="placeholder-text">Error: ${err.message}</span>`;
          _ctx.setStatus(`Patch ${P}: walk generation failed`);
        });
    });
  });
}

/**
 * Render walk results into a compact table.
 *
 * @param {Array<{formatted: string, syllables?: string[]}>} walkData - Walk payload.
 * @returns {string}
 */
function renderWalksTable(walkData) {
  if (!walkData || !walkData.length) return '';
  const rows = walkData.map((w, i) => {
    const sylCount = w.syllables ? w.syllables.length : 0;
    return `<tr><td>${i + 1}</td><td>${w.formatted}</td><td>${sylCount}</td></tr>`;
  }).join('');
  return `<table><thead><tr><th>#</th><th>Walk</th><th>Syl</th></tr></thead><tbody>${rows}</tbody></table>`;
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
      out.innerHTML = '<span class="placeholder-text">Generating candidates…</span>';
      btn.disabled = true;

      fetch('/api/walker/combine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody),
      })
        .then(r => r.json())
        .then(data => {
          btn.disabled = false;
          if (data.error) {
            out.innerHTML = `<span class="placeholder-text">${data.error}</span>`;
            _ctx.setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          /* Store unique count so the selector can use it in "unique" count mode */
          _ctx.state[`uniqueCandidates${P}`] = data.unique || 0;

          out.innerHTML = [
            `<span class="meta-key">generated  </span><span class="meta-val">${(data.generated || 0).toLocaleString()}</span>`,
            `<span class="meta-key">unique     </span><span class="meta-val">${(data.unique || 0).toLocaleString()}</span>`,
            `<span class="meta-key">duplicates </span><span class="meta-val">${(data.duplicates || 0).toLocaleString()}</span>`,
            `<span class="meta-key">syllables  </span><span class="meta-val">${Array.isArray(data.syllables) ? data.syllables.join(', ') : (data.syllables || sylls)}</span>`,
            `<span class="meta-key">source     </span><span class="meta-path">${data.source || _ctx.state[`corpus${P}`]}</span>`,
          ].join('<br/>');

          _ctx.setStatus(`Patch ${P}: ${(data.unique || 0).toLocaleString()} unique candidates generated`);
        })
        .catch(err => {
          btn.disabled = false;
          out.innerHTML = `<span class="placeholder-text">Error: ${err.message}</span>`;
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
            _ctx.setStatus(`Patch ${P}: ${data.error}`);
            return;
          }

          const names = data.names || [];
          _ctx.state[`names${P}`] = names;

          metaEl.innerHTML = [
            `<span class="meta-key">selected   </span><span class="meta-val">${data.count || names.length}</span>`,
            `<span class="meta-key">requested  </span><span class="meta-val">${data.requested || count}</span>`,
            `<span class="meta-key">class      </span><span class="meta-val">${data.name_class || cls}</span>`,
            `<span class="meta-key">patch      </span><span class="meta-path">${P}</span>`,
          ].join('<br/>');

          listEl.innerHTML = names.map(n => `<span class="name-item">${n}</span>`).join('');
          _ctx.setStatus(`Patch ${P}: ${names.length} names selected`);
        })
        .catch(err => {
          btn.disabled = false;
          metaEl.innerHTML = `<span class="placeholder-text">Error: ${err.message}</span>`;
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
      el.innerHTML = '<p class="placeholder-text">(Select names in the Walk screen first)</p>';
      return;
    }
    el.innerHTML = names.map(n => `<span class="render-name">${applyStyle(n)}</span>`).join('');
  });

  if (combine) {
    const el = document.getElementById('render-names-combined');
    if (!el) return;
    const A = _ctx.state.namesA || [];
    const B = _ctx.state.namesB || [];
    if (!A.length || !B.length) {
      el.innerHTML = '<p class="placeholder-text">(Select names for both patches first)</p>';
      return;
    }
    const combined = A.slice(0, Math.min(A.length, B.length))
      .map((a, i) => `${applyStyle(a)} ${applyStyle(B[i])}`);
    el.innerHTML = combined.map(n => `<span class="render-name">${n}</span>`).join('');
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
    };

    out.innerHTML = '<span class="placeholder-text">Building package…</span>';
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
          out.innerHTML = '';
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
        out.innerHTML = '';
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
