    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    const tabs = Array.from(document.querySelectorAll('.tab'));
    const panels = {
      generation: document.getElementById('panel-generation'),
      database: document.getElementById('panel-database'),
      favorites: document.getElementById('panel-favorites'),
      help: document.getElementById('panel-help'),
    };

    const dbState = {
      tableId: null,
      offset: 0,
      limit: 20,
      total: 0,
      packageId: null,
    };
    const generationCardKeys = [
      'first_name',
      'last_name',
      'place_name',
      'location_name',
      'object_item',
      'organisation',
      'title_epithet',
    ];
    const generationCardLabels = {
      first_name: 'First Name',
      last_name: 'Last Name',
      place_name: 'Place Name',
      location_name: 'Location Name',
      object_item: 'Object Item',
      organisation: 'Organisation',
      title_epithet: 'Title Epithet',
    };
    const apiBuilderSelections = [];
    const apiBuilderPreviewState = {
      curlText: '',
      postText: '',
    };
    let generationCardsCollapsed = true;
    let selectionPaneCollapsed = false;
    const themeStorageKey = 'pipeworks-theme';

    function setActiveTab(tabName) {
      for (const tab of tabs) {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
      }
      for (const [name, panel] of Object.entries(panels)) {
        panel.classList.toggle('active', name === tabName);
      }
    }

    for (const tab of tabs) {
      tab.addEventListener('click', () => setActiveTab(tab.dataset.tab));
    }

    function applyTheme(theme) {
      const toggle = document.getElementById('theme-toggle');
      document.documentElement.dataset.theme = theme;
      if (toggle) {
        toggle.textContent = theme === 'dark' ? 'Light Theme' : 'Dark Theme';
      }
      try {
        window.localStorage.setItem(themeStorageKey, theme);
      } catch (_error) {
        // Ignore storage failures; the UI still works without persistence.
      }
    }

    function initThemeToggle() {
      const toggle = document.getElementById('theme-toggle');
      let storedTheme = 'dark';
      try {
        storedTheme = window.localStorage.getItem(themeStorageKey) || 'dark';
      } catch (_error) {
        storedTheme = 'dark';
      }
      applyTheme(storedTheme);
      if (!toggle) {
        return;
      }
      toggle.addEventListener('click', () => {
        const current = document.documentElement.dataset.theme || 'light';
        applyTheme(current === 'light' ? 'dark' : 'light');
      });
    }

    function setGenerationCardsCollapsed(isCollapsed) {
      generationCardsCollapsed = isCollapsed;
      const section = document.getElementById('generation-class-card-section');
      const button = document.getElementById('generation-toggle-btn');
      const status = document.getElementById('generation-toggle-status');
      section.classList.toggle('generation-class-grid-collapsed', isCollapsed);
      button.textContent = isCollapsed ? 'Show Name Class Cards' : 'Hide Name Class Cards';
      status.textContent = isCollapsed
        ? 'Cards collapsed to save vertical space.'
        : 'Cards expanded.';
    }

    function toggleGenerationCards() {
      setGenerationCardsCollapsed(!generationCardsCollapsed);
    }

    function toggleSelectionPane() {
      selectionPaneCollapsed = !selectionPaneCollapsed;
      const pane = document.querySelector('.api-builder-selection-pane');
      if (pane) pane.classList.toggle('collapsed', selectionPaneCollapsed);
    }

    // ── Import File Browser ────────────────────────────────────────
    const importBrowserState = {
      selectedMetadataPath: null,
      selectedMetadataData: null,
      selectedZipPath: null,
      lastBrowsePath: '.',
      highlightedEntry: null,
    };

    function openImportBrowserModal() {
      const modal = document.getElementById('import-browser-modal');
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
      importBrowserState.highlightedEntry = null;
      document.getElementById('import-browser-select').disabled = true;
      browseTo(importBrowserState.lastBrowsePath);
    }

    function closeImportBrowserModal() {
      const modal = document.getElementById('import-browser-modal');
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
    }

    async function browseTo(dirPath) {
      const list = document.getElementById('import-browser-list');
      const breadcrumb = document.getElementById('import-browser-breadcrumb');
      list.innerHTML = '<p class="muted">Loading...</p>';

      const response = await fetch('/api/browse-directory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: dirPath }),
      });
      const data = await response.json();

      if (!response.ok) {
        list.innerHTML = `<p class="err">${escapeHtml(data.error || 'Failed to browse directory.')}</p>`;
        return;
      }

      importBrowserState.lastBrowsePath = data.path;
      importBrowserState.highlightedEntry = null;
      document.getElementById('import-browser-select').disabled = true;

      breadcrumb.textContent = data.path;

      list.innerHTML = '';

      if (data.parent) {
        const parentRow = document.createElement('div');
        parentRow.className = 'import-browser-entry import-browser-entry--dir';
        parentRow.textContent = '.. (parent directory)';
        parentRow.addEventListener('click', () => browseTo(data.parent));
        list.appendChild(parentRow);
      }

      for (const entry of data.entries) {
        const row = document.createElement('div');
        if (entry.type === 'directory') {
          row.className = 'import-browser-entry import-browser-entry--dir';
          row.textContent = entry.name + '/';
          row.addEventListener('click', () => browseTo(entry.path));
        } else {
          row.className = 'import-browser-entry import-browser-entry--file';
          row.textContent = entry.name;
          row.addEventListener('click', () => {
            const prev = list.querySelector('.import-browser-entry--selected');
            if (prev) prev.classList.remove('import-browser-entry--selected');
            row.classList.add('import-browser-entry--selected');
            importBrowserState.highlightedEntry = entry;
            document.getElementById('import-browser-select').disabled = false;
          });
          row.addEventListener('dblclick', () => {
            importBrowserState.highlightedEntry = entry;
            confirmBrowserSelection();
          });
        }
        list.appendChild(row);
      }

      if (!data.entries.length && !data.parent) {
        list.innerHTML = '<p class="muted">Empty directory.</p>';
      }
    }

    async function confirmBrowserSelection() {
      const entry = importBrowserState.highlightedEntry;
      if (!entry) return;

      const status = document.getElementById('import-status');
      status.className = 'muted';
      status.textContent = 'Reading metadata...';

      const response = await fetch('/api/read-metadata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: entry.path }),
      });
      const data = await response.json();

      if (!response.ok) {
        status.className = 'err';
        status.textContent = data.error || 'Failed to read metadata.';
        return;
      }

      const metadata = data.metadata || {};
      const directory = data.directory || '';
      const zipFile = metadata.zip_file || '';

      if (!zipFile) {
        status.className = 'err';
        status.textContent = 'Metadata JSON does not contain a "zip_file" field.';
        return;
      }

      const zipPath = directory ? directory + '/' + zipFile : zipFile;

      importBrowserState.selectedMetadataPath = entry.path;
      importBrowserState.selectedMetadataData = metadata;
      importBrowserState.selectedZipPath = zipPath;

      const selectedEl = document.getElementById('import-selected-path');
      selectedEl.className = 'import-selected-path ok';
      selectedEl.textContent = entry.path;

      document.getElementById('import-btn').disabled = false;
      status.className = 'ok';
      status.textContent = `Metadata loaded. ZIP: ${zipFile}`;

      closeImportBrowserModal();
    }

    async function importFromSelection() {
      const status = document.getElementById('import-status');
      if (!importBrowserState.selectedMetadataPath || !importBrowserState.selectedZipPath) {
        status.className = 'err';
        status.textContent = 'No metadata file selected. Use Browse to select one.';
        return;
      }

      status.className = 'muted';
      status.textContent = 'Importing...';

      const payload = {
        metadata_json_path: importBrowserState.selectedMetadataPath,
        package_zip_path: importBrowserState.selectedZipPath,
      };

      const response = await fetch('/api/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      status.className = response.ok ? 'ok' : 'err';
      status.textContent = data.message || data.error || 'Import failed.';

      if (response.ok) {
        await loadPackages();
        await loadGenerationPackageOptions();
      }
    }

    function setGenerationCardState(classKey, isEnabled, noteText, options) {
      const select = document.getElementById(`generation-package-${classKey}`);
      const sendButton = document.getElementById(`generation-send-${classKey}`);
      const note = document.getElementById(`generation-note-${classKey}`);
      select.innerHTML = '';

      if (!isEnabled) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'No package available';
        select.appendChild(opt);
        select.disabled = true;
        sendButton.disabled = true;
        setGenerationSyllableState(classKey, false, 'No syllable options available', []);
        note.className = 'muted';
        note.textContent = noteText;
        return;
      }

      const prompt = document.createElement('option');
      prompt.value = '';
      prompt.textContent = 'Select package';
      select.appendChild(prompt);

      for (const item of options) {
        const opt = document.createElement('option');
        opt.value = String(item.package_id);
        opt.textContent = `${item.package_name} (id ${item.package_id})`;
        select.appendChild(opt);
      }

      select.disabled = false;
      sendButton.disabled = false;
      setGenerationSyllableState(classKey, false, 'Select a package to list available syllables.', []);
      note.className = 'ok';
      note.textContent = noteText;
    }

    function setGenerationSyllableState(classKey, isEnabled, placeholderText, options) {
      const select = document.getElementById(`generation-syllables-${classKey}`);
      select.innerHTML = '';

      const prompt = document.createElement('option');
      prompt.value = '';
      prompt.textContent = placeholderText;
      select.appendChild(prompt);

      if (!isEnabled) {
        select.disabled = true;
        return;
      }

      for (const item of options) {
        const opt = document.createElement('option');
        opt.value = String(item.key);
        opt.textContent = item.label;
        select.appendChild(opt);
      }
      select.disabled = false;
    }

    async function loadGenerationSyllableOptions(classKey) {
      const packageSelect = document.getElementById(`generation-package-${classKey}`);
      const note = document.getElementById(`generation-note-${classKey}`);
      const packageId = Number(packageSelect.value || '0');
      if (!packageId) {
        setGenerationSyllableState(classKey, false, 'Select package first', []);
        note.className = 'muted';
        note.textContent = 'Select a package to list available syllable options.';
        return;
      }

      note.className = 'muted';
      note.textContent = 'Loading syllable options...';
      const query = new URLSearchParams({ class_key: classKey, package_id: String(packageId) });
      const response = await fetch(`/api/generation/package-syllables?${query.toString()}`);
      const data = await response.json();
      if (!response.ok) {
        setGenerationSyllableState(classKey, false, 'No syllables available', []);
        note.className = 'err';
        note.textContent = data.error || 'Failed to load syllable options.';
        return;
      }

      const syllableOptions = data.syllable_options || [];
      if (!syllableOptions.length) {
        setGenerationSyllableState(classKey, false, 'No syllables found', []);
        note.className = 'muted';
        note.textContent = 'Selected package has no mapped syllable options for this class.';
        return;
      }

      setGenerationSyllableState(classKey, true, 'Select syllable mode', syllableOptions);
      note.className = 'ok';
      note.textContent = `Loaded ${syllableOptions.length} syllable option(s).`;
    }

    // Read and normalize user-supplied API Builder request defaults so the
    // preview and copyable snippets use one canonical parameter snapshot.
    function readApiBuilderParams() {
      const countInput = document.getElementById('api-builder-param-count');
      const seedInput = document.getElementById('api-builder-param-seed');
      const formatSelect = document.getElementById('api-builder-param-format');
      const uniqueCheckbox = document.getElementById('api-builder-param-unique');
      const previewCapCheckbox = document.getElementById('api-builder-preview-cap-enabled');
      const renderSelect = document.getElementById('preview-render-style');
      const rawCount = Number(countInput.value || '0');
      const generationCount = Number.isFinite(rawCount)
        ? Math.min(100000, Math.max(1, Math.trunc(rawCount)))
        : 100;
      countInput.value = String(generationCount);

      let seed = null;
      if (seedInput.value.trim()) {
        const rawSeed = Number(seedInput.value);
        if (Number.isFinite(rawSeed)) {
          seed = Math.trunc(rawSeed);
        }
      }
      const outputFormat = formatSelect.value || 'json';
      const uniqueOnly = Boolean(uniqueCheckbox.checked);
      const previewCapEnabled = previewCapCheckbox ? Boolean(previewCapCheckbox.checked) : true;
      const renderStyle = renderSelect ? renderSelect.value : 'raw';

      return {
        generation_count: generationCount,
        seed: seed,
        output_format: outputFormat,
        unique_only: uniqueOnly,
        render_style: renderStyle,
        preview_cap_enabled: previewCapEnabled,
      };
    }

    function renderApiBuilder() {
      const queue = document.getElementById('api-builder-queue');
      const combined = document.getElementById('api-builder-combined');
      const curlEl = document.getElementById('api-builder-preview-curl');
      const postEl = document.getElementById('api-builder-preview-post');
      const clearButton = document.getElementById('api-builder-clear-btn');
      const requestParams = readApiBuilderParams();
      queue.innerHTML = '';

      if (!apiBuilderSelections.length) {
        clearButton.disabled = true;
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 5;
        td.className = 'muted';
        td.textContent = 'No selections queued.';
        tr.appendChild(td);
        queue.appendChild(tr);
        combined.textContent = 'Combined unique combinations: 0';
        apiBuilderPreviewState.curlText = '';
        apiBuilderPreviewState.postText = '';
        if (curlEl) curlEl.textContent = 'No selections queued yet.';
        if (postEl) postEl.textContent = 'No selections queued yet.';
        return;
      }
      clearButton.disabled = false;

      // Use BigInt to avoid overflow when selections from multiple classes are multiplied.
      let combinedUnique = 1n;
      const curlLines = [];
      const postPayloads = [];

      for (const item of apiBuilderSelections) {
        const tr = document.createElement('tr');
        const fmtNum = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        for (const text of [
          item.class_label,
          item.package_label,
          item.syllable_label,
          fmtNum(item.max_items),
          fmtNum(item.max_unique_combinations),
        ]) {
          const td = document.createElement('td');
          td.textContent = text;
          tr.appendChild(td);
        }
        queue.appendChild(tr);
        const uniqueCount = Math.max(0, Number(item.max_unique_combinations || 0));
        combinedUnique *= BigInt(uniqueCount);

        const generatePayload = {
          class_key: item.class_key,
          package_id: item.package_id,
          syllable_key: item.syllable_key,
          generation_count: requestParams.generation_count,
          output_format: requestParams.output_format,
          unique_only: requestParams.unique_only,
          render_style: requestParams.render_style,
        };
        if (requestParams.seed !== null) {
          generatePayload.seed = requestParams.seed;
        }
        postPayloads.push(generatePayload);
        curlLines.push(
          `curl -s -X POST "${window.location.origin}/api/generate" ` +
            `-H "Content-Type: application/json" ` +
            `-d '${JSON.stringify(generatePayload)}'`
        );
      }

      const combinedDisplay = String(combinedUnique).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      combined.textContent = `Combined unique combinations: ${combinedDisplay}`;

      apiBuilderPreviewState.curlText = curlLines.join('\n\n');
      apiBuilderPreviewState.postText = JSON.stringify(postPayloads, null, 2);
      if (curlEl) curlEl.textContent = apiBuilderPreviewState.curlText || 'No selections queued yet.';
      if (postEl) postEl.textContent = apiBuilderPreviewState.postText || 'No selections queued yet.';
    }

    async function copyBuilderSection(button, text) {
      if (!text) {
        return;
      }
      const label = button.querySelector('span:last-child');
      try {
        await navigator.clipboard.writeText(text);
        if (label) {
          label.textContent = 'Copied';
          button.classList.add('ok');
        }
      } catch (_error) {
        if (label) {
          label.textContent = 'Failed';
          button.classList.add('err');
        }
      }
      window.setTimeout(() => {
        if (label) {
          label.textContent = 'Copy';
          button.classList.remove('ok', 'err');
        }
      }, 1400);
    }

    // Generate a quick inline sample preview using the current queued
    // selections. This calls the SQLite-backed /api/generate endpoint and also
    // derives First x Last Cartesian combinations when both classes exist.
    async function generateApiBuilderInlinePreview() {
      const inlinePreview = document.getElementById('api-builder-inline-preview');
      const comboPreview = document.getElementById('api-builder-combo-preview');
      // Optional preview module renders interactive chips and live preview.
      const previewApi = window.PipeworksPreview || null;
      const params = readApiBuilderParams();
      if (!apiBuilderSelections.length) {
        if (previewApi) {
          previewApi.setInlineMessage(
            'Queue at least one selection before generating preview.',
            'err'
          );
          previewApi.setComboMessage(
            'Need at least one First Name and one Last Name selection to build combinations.',
            'muted'
          );
        } else {
          inlinePreview.className = 'api-builder-preview-list err';
          inlinePreview.textContent = 'Queue at least one selection before generating preview.';
          comboPreview.className = 'api-builder-preview-list muted';
          comboPreview.textContent =
            'Need at least one First Name and one Last Name selection to build combinations.';
        }
        return;
      }

      // Keep preview output bounded for UI readability.
      const requestedCount = params.generation_count;
      const previewCount = params.preview_cap_enabled
        ? Math.min(20, requestedCount)
        : requestedCount;
      if (previewApi) {
        previewApi.setInlineMessage(
          `Generating preview (${previewCount} per selection)...`,
          'muted'
        );
        previewApi.setComboMessage(
          'Building First + Last combinations from preview data...',
          'muted'
        );
      } else {
        inlinePreview.className = 'api-builder-preview-list muted';
        inlinePreview.textContent = `Generating preview (${previewCount} per selection)...`;
        comboPreview.className = 'api-builder-preview-list muted';
        comboPreview.textContent = 'Building First + Last combinations from preview data...';
      }

      const outputGroups = [];
      const namesByClass = {};
      for (const item of apiBuilderSelections) {
        const generatePayload = {
          class_key: item.class_key,
          package_id: item.package_id,
          syllable_key: item.syllable_key,
          generation_count: previewCount,
          unique_only: params.unique_only,
          output_format: params.output_format,
          render_style: params.render_style,
        };
        if (params.seed !== null) {
          generatePayload.seed = params.seed;
        }

        const response = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(generatePayload),
        });
        const data = await response.json();
        if (!response.ok) {
          if (previewApi) {
            previewApi.setInlineMessage(data.error || 'Failed to generate preview.', 'err');
            previewApi.setComboMessage(
              'Combination preview skipped because generation failed.',
              'err'
            );
          } else {
            inlinePreview.className = 'api-builder-preview-list err';
            inlinePreview.textContent = data.error || 'Failed to generate preview.';
            comboPreview.className = 'api-builder-preview-list err';
            comboPreview.textContent = 'Combination preview skipped because generation failed.';
          }
          return;
        }

        const generatedNames = (data.names || []).map((value) => String(value));
        if (!namesByClass[item.class_key]) {
          namesByClass[item.class_key] = [];
        }
        namesByClass[item.class_key].push(...generatedNames);

        const selectionMeta = {
          name_class: item.class_key,
          package_id: item.package_id,
          package_name: item.package_label,
          syllable_key: item.syllable_key,
          syllable_label: item.syllable_label,
          render_style: params.render_style,
          output_format: params.output_format,
          seed: params.seed,
          source: 'generated_preview',
          selection: {
            class_key: item.class_key,
            class_label: item.class_label,
            package_id: item.package_id,
            package_label: item.package_label,
            syllable_key: item.syllable_key,
            syllable_label: item.syllable_label,
            max_items: item.max_items,
            max_unique_combinations: item.max_unique_combinations,
          },
          generation_count: params.generation_count,
          preview_count: previewCount,
        };
        outputGroups.push({
          label: `${item.class_label} [${item.syllable_label}]`,
          entries: generatedNames.map((name) => ({
            name,
            meta: selectionMeta,
          })),
        });
      }

      if (previewApi) {
        previewApi.renderInline(outputGroups);
      } else {
        const outputLines = [];
        for (const group of outputGroups) {
          outputLines.push(`${group.label}`);
          outputLines.push(group.entries.map((entry) => entry.name).join(', '));
          outputLines.push('');
        }
        if (requestedCount > previewCount) {
          outputLines.push(
            `Note: requested ${requestedCount}, UI preview capped at ${previewCount} for readability.`
          );
        }
        inlinePreview.className = 'api-builder-preview-list ok';
        inlinePreview.textContent = outputLines.join('\n').trim() || 'No preview data returned.';
      }

      // Build a de-duplicated First x Last preview matrix from the generated
      // sample output. This provides a quick human check for blend scale.
      const firstNames = Array.from(new Set((namesByClass.first_name || []).filter(Boolean)));
      const lastNames = Array.from(new Set((namesByClass.last_name || []).filter(Boolean)));
      if (!firstNames.length || !lastNames.length) {
        if (previewApi) {
          previewApi.setComboMessage(
            'Need at least one First Name and one Last Name selection to build combinations.',
            'muted'
          );
        } else {
          comboPreview.className = 'api-builder-preview-list muted';
          comboPreview.textContent =
            'Need at least one First Name and one Last Name selection to build combinations.';
        }
        return;
      }

      const combinations = [];
      const firstSources = apiBuilderSelections
        .filter((item) => item.class_key === 'first_name')
        .map((item) => ({
          class_key: item.class_key,
          class_label: item.class_label,
          package_id: item.package_id,
          package_label: item.package_label,
          syllable_key: item.syllable_key,
          syllable_label: item.syllable_label,
        }));
      const lastSources = apiBuilderSelections
        .filter((item) => item.class_key === 'last_name')
        .map((item) => ({
          class_key: item.class_key,
          class_label: item.class_label,
          package_id: item.package_id,
          package_label: item.package_label,
          syllable_key: item.syllable_key,
          syllable_label: item.syllable_label,
        }));
      for (const firstName of firstNames) {
        for (const lastName of lastNames) {
          combinations.push({
            name: `${firstName} ${lastName}`,
            meta: {
              name_class: 'combo_name',
              render_style: params.render_style,
              output_format: params.output_format,
              seed: params.seed,
              source: 'combo_preview',
              name_parts: [firstName, lastName],
              component_sources: {
                first_name: firstSources,
                last_name: lastSources,
              },
              generation_count: params.generation_count,
              preview_count: previewCount,
            },
          });
        }
      }
      const summary = `Total combinations: ${firstNames.length * lastNames.length} (${firstNames.length} x ${lastNames.length})`;
      if (previewApi) {
        previewApi.renderCombinations(combinations, summary);
      } else {
        const combinationLines = [summary, '', ...combinations.map((entry) => entry.name)];
        comboPreview.className = 'api-builder-preview-list ok';
        comboPreview.textContent = combinationLines.join('\n');
      }
    }

    // Clear API Builder queued selections and reset inline previews so users
    // can quickly start a fresh query composition session.
    function clearApiBuilder() {
      apiBuilderSelections.length = 0;
      const inlinePreview = document.getElementById('api-builder-inline-preview');
      const comboPreview = document.getElementById('api-builder-combo-preview');
      const previewApi = window.PipeworksPreview || null;
      if (previewApi) {
        previewApi.setInlineMessage('No preview generated yet.', 'muted');
        previewApi.setComboMessage('No combination preview generated yet.', 'muted');
        previewApi.resetLivePreview();
      } else {
        inlinePreview.className = 'api-builder-preview-list muted';
        inlinePreview.textContent = 'No preview generated yet.';
        comboPreview.className = 'api-builder-preview-list muted';
        comboPreview.textContent = 'No combination preview generated yet.';
      }
      renderApiBuilder();
    }

    async function sendToApiBuilder(classKey) {
      const packageSelect = document.getElementById(`generation-package-${classKey}`);
      const syllableSelect = document.getElementById(`generation-syllables-${classKey}`);
      const note = document.getElementById(`generation-note-${classKey}`);

      if (!packageSelect.value) {
        note.className = 'err';
        note.textContent = 'Select a package before sending to API Builder.';
        return;
      }
      if (!syllableSelect.value) {
        note.className = 'err';
        note.textContent = 'Select a syllable option before sending to API Builder.';
        return;
      }

      note.className = 'muted';
      note.textContent = 'Loading max item and unique combination limits...';
      const query = new URLSearchParams({
        class_key: classKey,
        package_id: packageSelect.value,
        syllable_key: syllableSelect.value,
      });
      const response = await fetch(`/api/generation/selection-stats?${query.toString()}`);
      const stats = await response.json();
      if (!response.ok) {
        note.className = 'err';
        note.textContent = stats.error || 'Failed to load selection limits.';
        return;
      }

      apiBuilderSelections.push({
        class_key: classKey,
        class_label: generationCardLabels[classKey] || classKey,
        package_id: Number(packageSelect.value),
        package_label: packageSelect.selectedOptions[0]?.textContent || '',
        syllable_key: syllableSelect.value,
        syllable_label: syllableSelect.selectedOptions[0]?.textContent || '',
        max_items: Number(stats.max_items || 0),
        max_unique_combinations: Number(stats.max_unique_combinations || 0),
      });
      renderApiBuilder();
      note.className = 'ok';
      note.textContent = `Selection sent. Max items ${stats.max_items}; max unique combinations ${stats.max_unique_combinations}.`;
    }

    // Keep filename timestamps consistent across exports (YYYYMMDD_HHMMSS).
    function formatTimestamp(dateObj) {
      const pad = (value) => String(value).padStart(2, '0');
      return [
        dateObj.getFullYear(),
        pad(dateObj.getMonth() + 1),
        pad(dateObj.getDate()),
        '_',
        pad(dateObj.getHours()),
        pad(dateObj.getMinutes()),
        pad(dateObj.getSeconds()),
      ].join('');
    }

    // Trigger a browser download without involving the server.
    function downloadTextFile(filename, content) {
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    // Apply quick UI feedback to export buttons while async work runs.
    function setExportButtonState(button, text, tone, disabled) {
      if (!button) {
        return;
      }
      button.textContent = text;
      button.classList.remove('ok', 'err');
      if (tone) {
        button.classList.add(tone);
      }
      if (typeof disabled === 'boolean') {
        button.disabled = disabled;
      }
    }

    // Export full-count names or combinations based on the current API Builder
    // selections. This ignores the preview cap and always honors the requested
    // generation_count from the parameters pane.
    async function exportApiBuilderNames(kind) {
      const buttonId =
        kind === 'combo' ? 'api-builder-combo-export-btn' : 'api-builder-inline-export-btn';
      const button = document.getElementById(buttonId);
      if (!button) {
        return;
      }
      if (!apiBuilderSelections.length) {
        setExportButtonState(button, 'No selections', 'err', false);
        window.setTimeout(() => {
          setExportButtonState(button, 'Export TXT', null, false);
        }, 1200);
        return;
      }
      setExportButtonState(button, 'Exporting...', null, true);
      const params = readApiBuilderParams();
      const requestedCount = params.generation_count;
      // Collect full generated output for each queued selection so the exported
      // file contains every requested name.
      const namesByClass = { first_name: [], last_name: [] };
      const inlineNames = [];
      try {
        for (const item of apiBuilderSelections) {
          const generatePayload = {
            class_key: item.class_key,
            package_id: item.package_id,
            syllable_key: item.syllable_key,
            generation_count: requestedCount,
            unique_only: params.unique_only,
            output_format: params.output_format,
            render_style: params.render_style,
          };
          if (params.seed !== null) {
            generatePayload.seed = params.seed;
          }
          const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(generatePayload),
          });
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.error || 'Failed to generate export data.');
          }
          const generatedNames = (data.names || []).map((value) => String(value));
          if (kind === 'inline') {
            inlineNames.push(...generatedNames);
          }
          if (item.class_key === 'first_name') {
            namesByClass.first_name.push(...generatedNames);
          } else if (item.class_key === 'last_name') {
            namesByClass.last_name.push(...generatedNames);
          }
        }

        let outputNames = [];
        let filenamePrefix = 'pipeworks_names';
        if (kind === 'combo') {
          // Build a full cross-product of first/last names from the generated data.
          if (!namesByClass.first_name.length || !namesByClass.last_name.length) {
            throw new Error(
              'Need at least one First Name and one Last Name selection to export combinations.'
            );
          }
          for (const firstName of namesByClass.first_name) {
            for (const lastName of namesByClass.last_name) {
              outputNames.push(`${firstName} ${lastName}`);
            }
          }
          filenamePrefix = 'pipeworks_combinations';
        } else {
          outputNames = inlineNames;
        }

        if (!outputNames.length) {
          throw new Error('No names generated for export.');
        }

        const filename = `${filenamePrefix}_${formatTimestamp(new Date())}.txt`;
        downloadTextFile(filename, `${outputNames.join('\n')}\n`);
        setExportButtonState(button, 'Exported', 'ok', false);
      } catch (error) {
        setExportButtonState(button, 'Export failed', 'err', false);
        const message =
          error instanceof Error ? error.message : 'Export failed. Check the console.';
        console.error(message);
      } finally {
        window.setTimeout(() => {
          setExportButtonState(button, 'Export TXT', null, false);
        }, 1400);
      }
    }

    async function loadGenerationPackageOptions() {
      const status = document.getElementById('status-text');
      status.className = 'status-bar__text';
      status.textContent = 'Loading package options...';

      const response = await fetch('/api/generation/package-options');
      const data = await response.json();
      if (!response.ok) {
        status.className = 'status-bar__text err';
        status.textContent = data.error || 'Failed to load generation package options.';
        return;
      }

      const classEntries = data.name_classes || [];
      const classMap = {};
      for (const entry of classEntries) {
        classMap[entry.key] = entry;
      }

      let nonEmptyClassCount = 0;

      for (const classKey of generationCardKeys) {
        const entry = classMap[classKey];
        const packages = entry?.packages || [];
        if (!packages.length) {
          setGenerationCardState(
            classKey,
            false,
            'No imported package currently maps to this name class.',
            []
          );
          continue;
        }

        nonEmptyClassCount += 1;
        setGenerationCardState(
          classKey,
          true,
          `${packages.length} package(s) available for this class.`,
          packages
        );
      }

      if (!nonEmptyClassCount) {
        status.className = 'status-bar__text';
        status.textContent = 'No generation package options available yet. Import a package pair first.';
        return;
      }

      status.className = 'status-bar__text ok';
      status.textContent = `Loaded package options for ${nonEmptyClassCount} name class(es).`;
    }

    async function loadHelpContent() {
      const status = document.getElementById('help-status');
      const container = document.getElementById('help-content');
      status.className = 'muted';
      status.textContent = 'Loading help content...';
      container.innerHTML = '';

      const response = await fetch('/api/help');
      const data = await response.json();
      if (!response.ok) {
        status.className = 'err';
        status.textContent = data.error || 'Failed to load help content.';
        return;
      }

      const entries = Array.isArray(data.entries) ? data.entries : [];
      if (!entries.length) {
        status.className = 'muted';
        status.textContent = 'No help entries available yet.';
        return;
      }

      status.className = 'ok';
      status.textContent = 'Help content loaded.';

      for (const entry of entries) {
        const card = document.createElement('div');
        card.className = 'card help-entry';

        const question = document.createElement('h3');
        question.className = 'help-entry__question';
        question.textContent = entry.question || 'Untitled';
        card.appendChild(question);

        const answer = document.createElement('p');
        answer.className = 'help-entry__answer';
        answer.textContent = entry.answer || '';
        card.appendChild(answer);

        if (entry.code) {
          const pre = document.createElement('pre');
          const code = document.createElement('code');
          code.textContent = entry.code;
          pre.appendChild(code);
          card.appendChild(pre);
        }

        container.appendChild(card);
      }
    }

    async function loadPackages() {
      const packageSelect = document.getElementById('db-package-select');
      const status = document.getElementById('db-status');
      status.className = 'muted';
      status.textContent = 'Loading packages...';

      const response = await fetch('/api/database/packages');
      const data = await response.json();
      packageSelect.innerHTML = '';

      if (!response.ok) {
        status.className = 'err';
        status.textContent = data.error || 'Failed to load packages.';
        return;
      }

      const packages = data.packages || [];
      if (!packages.length) {
        status.className = 'muted';
        status.textContent = 'No imported packages available.';
        document.getElementById('db-table-select').innerHTML = '';
        document.getElementById('db-row-body').innerHTML = '';
        document.getElementById('db-page-status').textContent = 'Rows 0-0 of 0';
        return;
      }

      for (const pkg of packages) {
        const opt = document.createElement('option');
        opt.value = String(pkg.id);
        opt.textContent = `${pkg.package_name} (id ${pkg.id})`;
        opt.dataset.metadataPath = pkg.metadata_json_path || '';
        packageSelect.appendChild(opt);
      }

      dbState.packageId = Number(packageSelect.value);
      status.className = 'ok';
      status.textContent = `Loaded ${packages.length} package(s).`;
      await loadPackageTables();
    }

    function setDatabaseToolStatus(message, level) {
      const status = document.getElementById('db-export-status');
      if (!status) {
        return;
      }
      status.className = level;
      status.textContent = message;
    }

    async function exportDatabase() {
      // Exports write server-local files; nothing is downloaded in the browser.
      const confirmed = window.confirm('Export database using the server.ini export path?');
      if (!confirmed) {
        return;
      }

      setDatabaseToolStatus('Exporting database...', 'muted');
      const response = await fetch('/api/database/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await response.json();

      if (!response.ok) {
        setDatabaseToolStatus(data.error || 'Failed to export database.', 'err');
        return;
      }

      setDatabaseToolStatus(`Export written to ${data.export_path}.`, 'ok');
    }

    async function backupDatabase() {
      // Backups are server-local copies; use scp if you need the file elsewhere.
      const confirmed = window.confirm('Write database backup using the server.ini backup path?');
      if (!confirmed) {
        return;
      }

      setDatabaseToolStatus('Writing backup...', 'muted');
      const response = await fetch('/api/database/backup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await response.json();

      if (!response.ok) {
        setDatabaseToolStatus(data.error || 'Failed to write backup.', 'err');
        return;
      }

      setDatabaseToolStatus(`Backup written to ${data.backup_path}.`, 'ok');
    }

    async function deleteSelectedPackage() {
      const packageSelect = document.getElementById('db-package-select');
      const packageId = Number(packageSelect.value || '0');
      if (!packageId) {
        setDatabaseToolStatus('Select a package to delete.', 'err');
        return;
      }

      const packageLabel = packageSelect.selectedOptions[0]?.textContent || `id ${packageId}`;
      const confirmed = window.confirm(
        `Delete package "${packageLabel}" and all its imported tables?\n\nThis cannot be undone.`
      );
      if (!confirmed) {
        return;
      }

      setDatabaseToolStatus('Deleting package...', 'muted');
      const response = await fetch('/api/database/delete-package', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ package_id: packageId }),
      });
      const data = await response.json();

      if (!response.ok) {
        setDatabaseToolStatus(data.error || 'Failed to delete package.', 'err');
        return;
      }

      setDatabaseToolStatus(data.message || 'Package deleted.', 'ok');
      await loadPackages();
      await loadGenerationPackageOptions();
    }

    async function loadPackageTables() {
      const packageSelect = document.getElementById('db-package-select');
      const tableSelect = document.getElementById('db-table-select');
      const status = document.getElementById('db-status');
      tableSelect.innerHTML = '';

      document.getElementById('db-manifest-section').classList.add('hidden');
      document.getElementById('db-manifest-tbody').innerHTML = '';

      const packageId = Number(packageSelect.value || '0');
      if (!packageId) {
        status.className = 'muted';
        status.textContent = 'Pick a package.';
        return;
      }

      dbState.packageId = packageId;
      dbState.tableId = null;
      dbState.offset = 0;
      dbState.total = 0;

      const response = await fetch(`/api/database/package-tables?package_id=${encodeURIComponent(packageId)}`);
      const data = await response.json();

      if (!response.ok) {
        status.className = 'err';
        status.textContent = data.error || 'Failed to load tables.';
        return;
      }

      const tables = data.tables || [];
      if (!tables.length) {
        status.className = 'muted';
        status.textContent = 'No txt tables for this package.';
        document.getElementById('db-row-body').innerHTML = '';
        document.getElementById('db-page-status').textContent = 'Rows 0-0 of 0';
        return;
      }

      for (const table of tables) {
        const opt = document.createElement('option');
        opt.value = String(table.id);
        opt.textContent = table.source_txt_name;
        opt.dataset.rowCount = String(table.row_count);
        tableSelect.appendChild(opt);
      }

      dbState.tableId = Number(tableSelect.value);
      dbState.total = Number(tableSelect.selectedOptions[0]?.dataset.rowCount || '0');
      status.className = 'ok';
      status.textContent = `Loaded ${tables.length} table(s).`;
      await loadTableRows();
      loadManifestMetadata();
    }

    function loadManifestMetadata() {
      const section = document.getElementById('db-manifest-section');
      const tbody = document.getElementById('db-manifest-tbody');
      section.classList.add('hidden');
      tbody.innerHTML = '';

      const packageSelect = document.getElementById('db-package-select');
      const selectedOption = packageSelect.selectedOptions[0];
      const metadataPath = selectedOption?.dataset.metadataPath;
      if (!metadataPath) return;

      /* The metadata_json_path stored in the DB already points to the
         *_metadata.json file which contains the full package manifest. */
      fetch('/api/read-metadata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: metadataPath }),
      })
        .then(r => r.json())
        .then(data => {
          if (!data.metadata) return;
          const m = data.metadata;
          renderManifestTable(m, tbody);
          section.classList.remove('hidden');
        })
        .catch(() => {});
    }

    function renderManifestTable(manifest, tbody) {
      const rows = [];

      if (manifest.package_name) rows.push(['Package', escapeHtml(manifest.package_name)]);
      if (manifest.version) rows.push(['Version', escapeHtml(manifest.version)]);
      if (manifest.schema_version != null) rows.push(['Schema', String(manifest.schema_version)]);
      if (manifest.created_at) {
        const d = new Date(manifest.created_at);
        const formatted = Number.isNaN(d.getTime()) ? manifest.created_at : d.toLocaleString();
        rows.push(['Created', escapeHtml(formatted)]);
      }

      const patchKeys = ['patch_a', 'patch_b'];
      const patchLabels = { patch_a: 'Patch A', patch_b: 'Patch B' };
      for (const pk of patchKeys) {
        const patch = manifest[pk];
        if (!patch) continue;
        rows.push([patchLabels[pk], '__sub__']);
        if (patch.run_id) rows.push(['Run ID', `<code>${escapeHtml(patch.run_id)}</code>`]);
        if (patch.corpus_type) rows.push(['Corpus', escapeHtml(patch.corpus_type)]);
        if (patch.syllable_count != null) rows.push(['Syllables', String(patch.syllable_count).replace(/\B(?=(\d{3})+(?!\d))/g, ',')]);
        if (patch.walk_count != null) rows.push(['Walks', String(patch.walk_count)]);
        if (patch.candidate_count != null) rows.push(['Candidates', String(patch.candidate_count).replace(/\B(?=(\d{3})+(?!\d))/g, ',')]);
        if (patch.selection_count != null) rows.push(['Selections', String(patch.selection_count).replace(/\B(?=(\d{3})+(?!\d))/g, ',')]);
      }

      tbody.innerHTML = rows.map(([label, value]) => {
        if (value === '__sub__') {
          return `<tr><td colspan="2" class="manifest-sub">${escapeHtml(label)}</td></tr>`;
        }
        return `<tr><th>${escapeHtml(label)}</th><td>${value}</td></tr>`;
      }).join('');
    }

    async function loadTableRows() {
      const body = document.getElementById('db-row-body');
      const pageStatus = document.getElementById('db-page-status');
      const prevBtn = document.getElementById('db-prev-btn');
      const nextBtn = document.getElementById('db-next-btn');

      if (!dbState.tableId) {
        body.innerHTML = '';
        pageStatus.textContent = 'Rows 0-0 of 0';
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
      }

      const response = await fetch(
        `/api/database/table-rows?table_id=${encodeURIComponent(dbState.tableId)}&offset=${encodeURIComponent(dbState.offset)}&limit=${encodeURIComponent(dbState.limit)}`
      );
      const data = await response.json();
      body.innerHTML = '';

      if (!response.ok) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="2">${data.error || 'Failed to load rows.'}</td>`;
        body.appendChild(tr);
        pageStatus.textContent = 'Rows 0-0 of 0';
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
      }

      const rows = data.rows || [];
      dbState.total = Number(data.total_rows || 0);
      dbState.offset = Number(data.offset || 0);
      dbState.limit = Number(data.limit || dbState.limit);

      for (const row of rows) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${row.line_number}</td><td>${escapeHtml(row.value)}</td>`;
        body.appendChild(tr);
      }

      if (!rows.length) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="2" class="muted">No rows available.</td>';
        body.appendChild(tr);
      }

      const start = dbState.total ? dbState.offset + 1 : 0;
      const end = dbState.offset + rows.length;
      pageStatus.textContent = `Rows ${start}-${end} of ${dbState.total}`;
      prevBtn.disabled = dbState.offset <= 0;
      nextBtn.disabled = (dbState.offset + dbState.limit) >= dbState.total;
    }

    function pagePrev() {
      dbState.offset = Math.max(0, dbState.offset - dbState.limit);
      loadTableRows();
    }

    function pageNext() {
      dbState.offset = dbState.offset + dbState.limit;
      loadTableRows();
    }

    document.getElementById('import-btn').addEventListener('click', importFromSelection);
    document.getElementById('import-browse-btn').addEventListener('click', openImportBrowserModal);
    document.getElementById('import-browser-close').addEventListener('click', closeImportBrowserModal);
    document.getElementById('import-browser-cancel').addEventListener('click', closeImportBrowserModal);
    document.getElementById('import-browser-select').addEventListener('click', confirmBrowserSelection);
    document.getElementById('import-browser-modal').querySelector('.modal-backdrop').addEventListener('click', closeImportBrowserModal);
    document.getElementById('generation-toggle-btn').addEventListener('click', toggleGenerationCards);
    document.getElementById('api-builder-selection-toggle-btn').addEventListener('click', toggleSelectionPane);
    for (const classKey of generationCardKeys) {
      const select = document.getElementById(`generation-package-${classKey}`);
      const sendButton = document.getElementById(`generation-send-${classKey}`);
      select.addEventListener('change', () => {
        loadGenerationSyllableOptions(classKey);
      });
      sendButton.addEventListener('click', () => {
        void sendToApiBuilder(classKey);
      });
    }
    document.getElementById('db-refresh-packages').addEventListener('click', loadPackages);
    document.getElementById('db-export-btn').addEventListener('click', () => {
      void exportDatabase();
    });
    document.getElementById('db-backup-btn').addEventListener('click', () => {
      void backupDatabase();
    });
    document.getElementById('db-delete-package-btn').addEventListener('click', () => {
      void deleteSelectedPackage();
    });
    document.getElementById('db-package-select').addEventListener('change', loadPackageTables);
    document.getElementById('db-table-select').addEventListener('change', () => {
      const tableSelect = document.getElementById('db-table-select');
      dbState.tableId = Number(tableSelect.value || '0');
      dbState.total = Number(tableSelect.selectedOptions[0]?.dataset.rowCount || '0');
      dbState.offset = 0;
      loadTableRows();
    });
    document.getElementById('db-prev-btn').addEventListener('click', pagePrev);
    document.getElementById('db-next-btn').addEventListener('click', pageNext);
    document.getElementById('api-builder-copy-curl-btn').addEventListener('click', (e) => {
      void copyBuilderSection(e.currentTarget, apiBuilderPreviewState.curlText);
    });
    document.getElementById('api-builder-copy-post-btn').addEventListener('click', (e) => {
      void copyBuilderSection(e.currentTarget, apiBuilderPreviewState.postText);
    });
    document.getElementById('api-builder-clear-btn').addEventListener('click', clearApiBuilder);
    document.getElementById('api-builder-generate-preview-btn').addEventListener('click', () => {
      void generateApiBuilderInlinePreview();
    });
    const apiParamIds = [
      'api-builder-param-count',
      'api-builder-param-seed',
      'api-builder-param-format',
      'api-builder-param-unique',
      'api-builder-preview-cap-enabled',
    ];
    for (const paramId of apiParamIds) {
      const element = document.getElementById(paramId);
      element.addEventListener('input', renderApiBuilder);
      element.addEventListener('change', renderApiBuilder);
    }
    const renderSelect = document.getElementById('preview-render-style');
    if (renderSelect) {
      renderSelect.addEventListener('change', renderApiBuilder);
    }

    window.PipeworksApiBuilder = {
      exportNames(kind) {
        void exportApiBuilderNames(kind);
      },
    };

    initThemeToggle();
    loadPackages();
    loadGenerationPackageOptions();
    loadHelpContent();
    renderApiBuilder();
    setGenerationCardsCollapsed(true);

    /* Version is injected server-side into the HTML template. */
