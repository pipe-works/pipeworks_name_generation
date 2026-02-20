(function () {
  const previewState = {
    inlineEntries: [],
    comboEntries: [],
    liveEntry: null,
    liveIndex: -1,
  };
  // Live preview helpers are split into their own file so the main app logic
  // can remain focused on data fetching and API composition.
  // Update a preview container with a simple text message and styling tone.
  function setText(el, text, className) {
    if (!el) {
      return;
    }
    el.className = className;
    el.textContent = text;
  }

  // Clear all child nodes to prepare a container for new content.
  function clearElement(el) {
    while (el && el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  // Render a single group of names as table rows with a group header.
  function buildGroup(tbody, label, entries) {
    const headerRow = document.createElement('tr');
    headerRow.className = 'preview-table__group-header';
    const headerCell = document.createElement('td');
    headerCell.textContent = label;
    headerRow.appendChild(headerCell);
    tbody.appendChild(headerRow);

    if (!entries.length) {
      const emptyRow = document.createElement('tr');
      const emptyCell = document.createElement('td');
      emptyCell.className = 'muted';
      emptyCell.textContent = 'No names returned.';
      emptyRow.appendChild(emptyCell);
      tbody.appendChild(emptyRow);
      return;
    }

    for (const entry of entries) {
      const row = document.createElement('tr');
      row.className = 'preview-table__row';
      const cell = document.createElement('td');
      cell.textContent = entry.name;
      row.appendChild(cell);
      row.addEventListener('click', () => setLivePreview(entry));
      tbody.appendChild(row);
    }
  }

  // Render the multi-group inline preview as a table (one group per selection).
  function renderGroups(container, groups) {
    if (!container) {
      return;
    }
    clearElement(container);
    if (!groups.length) {
      setText(container, 'No preview generated yet.', 'api-builder-preview-list muted');
      previewState.inlineEntries = [];
      return;
    }
    container.className = 'api-builder-preview-list';
    previewState.inlineEntries = [];

    const table = document.createElement('table');
    table.className = 'preview-table';
    const tbody = document.createElement('tbody');

    for (const group of groups) {
      buildGroup(tbody, group.label, group.entries);
      previewState.inlineEntries.push(...group.entries);
    }

    table.appendChild(tbody);
    container.appendChild(table);
  }

  // Render a two-column table of First + Last combinations with summary metadata.
  function renderCombo(container, combos, summary) {
    if (!container) {
      return;
    }
    clearElement(container);
    if (!combos.length) {
      setText(
        container,
        'Need at least one First Name and one Last Name selection to build combinations.',
        'api-builder-preview-list muted'
      );
      previewState.comboEntries = [];
      return;
    }
    container.className = 'api-builder-preview-list';
    previewState.comboEntries = combos.slice();

    const table = document.createElement('table');
    table.className = 'preview-table';

    const thead = document.createElement('thead');
    const summaryRow = document.createElement('tr');
    summaryRow.className = 'preview-table__group-header';
    const summaryCell = document.createElement('td');
    summaryCell.colSpan = 2;
    summaryCell.textContent = summary;
    summaryRow.appendChild(summaryCell);
    thead.appendChild(summaryRow);

    const headerRow = document.createElement('tr');
    for (const label of ['First', 'Last']) {
      const th = document.createElement('th');
      th.textContent = label;
      headerRow.appendChild(th);
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    for (const combo of combos) {
      const row = document.createElement('tr');
      row.className = 'preview-table__row';
      const parts = combo.name.split(' ');
      const firstCell = document.createElement('td');
      firstCell.textContent = parts[0] || '';
      const lastCell = document.createElement('td');
      lastCell.textContent = parts.slice(1).join(' ') || '';
      row.appendChild(firstCell);
      row.appendChild(lastCell);
      row.addEventListener('click', () => setLivePreview(combo));
      tbody.appendChild(row);
    }
    table.appendChild(tbody);
    container.appendChild(table);
  }

  // Apply a render style transform to a name for live preview display.
  function transformName(name, style) {
    switch (style) {
      case 'lower': return name.toLowerCase();
      case 'upper': return name.toUpperCase();
      case 'title': return name.replace(/\b\w/g, (c) => c.toUpperCase());
      case 'sentence': return name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();
      default: return name;
    }
  }

  // Read the current render style from the Live Preview dropdown.
  function getPreviewRenderStyle() {
    const el = document.getElementById('preview-render-style');
    return el ? el.value : 'raw';
  }

  // Build a flat list of all navigable entries across both tables.
  function getAllEntries() {
    return [...previewState.inlineEntries, ...previewState.comboEntries];
  }

  // Update nav button enabled state and position indicator.
  function updateNavControls() {
    const prevBtn = document.getElementById('api-builder-live-prev-btn');
    const nextBtn = document.getElementById('api-builder-live-next-btn');
    const posEl = document.getElementById('api-builder-live-nav-pos');
    const all = getAllEntries();
    const idx = previewState.liveIndex;

    if (prevBtn) prevBtn.disabled = idx <= 0;
    if (nextBtn) nextBtn.disabled = idx < 0 || idx >= all.length - 1;
    if (posEl) {
      posEl.textContent = idx >= 0 && all.length ? `${idx + 1} / ${all.length}` : '';
    }
  }

  // Update the live preview output when a row is clicked.
  function setLivePreview(entry) {
    const output = document.getElementById('api-builder-live-output');
    if (!output) {
      return;
    }
    output.classList.remove('muted');
    output.textContent = transformName(entry.name, getPreviewRenderStyle());
    previewState.liveEntry = entry;

    // Resolve index in the combined entry list.
    const all = getAllEntries();
    const idx = all.indexOf(entry);
    previewState.liveIndex = idx >= 0 ? idx : -1;
    updateNavControls();
  }

  // Navigate the live preview by a signed delta (-1 = prev, +1 = next).
  function navigateLive(delta) {
    const all = getAllEntries();
    if (!all.length) {
      return;
    }
    let idx = previewState.liveIndex + delta;
    if (idx < 0) idx = 0;
    if (idx >= all.length) idx = all.length - 1;
    if (idx === previewState.liveIndex) {
      return;
    }
    setLivePreview(all[idx]);
  }

  // Restore the live preview placeholder text.
  function resetLivePreview() {
    const output = document.getElementById('api-builder-live-output');
    if (!output) {
      return;
    }
    output.classList.add('muted');
    output.textContent = 'No selection focused yet.';
    previewState.liveEntry = null;
    previewState.liveIndex = -1;
    updateNavControls();
  }

  // Apply font controls to the live preview output so users can
  // experiment with renderer styling before making API calls.
  function applyPreviewStyles() {
    const output = document.getElementById('api-builder-live-output');
    const fontSelect = document.getElementById('preview-font-family');
    const sizeInput = document.getElementById('preview-font-size');
    const weightInput = document.getElementById('preview-font-weight');
    const italicInput = document.getElementById('preview-font-italic');
    const sizeValue = document.getElementById('preview-font-size-value');
    const weightValue = document.getElementById('preview-font-weight-value');
    if (!output || !fontSelect || !sizeInput || !weightInput || !italicInput) {
      return;
    }
    const size = Number(sizeInput.value || '22');
    const weight = Number(weightInput.value || '500');

    sizeValue.textContent = `${size}px`;
    weightValue.textContent = String(weight);

    const fallback =
      fontSelect.selectedOptions[0]?.dataset.fallback ||
      fontSelect.getAttribute('data-fallback') ||
      'serif';
    output.style.fontFamily = `"${fontSelect.value}", ${fallback}`;
    output.style.fontSize = `${size}px`;
    output.style.fontWeight = String(weight);
    output.style.fontStyle = italicInput.checked ? 'italic' : 'normal';
  }

  // Hook up font and render control listeners once the DOM is ready.
  function initPreviewControls() {
    const fontSelect = document.getElementById('preview-font-family');
    const sizeInput = document.getElementById('preview-font-size');
    const weightInput = document.getElementById('preview-font-weight');
    const italicInput = document.getElementById('preview-font-italic');
    if (!fontSelect || !sizeInput || !weightInput || !italicInput) {
      return;
    }
    applyPreviewStyles();
    fontSelect.addEventListener('change', applyPreviewStyles);
    sizeInput.addEventListener('input', applyPreviewStyles);
    weightInput.addEventListener('input', applyPreviewStyles);
    italicInput.addEventListener('change', applyPreviewStyles);

    const renderSelect = document.getElementById('preview-render-style');
    if (renderSelect) {
      renderSelect.addEventListener('change', () => {
        if (previewState.liveEntry) {
          const output = document.getElementById('api-builder-live-output');
          if (output) {
            output.textContent = transformName(
              previewState.liveEntry.name,
              renderSelect.value
            );
          }
        }
      });
    }
  }

  async function copyNames(button, entries, emptyMessage) {
    if (!entries.length) {
      button.textContent = emptyMessage;
      button.classList.add('err');
      window.setTimeout(() => {
        button.classList.remove('err');
        button.textContent = 'Copy';
      }, 1200);
      return;
    }
    try {
      await navigator.clipboard.writeText(entries.map((entry) => entry.name).join('\n'));
      button.textContent = 'Copied';
      button.classList.add('ok');
    } catch (_error) {
      button.textContent = 'Copy failed';
      button.classList.add('err');
    }
    window.setTimeout(() => {
      button.classList.remove('ok', 'err');
      button.textContent = 'Copy';
    }, 1400);
  }

  function initCopyButtons() {
    const inlineCopy = document.getElementById('api-builder-inline-copy-btn');
    const comboCopy = document.getElementById('api-builder-combo-copy-btn');
    const inlineExport = document.getElementById('api-builder-inline-export-btn');
    const comboExport = document.getElementById('api-builder-combo-export-btn');
    if (inlineCopy) {
      inlineCopy.addEventListener('click', () => {
        copyNames(inlineCopy, previewState.inlineEntries, 'No names');
      });
    }
    if (comboCopy) {
      comboCopy.addEventListener('click', () => {
        copyNames(comboCopy, previewState.comboEntries, 'No combos');
      });
    }
    if (inlineExport) {
      inlineExport.addEventListener('click', () => {
        if (
          window.PipeworksApiBuilder &&
          typeof window.PipeworksApiBuilder.exportNames === 'function'
        ) {
          // Prefer full-count exports when the API Builder helper is available.
          window.PipeworksApiBuilder.exportNames('inline');
          return;
        }
        // Fallback: export only the names currently rendered in the preview.
        downloadNames(inlineExport, previewState.inlineEntries, 'No names');
      });
    }
    if (comboExport) {
      comboExport.addEventListener('click', () => {
        if (
          window.PipeworksApiBuilder &&
          typeof window.PipeworksApiBuilder.exportNames === 'function'
        ) {
          // Prefer full-count exports when the API Builder helper is available.
          window.PipeworksApiBuilder.exportNames('combo');
          return;
        }
        // Fallback: export only the combinations currently rendered in the preview.
        downloadNames(comboExport, previewState.comboEntries, 'No combos');
      });
    }
  }

  function formatTimestamp(now) {
    const pad = (value) => String(value).padStart(2, '0');
    return [
      now.getFullYear(),
      pad(now.getMonth() + 1),
      pad(now.getDate()),
      '_',
      pad(now.getHours()),
      pad(now.getMinutes()),
      pad(now.getSeconds()),
    ].join('');
  }

  function downloadNames(button, entries, emptyMessage) {
    if (!entries.length) {
      button.textContent = emptyMessage;
      button.classList.add('err');
      window.setTimeout(() => {
        button.classList.remove('err');
        button.textContent = 'Export TXT';
      }, 1200);
      return;
    }
    const content = entries.map((entry) => entry.name).join('\n') + '\n';
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pipeworks_names_${formatTimestamp(new Date())}.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    button.textContent = 'Exported';
    button.classList.add('ok');
    window.setTimeout(() => {
      button.classList.remove('ok');
      button.textContent = 'Export TXT';
    }, 1400);
  }

  // Expose a minimal interface for the main app script to use.
  window.PipeworksPreview = {
    renderInline(groups) {
      const container = document.getElementById('api-builder-inline-preview');
      renderGroups(container, groups);
    },
    renderCombinations(combos, summary) {
      const container = document.getElementById('api-builder-combo-preview');
      renderCombo(container, combos, summary);
    },
    setInlineMessage(message, tone) {
      const container = document.getElementById('api-builder-inline-preview');
      setText(container, message, `api-builder-preview-list ${tone || 'muted'}`);
      previewState.inlineEntries = [];
    },
    setComboMessage(message, tone) {
      const container = document.getElementById('api-builder-combo-preview');
      setText(container, message, `api-builder-preview-list ${tone || 'muted'}`);
      previewState.comboEntries = [];
    },
    resetLivePreview,
    setLivePreview,
    navigateLive,
    getInlineEntries() {
      return previewState.inlineEntries.slice();
    },
    getComboEntries() {
      return previewState.comboEntries.slice();
    },
    getLiveEntry() {
      return previewState.liveEntry;
    },
  };

  function initLiveNav() {
    const prevBtn = document.getElementById('api-builder-live-prev-btn');
    const nextBtn = document.getElementById('api-builder-live-next-btn');
    if (prevBtn) {
      prevBtn.addEventListener('click', () => navigateLive(-1));
    }
    if (nextBtn) {
      nextBtn.addEventListener('click', () => navigateLive(1));
    }
    document.addEventListener('keydown', (e) => {
      // Only respond when no input/textarea/select is focused.
      const tag = (e.target && e.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
        return;
      }
      if (e.key === 'h') {
        navigateLive(-1);
      } else if (e.key === 'l') {
        navigateLive(1);
      }
    });
    updateNavControls();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initPreviewControls();
      initCopyButtons();
      initLiveNav();
    });
  } else {
    initPreviewControls();
    initCopyButtons();
    initLiveNav();
  }
})();
