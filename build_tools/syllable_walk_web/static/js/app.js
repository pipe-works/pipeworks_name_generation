/*
   app.js
   Entry-point orchestrator for the Pipe-Works Build Tools web application.

   This module owns shared state and boot wiring only. Feature implementations
   live in focused modules under core/, ui/, walker/, and pipeline/.
*/

'use strict';

import { downloadBlob } from './core/files.js';
import { setStatus } from './core/status.js';
import { initPipeline, checkPipelineReady } from './pipeline/pipeline.js';
import { initTheme } from './ui/theme.js';
import { initNavigation, navigateToScreen, updateStatusBarContext } from './ui/navigation.js';
import { initParamInfo } from './ui/param-info.js';
import { initControls } from './walker/controls.js';
import { initCorpus, populateCorpusDropdowns } from './walker/corpus.js';
import { initOperations, populateAnalysis, populateRender } from './walker/operations.js';
import { initReachModule, updateReachValues } from './walker/reach.js';

/* Shared cross-module app state. */
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

/**
 * Initialise application modules in dependency-safe order.
 *
 * @returns {void}
 * Side effects:
 * - Registers all UI and API handlers for the frontend.
 * - Performs boot-time API fetches for version and walker stats.
 */
document.addEventListener('DOMContentLoaded', () => {
  initTheme();

  initOperations({ state, setStatus });
  initNavigation({ state, populateRender, populateAnalysis });
  initReachModule({ setStatus, downloadBlob });
  initCorpus({ state, setStatus, updateReachValues });
  initPipeline({ state, setStatus, populateCorpusDropdowns });
  initControls({ state, checkPipelineReady });
  initParamInfo();

  /* Set initial screen */
  navigateToScreen('pipeline-configure');
  updateStatusBarContext('pipeline');

  /* Populate header version from the package's __version__. */
  fetch('/api/version')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('app-version');
      if (el && data.version) {
        el.textContent = `build tools · v${data.version}`;
      }
    })
    .catch(() => { /* keep fallback text */ });

  /* Fetch initial walker stats from API.
     If the server already has a walker ready (e.g. after a page refresh),
     populate corpus status and reach values without waiting for user actions. */
  fetch('/api/walker/stats')
    .then(r => r.json())
    .then(data => {
      ['a', 'b'].forEach(patch => {
        const info = data[`patch_${patch}`];
        if (!info || !info.corpus) return;
        const P = patch.toUpperCase();
        state[`corpus${P}`] = info.corpus;

        document.getElementById(`status-corpus-${patch}`).textContent = info.corpus;
        const statusEl = document.getElementById(`corpus-status-${patch}`);
        if (!statusEl) return;
        statusEl.classList.remove('is-loaded', 'is-error');

        /* Hydrate all loader states so refresh preserves accurate UX gating/status. */
        if (info.loader_status === 'error' || info.loading_error) {
          statusEl.classList.add('is-error');
          statusEl.textContent = `${info.corpus} · ${info.loading_error || 'walker initialisation failed'}`;
          return;
        }

        if (info.walker_ready || info.loader_status === 'ready') {
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          statusEl.classList.add('is-loaded');
          statusEl.textContent = `${info.corpus} · ${count} syllables · walker ready ✓`;
          if (info.reaches) {
            updateReachValues(patch, info.reaches);
          }
          return;
        }

        if (info.loader_status === 'loading' || info.loading_stage) {
          const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
          const stage = info.loading_stage || 'Loading corpus data';
          statusEl.textContent = `${info.corpus} · ${count} syllables · ${stage}…`;
          return;
        }

        const count = info.syllable_count ? info.syllable_count.toLocaleString() : '?';
        statusEl.textContent = `${info.corpus} · ${count} syllables`;
      });
    })
    .catch(() => { /* ignore */ });

  setStatus('Ready');
});
