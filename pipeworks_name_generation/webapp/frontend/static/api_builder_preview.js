(function () {
  const previewState = {
    inlineEntries: [],
    comboEntries: [],
    liveEntry: null,
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

  // Clear all child nodes to prepare a container for new preview chips.
  function clearElement(el) {
    while (el && el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  // Render a single group of names with a label and clickable chips.
  function buildGroup(container, label, entries) {
    const group = document.createElement('div');
    group.className = 'api-builder-preview-group';

    const title = document.createElement('div');
    title.className = 'api-builder-preview-group-title';
    title.textContent = label;
    group.appendChild(title);

    const row = document.createElement('div');
    row.className = 'api-builder-preview-chip-row';

    if (!entries.length) {
      const empty = document.createElement('span');
      empty.className = 'muted';
      empty.textContent = 'No names returned.';
      row.appendChild(empty);
    } else {
      for (const entry of entries) {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'api-builder-preview-chip';
        chip.textContent = entry.name;
        chip.addEventListener('click', () => {
          setLivePreview(entry);
        });
        row.appendChild(chip);
      }
    }

    group.appendChild(row);
    container.appendChild(group);
  }

  // Render the multi-group inline preview (one group per selection).
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
    for (const group of groups) {
      buildGroup(container, group.label, group.entries);
      previewState.inlineEntries.push(...group.entries);
    }
  }

  // Render a flattened list of First + Last combinations with summary metadata.
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
    const group = document.createElement('div');
    group.className = 'api-builder-preview-group';

    const title = document.createElement('div');
    title.className = 'api-builder-preview-group-title';
    title.textContent = summary;
    group.appendChild(title);

    const row = document.createElement('div');
    row.className = 'api-builder-preview-chip-row';
    for (const combo of combos) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'api-builder-preview-chip';
      chip.textContent = combo.name;
      chip.addEventListener('click', () => {
        setLivePreview(combo);
      });
      row.appendChild(chip);
    }
    group.appendChild(row);
    container.appendChild(group);
  }

  // Update the live preview output when a chip is clicked.
  function setLivePreview(entry) {
    const output = document.getElementById('api-builder-live-output');
    if (!output) {
      return;
    }
    output.classList.remove('muted');
    output.textContent = entry.name;
    previewState.liveEntry = entry;
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

  // Hook up font control listeners once the DOM is ready.
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initPreviewControls();
      initCopyButtons();
    });
  } else {
    initPreviewControls();
    initCopyButtons();
  }
})();
