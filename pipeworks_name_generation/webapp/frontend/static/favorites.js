(function () {
  const favoritesState = {
    offset: 0,
    limit: 20,
    total: 0,
    tag: '',
    query: '',
  };

  const modalState = {
    mode: 'create',
    entries: [],
    favoriteId: null,
  };

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(message, tone) {
    const status = $('favorites-status');
    if (!status) {
      return;
    }
    status.className = tone || 'muted';
    status.textContent = message;
  }

  function formatDate(value) {
    if (!value) {
      return '';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString();
  }

  function parseTagInput(raw) {
    return String(raw || '')
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  function buildFavoriteEntry(entry, fallbackSource) {
    const meta = entry && typeof entry.meta === 'object' ? entry.meta : {};
    const selection = meta.selection || {};
    return {
      name: entry.name,
      name_class: meta.name_class || selection.class_key || null,
      package_id: meta.package_id ?? selection.package_id ?? null,
      package_name: meta.package_name || selection.package_label || null,
      syllable_key: meta.syllable_key || selection.syllable_key || null,
      render_style: meta.render_style || null,
      output_format: meta.output_format || null,
      seed: meta.seed ?? null,
      gender: meta.gender || null,
      source: meta.source || fallbackSource || 'api_builder',
      metadata: meta && typeof meta === 'object' ? meta : {},
    };
  }

  function mapEntries(entries, fallbackSource) {
    return entries.map((entry) => buildFavoriteEntry(entry, fallbackSource));
  }

  function renderModalNames(entries) {
    const container = $('favorites-modal-names');
    if (!container) {
      return;
    }
    container.innerHTML = '';
    if (!entries.length) {
      container.textContent = 'No names selected.';
      return;
    }
    const maxShown = 30;
    const shown = entries.slice(0, maxShown);
    for (const entry of shown) {
      const row = document.createElement('div');
      row.textContent = entry.name;
      container.appendChild(row);
    }
    if (entries.length > maxShown) {
      const more = document.createElement('div');
      more.className = 'muted';
      more.textContent = `+ ${entries.length - maxShown} more name(s)`;
      container.appendChild(more);
    }
  }

  function openModal(entries, mode) {
    const modal = $('favorites-modal');
    if (!modal) {
      return;
    }
    modalState.mode = mode || 'create';
    modalState.entries = entries;
    modalState.favoriteId = null;

    const title = $('favorites-modal-title');
    const summary = $('favorites-modal-summary');
    const saveButton = $('favorites-modal-save');
    const isEdit = modalState.mode === 'edit';

    if (title) {
      title.textContent = isEdit ? 'Edit Favorite' : 'Save Favorites';
    }
    if (summary) {
      summary.textContent = isEdit
        ? 'Update tags and notes for this favorite.'
        : `Saving ${entries.length} favorite name(s).`;
    }
    if (saveButton) {
      saveButton.textContent = isEdit ? 'Save Changes' : 'Save Favorites';
    }
    $('favorites-modal-tags').value = '';
    $('favorites-modal-note').value = '';
    const genderSelect = $('favorites-modal-gender');
    if (genderSelect) {
      genderSelect.value = '';
    }
    $('favorites-modal-id').value = '';

    renderModalNames(entries);
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  }

  function openEditModal(favorite) {
    const entries = [
      {
        name: favorite.name,
        meta: {
          name_class: favorite.name_class,
          package_id: favorite.package_id,
          package_name: favorite.package_name,
          syllable_key: favorite.syllable_key,
          render_style: favorite.render_style,
          output_format: favorite.output_format,
          seed: favorite.seed,
          source: favorite.source,
          metadata: favorite.metadata,
        },
      },
    ];
    openModal(entries, 'edit');
    modalState.favoriteId = favorite.id;
    $('favorites-modal-tags').value = (favorite.tags || []).join(', ');
    $('favorites-modal-note').value = favorite.note_md || '';
    $('favorites-modal-id').value = String(favorite.id);
    const genderSelect = $('favorites-modal-gender');
    if (genderSelect) {
      genderSelect.value = favorite.gender || '';
    }
  }

  function closeModal() {
    const modal = $('favorites-modal');
    if (!modal) {
      return;
    }
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    modalState.entries = [];
    modalState.favoriteId = null;
  }

  async function saveModalFavorites() {
    const saveButton = $('favorites-modal-save');
    const tagsInput = $('favorites-modal-tags');
    const noteInput = $('favorites-modal-note');
    if (!saveButton || !tagsInput || !noteInput) {
      return;
    }
    saveButton.disabled = true;

    const tags = parseTagInput(tagsInput.value);
    const noteValue = noteInput.value.trim();
    const genderValue = $('favorites-modal-gender')?.value || '';

    try {
      if (modalState.mode === 'edit') {
        const favoriteId = modalState.favoriteId;
        if (!favoriteId) {
          throw new Error('Missing favorite id.');
        }
        const response = await fetch('/api/favorites/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            favorite_id: favoriteId,
            tags,
            note_md: noteValue,
            gender: genderValue,
          }),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || 'Failed to update favorite.');
        }
        setStatus('Favorite updated.', 'ok');
      } else {
        if (!modalState.entries.length) {
          throw new Error('No favorites selected.');
        }
        const payload = {
          entries: mapEntries(modalState.entries, 'api_builder_preview'),
          tags,
          note_md: noteValue || null,
          gender: genderValue,
        };
        const response = await fetch('/api/favorites', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || 'Failed to save favorites.');
        }
        setStatus(`Saved ${data.count || payload.entries.length} favorite(s).`, 'ok');
      }
      closeModal();
      await loadFavorites();
      await loadFavoriteTags();
    } catch (error) {
      setStatus(error.message || 'Failed to save favorites.', 'err');
    } finally {
      saveButton.disabled = false;
    }
  }

  function renderFavoritesTable(favorites) {
    const tbody = $('favorites-table-body');
    if (!tbody) {
      return;
    }
    tbody.innerHTML = '';
    if (!favorites.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 8;
      cell.className = 'muted';
      cell.textContent = 'No favorites saved yet.';
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }
    for (const favorite of favorites) {
      const row = document.createElement('tr');

      const nameCell = document.createElement('td');
      nameCell.textContent = favorite.name;
      row.appendChild(nameCell);

      const classCell = document.createElement('td');
      classCell.textContent = favorite.name_class || '—';
      row.appendChild(classCell);

      const genderCell = document.createElement('td');
      genderCell.textContent = favorite.gender || '—';
      row.appendChild(genderCell);

      const packageCell = document.createElement('td');
      const packageLabel = favorite.package_name
        ? `${favorite.package_name} (id ${favorite.package_id || 'n/a'})`
        : favorite.package_id
          ? `Package ${favorite.package_id}`
          : '—';
      packageCell.textContent = packageLabel;
      row.appendChild(packageCell);

      const tagCell = document.createElement('td');
      tagCell.textContent = (favorite.tags || []).join(', ') || '—';
      row.appendChild(tagCell);

      const noteCell = document.createElement('td');
      noteCell.textContent = favorite.note_md || '—';
      row.appendChild(noteCell);

      const dateCell = document.createElement('td');
      dateCell.textContent = formatDate(favorite.created_at);
      row.appendChild(dateCell);

      const actionsCell = document.createElement('td');
      const editButton = document.createElement('button');
      editButton.type = 'button';
      editButton.textContent = 'Edit';
      editButton.addEventListener('click', () => openEditModal(favorite));
      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';
      deleteButton.textContent = 'Delete';
      deleteButton.addEventListener('click', async () => {
        const confirmed = window.confirm(
          `Delete favorite \"${favorite.name}\"? This cannot be undone.`
        );
        if (!confirmed) {
          return;
        }
        const response = await fetch('/api/favorites/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ favorite_id: favorite.id }),
        });
        const data = await response.json();
        if (!response.ok) {
          setStatus(data.error || 'Failed to delete favorite.', 'err');
          return;
        }
        setStatus('Favorite deleted.', 'ok');
        await loadFavorites();
        await loadFavoriteTags();
      });
      actionsCell.appendChild(editButton);
      actionsCell.appendChild(deleteButton);
      row.appendChild(actionsCell);

      tbody.appendChild(row);
    }
  }

  function updateFavoritesPagination() {
    const status = $('favorites-page-status');
    if (!status) {
      return;
    }
    const start = favoritesState.total ? favoritesState.offset + 1 : 0;
    const end = Math.min(favoritesState.offset + favoritesState.limit, favoritesState.total);
    status.textContent = `Rows ${start}-${end} of ${favoritesState.total}`;
  }

  async function loadFavorites() {
    const params = new URLSearchParams({
      limit: String(favoritesState.limit),
      offset: String(favoritesState.offset),
    });
    if (favoritesState.tag) {
      params.append('tag', favoritesState.tag);
    }
    if (favoritesState.query) {
      params.append('q', favoritesState.query);
    }
    const response = await fetch(`/api/favorites?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || 'Failed to load favorites.', 'err');
      return;
    }
    favoritesState.total = data.total || 0;
    renderFavoritesTable(data.favorites || []);
    updateFavoritesPagination();
    setStatus(`Loaded ${data.total || 0} favorite(s).`, 'ok');
  }

  async function loadFavoriteTags() {
    const select = $('favorites-tag-filter');
    if (!select) {
      return;
    }
    const response = await fetch('/api/favorites/tags');
    const data = await response.json();
    if (!response.ok) {
      return;
    }
    const tags = data.tags || [];
    select.innerHTML = '';
    const allOption = document.createElement('option');
    allOption.value = '';
    allOption.textContent = 'All tags';
    select.appendChild(allOption);
    for (const tag of tags) {
      const option = document.createElement('option');
      option.value = tag;
      option.textContent = tag;
      select.appendChild(option);
    }
    select.value = favoritesState.tag;
  }

  async function exportFavoritesToClipboard() {
    const response = await fetch('/api/favorites/export');
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || 'Failed to export favorites.', 'err');
      return;
    }
    const payload = JSON.stringify(data, null, 2);
    try {
      await navigator.clipboard.writeText(payload);
      setStatus('Export copied to clipboard.', 'ok');
    } catch (_error) {
      setStatus('Clipboard unavailable. Copy from developer tools.', 'err');
    }
  }

  async function writeBackup() {
    const pathInput = $('favorites-export-path');
    if (!pathInput) {
      return;
    }
    const outputPath = pathInput.value.trim();
    if (!outputPath) {
      setStatus('Enter a backup path before exporting.', 'err');
      return;
    }
    const confirmed = window.confirm(`Write favorites backup to ${outputPath}?`);
    if (!confirmed) {
      return;
    }
    const response = await fetch('/api/favorites/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ output_path: outputPath }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || 'Failed to write backup.', 'err');
      return;
    }
    setStatus(`Backup written to ${data.path}.`, 'ok');
  }

  async function importFavorites() {
    const pathInput = $('favorites-import-path');
    if (!pathInput) {
      return;
    }
    const importPath = pathInput.value.trim();
    if (!importPath) {
      setStatus('Enter a JSON path before importing.', 'err');
      return;
    }
    const confirmed = window.confirm(
      `Import favorites from ${importPath}? Existing favorites will remain.`
    );
    if (!confirmed) {
      return;
    }
    const response = await fetch('/api/favorites/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ import_path: importPath }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.error || 'Failed to import favorites.', 'err');
      return;
    }
    setStatus(`Imported ${data.count || 0} favorite(s).`, 'ok');
    await loadFavorites();
    await loadFavoriteTags();
  }

  function attachFavoriteButtons() {
    const previewApi = window.PipeworksPreview || null;
    const inlineButton = $('api-builder-inline-fav-btn');
    const comboButton = $('api-builder-combo-fav-btn');
    const liveButton = $('api-builder-live-fav-btn');

    if (inlineButton) {
      inlineButton.addEventListener('click', () => {
        const entries = previewApi ? previewApi.getInlineEntries() : [];
        if (!entries.length) {
          setStatus('Generate a preview before saving favorites.', 'err');
          return;
        }
        openModal(entries, 'create');
      });
    }

    if (comboButton) {
      comboButton.addEventListener('click', () => {
        const entries = previewApi ? previewApi.getComboEntries() : [];
        if (!entries.length) {
          setStatus('Generate a combo preview before saving favorites.', 'err');
          return;
        }
        openModal(entries, 'create');
      });
    }

    if (liveButton) {
      liveButton.addEventListener('click', () => {
        const entry = previewApi ? previewApi.getLiveEntry() : null;
        if (!entry) {
          setStatus('Select a name from the preview first.', 'err');
          return;
        }
        openModal([entry], 'create');
      });
    }
  }

  function attachFavoritesPanelEvents() {
    const refreshButton = $('favorites-refresh-btn');
    const exportButton = $('favorites-export-btn');
    const backupButton = $('favorites-backup-btn');
    const importButton = $('favorites-import-btn');
    const prevButton = $('favorites-prev-btn');
    const nextButton = $('favorites-next-btn');
    const tagFilter = $('favorites-tag-filter');
    const searchInput = $('favorites-search');

    if (refreshButton) {
      refreshButton.addEventListener('click', async () => {
        await loadFavorites();
        await loadFavoriteTags();
      });
    }
    if (exportButton) {
      exportButton.addEventListener('click', () => {
        void exportFavoritesToClipboard();
      });
    }
    if (backupButton) {
      backupButton.addEventListener('click', () => {
        void writeBackup();
      });
    }
    if (importButton) {
      importButton.addEventListener('click', () => {
        void importFavorites();
      });
    }
    if (prevButton) {
      prevButton.addEventListener('click', () => {
        favoritesState.offset = Math.max(0, favoritesState.offset - favoritesState.limit);
        void loadFavorites();
      });
    }
    if (nextButton) {
      nextButton.addEventListener('click', () => {
        favoritesState.offset = favoritesState.offset + favoritesState.limit;
        void loadFavorites();
      });
    }
    if (tagFilter) {
      tagFilter.addEventListener('change', () => {
        favoritesState.tag = tagFilter.value;
        favoritesState.offset = 0;
        void loadFavorites();
      });
    }
    if (searchInput) {
      let searchTimeout = null;
      searchInput.addEventListener('input', () => {
        if (searchTimeout) {
          window.clearTimeout(searchTimeout);
        }
        searchTimeout = window.setTimeout(() => {
          favoritesState.query = searchInput.value.trim();
          favoritesState.offset = 0;
          void loadFavorites();
        }, 250);
      });
    }
  }

  function attachModalEvents() {
    const modal = $('favorites-modal');
    const closeButton = $('favorites-modal-close');
    const cancelButton = $('favorites-modal-cancel');
    const saveButton = $('favorites-modal-save');
    if (closeButton) {
      closeButton.addEventListener('click', closeModal);
    }
    if (cancelButton) {
      cancelButton.addEventListener('click', closeModal);
    }
    if (saveButton) {
      saveButton.addEventListener('click', () => {
        void saveModalFavorites();
      });
    }
    if (modal) {
      modal.addEventListener('click', (event) => {
        const target = event.target;
        if (target instanceof HTMLElement && target.dataset.close === 'true') {
          closeModal();
        }
      });
    }
  }

  function attachTabAutoload() {
    const favoritesTab = document.querySelector('.tab[data-tab="favorites"]');
    if (!favoritesTab) {
      return;
    }
    favoritesTab.addEventListener('click', () => {
      void loadFavorites();
      void loadFavoriteTags();
    });
  }

  function initFavorites() {
    attachFavoriteButtons();
    attachFavoritesPanelEvents();
    attachModalEvents();
    attachTabAutoload();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFavorites);
  } else {
    initFavorites();
  }
})();
