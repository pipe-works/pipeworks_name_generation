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
      import: document.getElementById('panel-import'),
      generation: document.getElementById('panel-generation'),
      database: document.getElementById('panel-database'),
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
    let generationCardsCollapsed = true;

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

    async function importPair() {
      const status = document.getElementById('import-status');
      status.className = 'muted';
      status.textContent = 'Importing...';

      const payload = {
        metadata_json_path: document.getElementById('metadata-path').value.trim(),
        package_zip_path: document.getElementById('zip-path').value.trim(),
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
      const summary = document.getElementById('api-builder-param-summary');

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

      const seedText = seed === null ? 'random' : String(seed);
      summary.textContent = `Count ${generationCount}, seed ${seedText}, format ${outputFormat}, unique ${uniqueOnly}`;

      return {
        generation_count: generationCount,
        seed: seed,
        output_format: outputFormat,
        unique_only: uniqueOnly,
      };
    }

    // Render API Builder queue, combined unique estimate, and copyable query
    // snippets from current selections + parameter defaults.
    function renderApiBuilder() {
      const queue = document.getElementById('api-builder-queue');
      const preview = document.getElementById('api-builder-preview');
      const combined = document.getElementById('api-builder-combined');
      const copyStatus = document.getElementById('api-builder-copy-status');
      const clearButton = document.getElementById('api-builder-clear-btn');
      const requestParams = readApiBuilderParams();
      queue.innerHTML = '';

      if (!apiBuilderSelections.length) {
        clearButton.disabled = true;
        const li = document.createElement('li');
        li.className = 'muted';
        li.textContent = 'No selections queued.';
        queue.appendChild(li);
        combined.textContent = 'Combined unique combinations: 0';
        copyStatus.className = 'muted';
        copyStatus.textContent = 'No query content yet.';
        preview.textContent = 'No selections queued yet.';
        return;
      }
      clearButton.disabled = false;

      // Use BigInt to avoid overflow when selections from multiple classes are multiplied.
      let combinedUnique = 1n;

      for (const item of apiBuilderSelections) {
        const li = document.createElement('li');
        li.textContent =
          `${item.class_label}: ${item.package_label} [${item.syllable_label}] ` +
          `(max items ${item.max_items}, max unique ${item.max_unique_combinations})`;
        queue.appendChild(li);
        const uniqueCount = Math.max(0, Number(item.max_unique_combinations || 0));
        combinedUnique *= BigInt(uniqueCount);
      }

      const combinedDisplay = String(combinedUnique).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
      combined.textContent = `Combined unique combinations: ${combinedDisplay}`;
      const previewLines = [
        '# Pipeworks API Builder Output',
        '# Selection stats query commands',
        `# Defaults: count=${requestParams.generation_count}, seed=${requestParams.seed === null ? 'random' : requestParams.seed}, format=${requestParams.output_format}, unique_only=${requestParams.unique_only}`,
      ];
      for (const item of apiBuilderSelections) {
        const query = new URLSearchParams({
          class_key: item.class_key,
          package_id: String(item.package_id),
          syllable_key: item.syllable_key,
        });
        previewLines.push('');
        previewLines.push(`# ${item.class_label} (${item.syllable_label})`);
        previewLines.push(
          `curl -s "${window.location.origin}/api/generation/selection-stats?${query.toString()}"`
        );
        const generatePayload = {
          class_key: item.class_key,
          package_id: item.package_id,
          syllable_key: item.syllable_key,
          generation_count: requestParams.generation_count,
          output_format: requestParams.output_format,
          unique_only: requestParams.unique_only,
        };
        if (requestParams.seed !== null) {
          generatePayload.seed = requestParams.seed;
        }
        previewLines.push('POST /api/generate payload:');
        previewLines.push(JSON.stringify(generatePayload));
      }
      previewLines.push('');
      previewLines.push(`# Combined unique combinations estimate: ${combinedDisplay}`);
      previewLines.push('# Structured selection payload');
      previewLines.push(
        JSON.stringify(
          apiBuilderSelections.map((item) => ({
            class_key: item.class_key,
            package_id: item.package_id,
            syllable_key: item.syllable_key,
            generation_count: requestParams.generation_count,
            seed: requestParams.seed,
            output_format: requestParams.output_format,
            unique_only: requestParams.unique_only,
            max_items: item.max_items,
            max_unique_combinations: item.max_unique_combinations,
          })),
          null,
          2
        )
      );
      copyStatus.className = 'muted';
      copyStatus.textContent = 'Preview ready. Use copy button for programmatic use.';
      preview.textContent = previewLines.join('\n');
    }

    // Copy the full builder preview text (query snippets + payload examples)
    // into the clipboard so it can be pasted into scripts or terminals.
    async function copyApiBuilderPreview() {
      const preview = document.getElementById('api-builder-preview');
      const copyStatus = document.getElementById('api-builder-copy-status');
      const text = String(preview.textContent || '').trim();
      if (!text || text === 'No selections queued yet.') {
        copyStatus.className = 'err';
        copyStatus.textContent = 'Nothing to copy yet. Queue at least one selection.';
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
        copyStatus.className = 'ok';
        copyStatus.textContent = 'Copied query text to clipboard.';
      } catch (_error) {
        copyStatus.className = 'err';
        copyStatus.textContent = 'Clipboard unavailable. Copy directly from preview text.';
      }
    }

    // Generate a quick inline sample preview using the current queued
    // selections. This calls the SQLite-backed /api/generate endpoint and also
    // derives First x Last Cartesian combinations when both classes exist.
    async function generateApiBuilderInlinePreview() {
      const inlinePreview = document.getElementById('api-builder-inline-preview');
      const comboPreview = document.getElementById('api-builder-combo-preview');
      const params = readApiBuilderParams();
      if (!apiBuilderSelections.length) {
        inlinePreview.className = 'err';
        inlinePreview.textContent = 'Queue at least one selection before generating preview.';
        comboPreview.className = 'muted';
        comboPreview.textContent =
          'Need at least one First Name and one Last Name selection to build combinations.';
        return;
      }

      // Keep preview output bounded for UI readability.
      const requestedCount = params.generation_count;
      const previewCount = Math.min(20, requestedCount);
      inlinePreview.className = 'muted';
      inlinePreview.textContent = `Generating preview (${previewCount} per selection)...`;
      comboPreview.className = 'muted';
      comboPreview.textContent = 'Building First + Last combinations from preview data...';

      const outputLines = [];
      const namesByClass = {};
      for (const item of apiBuilderSelections) {
        const generatePayload = {
          class_key: item.class_key,
          package_id: item.package_id,
          syllable_key: item.syllable_key,
          generation_count: previewCount,
          unique_only: params.unique_only,
          output_format: params.output_format,
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
          inlinePreview.className = 'err';
          inlinePreview.textContent = data.error || 'Failed to generate preview.';
          comboPreview.className = 'err';
          comboPreview.textContent = 'Combination preview skipped because generation failed.';
          return;
        }

        const generatedNames = (data.names || []).map((value) => String(value));
        if (!namesByClass[item.class_key]) {
          namesByClass[item.class_key] = [];
        }
        namesByClass[item.class_key].push(...generatedNames);

        outputLines.push(`${item.class_label} [${item.syllable_label}]`);
        outputLines.push(generatedNames.join(', '));
        outputLines.push('');
      }

      if (requestedCount > previewCount) {
        outputLines.push(
          `Note: requested ${requestedCount}, UI preview capped at ${previewCount} for readability.`
        );
      }

      inlinePreview.className = 'ok';
      inlinePreview.textContent = outputLines.join('\n').trim() || 'No preview data returned.';

      // Build a de-duplicated First x Last preview matrix from the generated
      // sample output. This provides a quick human check for blend scale.
      const firstNames = Array.from(new Set((namesByClass.first_name || []).filter(Boolean)));
      const lastNames = Array.from(new Set((namesByClass.last_name || []).filter(Boolean)));
      if (!firstNames.length || !lastNames.length) {
        comboPreview.className = 'muted';
        comboPreview.textContent =
          'Need at least one First Name and one Last Name selection to build combinations.';
        return;
      }

      const combinationLines = [
        `Total combinations: ${firstNames.length * lastNames.length} (${firstNames.length} x ${lastNames.length})`,
        '',
      ];
      for (const firstName of firstNames) {
        for (const lastName of lastNames) {
          combinationLines.push(`${firstName} ${lastName}`);
        }
      }
      comboPreview.className = 'ok';
      comboPreview.textContent = combinationLines.join('\n');
    }

    // Clear API Builder queued selections and reset inline previews so users
    // can quickly start a fresh query composition session.
    function clearApiBuilder() {
      apiBuilderSelections.length = 0;
      const inlinePreview = document.getElementById('api-builder-inline-preview');
      const comboPreview = document.getElementById('api-builder-combo-preview');
      inlinePreview.className = 'muted';
      inlinePreview.textContent = 'No preview generated yet.';
      comboPreview.className = 'muted';
      comboPreview.textContent = 'No combination preview generated yet.';
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

    async function loadGenerationPackageOptions() {
      const status = document.getElementById('generation-status');
      status.className = 'muted';
      status.textContent = 'Loading package options...';

      const response = await fetch('/api/generation/package-options');
      const data = await response.json();
      if (!response.ok) {
        status.className = 'err';
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
        status.className = 'muted';
        status.textContent = 'No generation package options available yet. Import a package pair first.';
        return;
      }

      status.className = 'ok';
      status.textContent = `Loaded package options for ${nonEmptyClassCount} name class(es).`;
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
        document.getElementById('db-table-list').innerHTML = '';
        document.getElementById('db-row-body').innerHTML = '';
        document.getElementById('db-page-status').textContent = 'Rows 0-0 of 0';
        return;
      }

      for (const pkg of packages) {
        const opt = document.createElement('option');
        opt.value = String(pkg.id);
        opt.textContent = `${pkg.package_name} (id ${pkg.id})`;
        packageSelect.appendChild(opt);
      }

      dbState.packageId = Number(packageSelect.value);
      status.className = 'ok';
      status.textContent = `Loaded ${packages.length} package(s).`;
      await loadPackageTables();
    }

    async function loadPackageTables() {
      const packageSelect = document.getElementById('db-package-select');
      const tableSelect = document.getElementById('db-table-select');
      const tableList = document.getElementById('db-table-list');
      const status = document.getElementById('db-status');
      tableSelect.innerHTML = '';
      tableList.innerHTML = '';

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

        const li = document.createElement('li');
        li.innerHTML =
          `<div><strong>${escapeHtml(table.source_txt_name)}</strong> ` +
          `<span class="muted">(${table.row_count} rows)</span></div>` +
          `<code>${escapeHtml(table.table_name)}</code>`;
        tableList.appendChild(li);
      }

      dbState.tableId = Number(tableSelect.value);
      dbState.total = Number(tableSelect.selectedOptions[0]?.dataset.rowCount || '0');
      status.className = 'ok';
      status.textContent = `Loaded ${tables.length} table(s).`;
      await loadTableRows();
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

    document.getElementById('import-btn').addEventListener('click', importPair);
    document.getElementById('generation-toggle-btn').addEventListener('click', toggleGenerationCards);
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
    document.getElementById('api-builder-copy-btn').addEventListener('click', () => {
      void copyApiBuilderPreview();
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
    ];
    for (const paramId of apiParamIds) {
      const element = document.getElementById(paramId);
      element.addEventListener('input', renderApiBuilder);
      element.addEventListener('change', renderApiBuilder);
    }

    loadPackages();
    loadGenerationPackageOptions();
    renderApiBuilder();
    setGenerationCardsCollapsed(true);
