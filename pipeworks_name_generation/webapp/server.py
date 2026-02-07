"""Simple web server with Import, Generation, and Database View tabs.

This version stores package imports in SQLite and creates one SQLite data table
for each imported ``*.txt`` selection file. JSON files are intentionally ignored
for now, per current requirements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import sqlite3
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, urlsplit

from pipeworks_name_generation.webapp.config import (
    ServerSettings,
    apply_runtime_overrides,
    load_server_settings,
)

# Keep pagination intentionally small so database browsing is readable.
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 200

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pipeworks Name Generator</title>
  <style>
    :root {
      --bg: #0b1020;
      --panel: #121a2d;
      --panel-2: #0f172a;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --border: #334155;
      --accent: #22d3ee;
      --accent-2: #0891b2;
      --ok: #34d399;
      --err: #f87171;
    }
    body {
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: radial-gradient(circle at top right, #1e293b, var(--bg));
      color: var(--text);
    }
    .wrap {
      max-width: 1280px;
      margin: 1.4rem auto;
      padding: 0 1rem;
    }
    .card {
      border: 1px solid var(--border);
      background: color-mix(in srgb, var(--panel) 92%, black 8%);
      border-radius: 12px;
      padding: 1rem;
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.25);
    }
    h1 {
      margin: 0 0 0.9rem 0;
      font-size: 1.35rem;
    }
    .tabs {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--border);
      margin-bottom: 1rem;
      padding-bottom: 0.8rem;
    }
    .tab {
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 8px;
      padding: 0.45rem 0.7rem;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
    }
    .tab.active {
      border-color: color-mix(in srgb, var(--accent) 65%, white 35%);
      background: color-mix(in srgb, var(--accent-2) 22%, var(--panel-2) 78%);
    }
    .panel {
      display: none;
    }
    .panel.active {
      display: block;
    }
    .grid {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 0.6rem;
      align-items: center;
      margin-bottom: 0.6rem;
    }
    input, select {
      width: 100%;
      box-sizing: border-box;
      border: 1px solid var(--border);
      background: #0a1324;
      color: var(--text);
      border-radius: 8px;
      padding: 0.5rem 0.6rem;
      font-size: 0.9rem;
    }
    button {
      border: 1px solid color-mix(in srgb, var(--accent) 75%, white 25%);
      background: color-mix(in srgb, var(--accent-2) 35%, #020617 65%);
      color: #ecfeff;
      border-radius: 8px;
      padding: 0.5rem 0.8rem;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
    }
    button:hover {
      filter: brightness(1.1);
    }
    button[disabled] {
      opacity: 0.45;
      cursor: default;
      filter: none;
    }
    .row-buttons {
      margin-top: 0.4rem;
      margin-bottom: 0.8rem;
      display: flex;
      gap: 0.45rem;
      align-items: center;
    }
    .muted { color: var(--muted); }
    .ok { color: var(--ok); }
    .err { color: var(--err); }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }
    th, td {
      border-bottom: 1px solid var(--border);
      text-align: left;
      padding: 0.45rem;
      vertical-align: top;
    }
    ul {
      margin-top: 0.5rem;
      padding-left: 1.25rem;
    }
    li {
      line-height: 1.35;
      margin-bottom: 0.35rem;
    }
    code {
      color: #67e8f9;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .split {
      display: grid;
      grid-template-columns: minmax(360px, 440px) minmax(0, 1fr);
      gap: 1.1rem;
      align-items: start;
    }
    .generation-class-wrapper {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.75rem;
      background: color-mix(in srgb, var(--panel-2) 70%, black 30%);
      margin-top: 0.8rem;
      margin-bottom: 0.8rem;
    }
    .generation-class-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.85rem;
      align-items: stretch;
    }
    .generation-class-grid-collapsed {
      display: none;
    }
    .generation-card {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.8rem;
      background: color-mix(in srgb, var(--panel-2) 84%, black 16%);
      min-height: 132px;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
    }
    .generation-card h3 {
      margin: 0;
      font-size: 0.95rem;
      letter-spacing: 0.01em;
    }
    .generation-card p {
      margin: 0;
      font-size: 0.86rem;
      line-height: 1.35;
    }
    .generation-card .generation-package-select {
      margin-top: 0.15rem;
    }
    .generation-card .generation-syllable-select {
      margin-top: 0.1rem;
    }
    .generation-card .generation-send-btn {
      align-self: flex-start;
      margin-top: 0.2rem;
    }
    .generation-placeholder {
      justify-content: center;
    }
    .generation-card-full-width {
      grid-column: 1 / -1;
    }
    .api-builder-layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 0.8rem;
      width: 100%;
    }
    .api-builder-pane {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.65rem;
      background: color-mix(in srgb, var(--panel-2) 78%, black 22%);
      min-height: 132px;
    }
    .api-builder-pane h4 {
      margin: 0 0 0.45rem 0;
      font-size: 0.88rem;
      letter-spacing: 0.01em;
    }
    #api-builder-queue {
      margin: 0;
      padding-left: 1.1rem;
    }
    #api-builder-combined {
      margin: 0.6rem 0 0 0;
      font-size: 0.84rem;
      color: var(--muted);
    }
    #api-builder-preview {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--muted);
      font-size: 0.83rem;
      line-height: 1.35;
    }
    .db-sidebar .grid {
      grid-template-columns: 90px 1fr;
    }
    .db-sidebar select {
      min-width: 0;
    }
    #db-table-list {
      margin-top: 0.6rem;
      margin-bottom: 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.65rem 0.8rem;
      max-height: 56vh;
      overflow: auto;
      background: color-mix(in srgb, var(--panel-2) 85%, black 15%);
    }
    #db-row-body td:first-child {
      width: 90px;
      white-space: nowrap;
    }
    .db-main table {
      table-layout: fixed;
    }
    .db-main .row-buttons {
      flex-wrap: wrap;
      gap: 0.55rem;
    }
    #db-page-status {
      margin-left: 0.15rem;
    }
    @media (max-width: 980px) {
      .split { grid-template-columns: 1fr; }
      .generation-class-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 800px) {
      .grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .generation-class-grid { grid-template-columns: 1fr; }
      .api-builder-layout { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Pipeworks Name Generator</h1>
      <div class="tabs">
        <button type="button" class="tab active" data-tab="import">Import</button>
        <button type="button" class="tab" data-tab="generation">Generation</button>
        <button type="button" class="tab" data-tab="database">Database View</button>
      </div>

      <section class="panel active" id="panel-import">
        <div class="grid">
          <label for="metadata-path">Metadata JSON Path</label>
          <input id="metadata-path" type="text" placeholder="/path/to/package_metadata.json" />
        </div>
        <div class="grid">
          <label for="zip-path">Package ZIP Path</label>
          <input id="zip-path" type="text" placeholder="/path/to/package.zip" />
        </div>
        <div class="row-buttons">
          <button type="button" id="import-btn">Import Pair</button>
        </div>
        <p id="import-status" class="muted">Waiting for input.</p>
      </section>

      <section class="panel" id="panel-generation">
        <article class="generation-card generation-placeholder generation-card-full-width">
          <h3>Generation Placeholder</h3>
          <p class="muted">Reserved for future blended generation controls.</p>
        </article>

        <section class="generation-class-wrapper generation-card-full-width">
          <div class="row-buttons">
            <button type="button" id="generation-toggle-btn">Show Name Class Cards</button>
            <span id="generation-toggle-status" class="muted">Cards collapsed to save vertical space.</span>
          </div>
          <div id="generation-class-card-section" class="generation-class-grid generation-class-grid-collapsed">
            <article class="generation-card generation-class-card" data-class-key="first_name">
              <h3>First Name</h3>
              <select id="generation-package-first_name" class="generation-package-select"></select>
              <select id="generation-syllables-first_name" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-first_name" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-first_name" class="muted">Loading package options...</p>
            </article>

            <article class="generation-card generation-class-card" data-class-key="last_name">
              <h3>Last Name</h3>
              <select id="generation-package-last_name" class="generation-package-select"></select>
              <select id="generation-syllables-last_name" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-last_name" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-last_name" class="muted">Loading package options...</p>
            </article>

            <article class="generation-card generation-class-card" data-class-key="place_name">
              <h3>Place Name</h3>
              <select id="generation-package-place_name" class="generation-package-select"></select>
              <select id="generation-syllables-place_name" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-place_name" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-place_name" class="muted">Loading package options...</p>
            </article>

            <article class="generation-card generation-class-card" data-class-key="location_name">
              <h3>Location Name</h3>
              <select id="generation-package-location_name" class="generation-package-select"></select>
              <select id="generation-syllables-location_name" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-location_name" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-location_name" class="muted">Loading package options...</p>
            </article>

            <article class="generation-card generation-class-card" data-class-key="object_item">
              <h3>Object Item</h3>
              <select id="generation-package-object_item" class="generation-package-select"></select>
              <select id="generation-syllables-object_item" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-object_item" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-object_item" class="muted">Loading package options...</p>
            </article>

            <article class="generation-card generation-class-card" data-class-key="organisation">
              <h3>Organisation</h3>
              <select id="generation-package-organisation" class="generation-package-select"></select>
              <select id="generation-syllables-organisation" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-organisation" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-organisation" class="muted">Loading package options...</p>
            </article>

            <article class="generation-card generation-class-card" data-class-key="title_epithet">
              <h3>Title Epithet</h3>
              <select id="generation-package-title_epithet" class="generation-package-select"></select>
              <select id="generation-syllables-title_epithet" class="generation-syllable-select"></select>
              <button type="button" id="generation-send-title_epithet" class="generation-send-btn">
                Send to API Builder
              </button>
              <p id="generation-note-title_epithet" class="muted">Loading package options...</p>
            </article>
          </div>
        </section>

        <article class="generation-card generation-placeholder generation-card-full-width">
          <h3>API Builder</h3>
          <div class="api-builder-layout">
            <section class="api-builder-pane">
              <h4>Selected Inputs</h4>
              <ul id="api-builder-queue"></ul>
              <p id="api-builder-combined">Combined unique combinations: 0</p>
            </section>
            <section class="api-builder-pane">
              <h4>Builder Preview</h4>
              <p id="api-builder-preview">No selections queued yet.</p>
            </section>
          </div>
        </article>
        <p id="generation-status" class="muted">Loading package options...</p>
      </section>

      <section class="panel" id="panel-database">
        <div class="split">
          <div class="db-sidebar">
            <div class="row-buttons">
              <button type="button" id="db-refresh-packages">Refresh Packages</button>
            </div>
            <div class="grid">
              <label for="db-package-select">Package</label>
              <select id="db-package-select"></select>
            </div>
            <div class="grid">
              <label for="db-table-select">Table</label>
              <select id="db-table-select"></select>
            </div>
            <p class="muted" id="db-status">Load packages to begin browsing.</p>
            <ul id="db-table-list"></ul>
          </div>
          <div class="db-main">
            <div class="row-buttons">
              <button type="button" id="db-prev-btn">Previous</button>
              <button type="button" id="db-next-btn">Next</button>
              <span id="db-page-status" class="muted">Rows 0-0</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Line</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody id="db-row-body"></tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  </div>

  <script>
    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll(\"'\", '&#39;');
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

    function renderApiBuilder() {
      const queue = document.getElementById('api-builder-queue');
      const preview = document.getElementById('api-builder-preview');
      const combined = document.getElementById('api-builder-combined');
      queue.innerHTML = '';

      if (!apiBuilderSelections.length) {
        const li = document.createElement('li');
        li.className = 'muted';
        li.textContent = 'No selections queued.';
        queue.appendChild(li);
        combined.textContent = 'Combined unique combinations: 0';
        preview.textContent = 'No selections queued yet.';
        return;
      }

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

      const combinedDisplay = String(combinedUnique).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
      combined.textContent = `Combined unique combinations: ${combinedDisplay}`;
      preview.textContent = JSON.stringify(apiBuilderSelections, null, 2);
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
          `<span class=\"muted\">(${table.row_count} rows)</span></div>` +
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

    loadPackages();
    loadGenerationPackageOptions();
    renderApiBuilder();
    setGenerationCardsCollapsed(true);
  </script>
</body>
</html>
"""

SAMPLE_SYLLABLES = [
    "zor",
    "mok",
    "dra",
    "ven",
    "tal",
    "rik",
    "sul",
    "nor",
    "kai",
    "bel",
    "esh",
    "grim",
]

# Canonical class keys and labels used by the Generation tab card layout.
GENERATION_NAME_CLASSES: list[tuple[str, str]] = [
    ("first_name", "First Name"),
    ("last_name", "Last Name"),
    ("place_name", "Place Name"),
    ("location_name", "Location Name"),
    ("object_item", "Object Item"),
    ("organisation", "Organisation"),
    ("title_epithet", "Title Epithet"),
]

# Filename pattern hints used to map imported txt source files to generation
# classes. Patterns are compared against a normalized lowercase stem.
GENERATION_CLASS_PATTERNS: dict[str, tuple[str, ...]] = {
    "first_name": ("first_name",),
    "last_name": ("last_name",),
    "place_name": ("place_name",),
    "location_name": ("location_name",),
    "object_item": ("object_item", "object_name"),
    "organisation": ("organisation", "organization", "org_name"),
    "title_epithet": ("title_epithet", "epithet"),
}

GENERATION_CLASS_KEYS: set[str] = {key for key, _ in GENERATION_NAME_CLASSES}

# Display labels for normalized syllable mode keys presented in the UI.
GENERATION_SYLLABLE_LABELS: dict[str, str] = {
    "2syl": "2 syllables",
    "3syl": "3 syllables",
    "4syl": "4 syllables",
    "all": "All syllables",
}


class WebAppHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the tabbed web UI and JSON API.

    The handler serves one static HTML page and a small set of JSON endpoints:

    - ``GET /``: Web UI shell
    - ``GET /api/health``: Liveness check
    - ``GET /api/generation/package-options``: Per-class package dropdown options
    - ``GET /api/generation/package-syllables``: Syllable options for one package/class
    - ``GET /api/generation/selection-stats``: Max item/unique limits for one selection
    - ``GET /api/database/packages``: Imported package list
    - ``GET /api/database/package-tables``: Table list for one package
    - ``GET /api/database/table-rows``: Paginated rows for one table
    - ``POST /api/import``: Import metadata+zip package pair
    - ``POST /api/generate``: Return placeholder generated names

    Class attributes ``verbose`` and ``db_path`` are injected at startup by
    :func:`create_handler_class`, which allows one handler implementation to be
    reused with per-process runtime settings.
    """

    verbose: bool = True
    db_path: Path = Path("pipeworks_name_generation/data/name_packages.sqlite3")

    def log_message(self, format: str, *args: Any) -> None:
        """Keep request logging optional."""
        if self.verbose:
            super().log_message(format, *args)

    def _send_text(self, content: str, status: int = 200, content_type: str = "text/plain") -> None:
        """Send a UTF-8 text response."""
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        """Send a JSON response."""
        self._send_text(json.dumps(payload), status=status, content_type="application/json")

    def _read_json_body(self) -> dict[str, Any]:
        """Read request JSON body and return object payload."""
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length header.") from exc

        if content_length <= 0:
            raise ValueError("Request body is required.")

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        """Handle all supported ``GET`` routes.

        Response behavior:

        - Returns ``200`` with HTML for ``/``.
        - Returns ``200`` with JSON for known API routes.
        - Returns ``204`` for ``/favicon.ico`` to avoid browser noise.
        - Returns ``404`` for unknown paths.
        """
        parsed = urlsplit(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        if route == "/":
            self._send_text(HTML_TEMPLATE, content_type="text/html")
            return

        if route == "/api/health":
            self._send_json({"ok": True})
            return

        if route == "/api/generation/package-options":
            try:
                with _connect_database(self.db_path) as conn:
                    _initialize_schema(conn)
                    name_classes = _list_generation_package_options(conn)
                self._send_json({"name_classes": name_classes})
            except Exception as exc:  # nosec B110 - converted into controlled API response
                self._send_json(
                    {"error": f"Failed to list generation package options: {exc}"},
                    status=500,
                )
            return

        if route == "/api/generation/package-syllables":
            try:
                package_id = _parse_required_int(query, "package_id", minimum=1)
                class_values = query.get("class_key", [])
                class_key = class_values[0].strip() if class_values else ""
                if not class_key:
                    raise ValueError("Missing required query parameter: class_key")
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            try:
                with _connect_database(self.db_path) as conn:
                    _initialize_schema(conn)
                    syllable_options = _list_generation_syllable_options(
                        conn,
                        class_key=class_key,
                        package_id=package_id,
                    )
                self._send_json(
                    {
                        "class_key": class_key,
                        "package_id": package_id,
                        "syllable_options": syllable_options,
                    }
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:  # nosec B110 - converted into controlled API response
                self._send_json(
                    {"error": f"Failed to list generation syllable options: {exc}"},
                    status=500,
                )
            return

        if route == "/api/generation/selection-stats":
            try:
                package_id = _parse_required_int(query, "package_id", minimum=1)
                class_values = query.get("class_key", [])
                class_key = class_values[0].strip() if class_values else ""
                if not class_key:
                    raise ValueError("Missing required query parameter: class_key")

                syllable_values = query.get("syllable_key", [])
                syllable_key = syllable_values[0].strip() if syllable_values else ""
                if not syllable_key:
                    raise ValueError("Missing required query parameter: syllable_key")
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            try:
                with _connect_database(self.db_path) as conn:
                    _initialize_schema(conn)
                    stats = _get_generation_selection_stats(
                        conn,
                        class_key=class_key,
                        package_id=package_id,
                        syllable_key=syllable_key,
                    )
                self._send_json(
                    {
                        "class_key": class_key,
                        "package_id": package_id,
                        "syllable_key": syllable_key,
                        **stats,
                    }
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
            except Exception as exc:  # nosec B110 - converted into controlled API response
                self._send_json(
                    {"error": f"Failed to compute generation selection stats: {exc}"},
                    status=500,
                )
            return

        if route == "/api/database/packages":
            try:
                with _connect_database(self.db_path) as conn:
                    _initialize_schema(conn)
                    packages = _list_packages(conn)
                self._send_json({"packages": packages, "db_path": str(self.db_path)})
            except Exception as exc:  # nosec B110 - converted into controlled API response
                self._send_json({"error": f"Failed to list packages: {exc}"}, status=500)
            return

        if route == "/api/database/package-tables":
            try:
                package_id = _parse_required_int(query, "package_id", minimum=1)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            try:
                with _connect_database(self.db_path) as conn:
                    _initialize_schema(conn)
                    tables = _list_package_tables(conn, package_id)
                self._send_json({"tables": tables})
            except Exception as exc:  # nosec B110 - converted into controlled API response
                self._send_json({"error": f"Failed to list package tables: {exc}"}, status=500)
            return

        if route == "/api/database/table-rows":
            try:
                table_id = _parse_required_int(query, "table_id", minimum=1)
                offset = _parse_optional_int(query, "offset", default=0, minimum=0)
                limit = _parse_optional_int(
                    query,
                    "limit",
                    default=DEFAULT_PAGE_LIMIT,
                    minimum=1,
                    maximum=MAX_PAGE_LIMIT,
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            try:
                with _connect_database(self.db_path) as conn:
                    _initialize_schema(conn)
                    table_meta = _get_package_table(conn, table_id)
                    if table_meta is None:
                        self._send_json({"error": "Table id not found."}, status=404)
                        return

                    rows = _fetch_text_rows(
                        conn, table_meta["table_name"], offset=offset, limit=limit
                    )
                    self._send_json(
                        {
                            "table": table_meta,
                            "rows": rows,
                            "offset": offset,
                            "limit": limit,
                            "total_rows": table_meta["row_count"],
                        }
                    )
            except Exception as exc:  # nosec B110 - converted into controlled API response
                self._send_json({"error": f"Failed to load table rows: {exc}"}, status=500)
            return

        if route == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        """Handle all supported ``POST`` routes.

        Delegates to route-specific helpers so payload parsing and validation
        stay isolated from top-level route dispatch.
        """
        if self.path == "/api/import":
            self._handle_import()
            return

        if self.path == "/api/generate":
            self._handle_generation()
            return

        self.send_error(404, "Not Found")

    def _handle_import(self) -> None:
        """Import one metadata+zip pair and create tables for included txt data.

        Expected JSON payload keys:

        - ``metadata_json_path``: Filesystem path to package metadata JSON
        - ``package_zip_path``: Filesystem path to package zip archive

        Returns ``200`` with import summary JSON on success. Returns ``400`` for
        validation/input errors and ``500`` for unexpected runtime failures.
        """
        try:
            payload = self._read_json_body()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        metadata_raw = str(payload.get("metadata_json_path", "")).strip()
        zip_raw = str(payload.get("package_zip_path", "")).strip()
        if not metadata_raw or not zip_raw:
            self._send_json(
                {"error": "Both 'metadata_json_path' and 'package_zip_path' are required."},
                status=400,
            )
            return

        metadata_path = Path(metadata_raw).expanduser()
        zip_path = Path(zip_raw).expanduser()

        try:
            with _connect_database(self.db_path) as conn:
                _initialize_schema(conn)
                result = _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)
            self._send_json(result)
        except (FileNotFoundError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # nosec B110 - converted into controlled API response
            self._send_json({"error": f"Import failed: {exc}"}, status=500)

    def _handle_generation(self) -> None:
        """Generate a deterministic placeholder list for the Generation tab.

        Expected JSON payload keys:

        - ``name_class``: Logical class label (for deterministic variation)
        - ``count``: Requested output size (clamped to ``1..20``)
        """
        try:
            payload = self._read_json_body()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        name_class = str(payload.get("name_class", "first_name")).strip() or "first_name"
        raw_count = payload.get("count", 5)
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            self._send_json({"error": "Field 'count' must be an integer."}, status=400)
            return

        count = max(1, min(20, count))
        names = _generate_placeholder_names(name_class, count)
        self._send_json(
            {
                "message": f"Generated {len(names)} placeholder name(s) for {name_class}.",
                "names": names,
            }
        )


def _generate_placeholder_names(name_class: str, count: int) -> list[str]:
    """Generate deterministic placeholder names for the Generation tab."""
    names: list[str] = []
    for index in range(count):
        # Use a stable hash per position to keep output deterministic without
        # depending on pseudo-random generators.
        digest = hashlib.sha256(f"{name_class}:{index}".encode("utf-8")).digest()
        pieces = 2 + (digest[0] % 2)
        syllables = [
            SAMPLE_SYLLABLES[digest[offset] % len(SAMPLE_SYLLABLES)]
            for offset in range(1, pieces + 1)
        ]
        names.append("".join(syllables))
    return names


def _connect_database(db_path: Path) -> sqlite3.Connection:
    """Connect to SQLite and prepare runtime defaults."""
    resolved = db_path.expanduser()
    if resolved.parent and str(resolved.parent) != ".":
        resolved.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _initialize_schema(conn: sqlite3.Connection) -> None:
    """Create metadata tables used by import and database browsing."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS imported_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            metadata_json_path TEXT NOT NULL,
            package_zip_path TEXT NOT NULL,
            UNIQUE(metadata_json_path, package_zip_path)
        );

        CREATE TABLE IF NOT EXISTS package_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            source_txt_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(package_id) REFERENCES imported_packages(id) ON DELETE CASCADE,
            UNIQUE(package_id, source_txt_name)
        );
        """)
    conn.commit()


def _import_package_pair(
    conn: sqlite3.Connection, *, metadata_path: Path, zip_path: Path
) -> dict[str, Any]:
    """Import one metadata+zip pair and create one SQLite table per ``*.txt``.

    The importer currently ignores JSON files inside the archive. It uses the
    metadata ``files_included`` list (when provided) to limit which ``*.txt``
    entries are imported. Each imported txt file becomes its own physical
    SQLite table, with one row per non-empty line.

    Args:
        conn: Open SQLite connection.
        metadata_path: Path to ``*_metadata.json`` file.
        zip_path: Path to package zip file.

    Returns:
        API-style summary payload describing imported package and created tables.

    Raises:
        FileNotFoundError: If metadata or zip path does not exist.
        ValueError: For invalid metadata, duplicate imports, or zip format/data
            issues.
    """
    metadata_resolved = metadata_path.resolve()
    zip_resolved = zip_path.resolve()

    if not metadata_resolved.exists():
        raise FileNotFoundError(f"Metadata JSON does not exist: {metadata_resolved}")
    if not zip_resolved.exists():
        raise FileNotFoundError(f"Package ZIP does not exist: {zip_resolved}")

    payload = _load_metadata_json(metadata_resolved)
    package_name = str(payload.get("common_name", "")).strip() or zip_resolved.stem

    raw_files_included = payload.get("files_included")
    if raw_files_included is None:
        files_included: list[Any] = []
    elif isinstance(raw_files_included, list):
        files_included = raw_files_included
    else:
        raise ValueError("Metadata key 'files_included' must be a list when provided.")

    allowed_txt_names = {
        str(name).strip() for name in files_included if str(name).strip().lower().endswith(".txt")
    }

    try:
        with zipfile.ZipFile(zip_resolved, "r") as archive:
            entries = sorted(
                name
                for name in archive.namelist()
                if not name.endswith("/") and name.lower().endswith(".txt")
            )

            # Restrict to metadata listed txt files when the list is present.
            if allowed_txt_names:
                entries = [entry for entry in entries if Path(entry).name in allowed_txt_names]

            cursor = conn.execute(
                """
                INSERT INTO imported_packages (
                    package_name,
                    imported_at,
                    metadata_json_path,
                    package_zip_path
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    package_name,
                    datetime.now(timezone.utc).isoformat(),
                    str(metadata_resolved),
                    str(zip_resolved),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return a row id for imported package insert.")
            package_id = int(cursor.lastrowid)

            created_tables: list[dict[str, Any]] = []
            for index, entry_name in enumerate(entries, start=1):
                txt_rows = _read_txt_rows(archive, entry_name)
                table_name = _build_package_table_name(
                    package_name, Path(entry_name).stem, package_id, index
                )
                _create_text_table(conn, table_name)
                _insert_text_rows(conn, table_name, txt_rows)

                conn.execute(
                    """
                    INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (package_id, Path(entry_name).name, table_name, len(txt_rows)),
                )
                created_tables.append(
                    {
                        "source_txt_name": Path(entry_name).name,
                        "table_name": table_name,
                        "row_count": len(txt_rows),
                    }
                )

            conn.commit()
            return {
                "message": (
                    f"Imported package '{package_name}' with {len(created_tables)} txt table(s)."
                ),
                "package_id": package_id,
                "package_name": package_name,
                "tables": created_tables,
            }
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("This metadata/zip pair has already been imported.") from exc
    except zipfile.BadZipFile as exc:
        conn.rollback()
        raise ValueError(f"Invalid ZIP file: {zip_resolved}") from exc
    except Exception:
        conn.rollback()
        raise


def _load_metadata_json(metadata_path: Path) -> dict[str, Any]:
    """Load metadata JSON and enforce object-root structure.

    Args:
        metadata_path: Path to metadata JSON file.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: If the root JSON value is not an object.
    """
    with open(metadata_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Metadata JSON root must be an object.")
    return payload


def _read_txt_rows(archive: zipfile.ZipFile, entry_name: str) -> list[tuple[int, str]]:
    """Read one txt entry and return ``(line_number, value)`` tuples.

    Empty/whitespace-only lines are skipped during import so DB tables contain
    meaningful values only.
    """
    try:
        payload = archive.read(entry_name)
    except KeyError as exc:
        raise ValueError(f"TXT entry missing from zip: {entry_name}") from exc

    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"TXT entry is not valid UTF-8: {entry_name}") from exc

    rows: list[tuple[int, str]] = []
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        rows.append((line_number, text))
    return rows


def _build_package_table_name(package_name: str, txt_stem: str, package_id: int, index: int) -> str:
    """Create a safe SQLite table name that references package and txt source."""
    package_slug = _slugify_identifier(package_name, max_length=24)
    txt_slug = _slugify_identifier(txt_stem, max_length=24)
    return f"pkg_{package_id}_{package_slug}_{txt_slug}_{index}"


def _slugify_identifier(value: str, max_length: int) -> str:
    """Convert free text into an ASCII-safe SQL identifier chunk."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    slug = slug[:max_length].strip("_")
    if not slug:
        slug = "item"
    if slug[0].isdigit():
        slug = f"n_{slug}"
    return slug


def _quote_identifier(identifier: str) -> str:
    """Validate and quote a SQLite identifier."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier!r}")
    return f'"{identifier}"'


def _create_text_table(conn: sqlite3.Connection, table_name: str) -> None:
    """Create one physical text table for imported txt rows.

    The table schema is intentionally minimal:

    - ``id``: surrogate primary key
    - ``line_number``: source txt line number
    - ``value``: trimmed non-empty line value
    """
    quoted = _quote_identifier(table_name)
    query = f"""
        CREATE TABLE IF NOT EXISTS {quoted} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_number INTEGER NOT NULL,
            value TEXT NOT NULL
        )
        """
    conn.execute(query)


def _insert_text_rows(
    conn: sqlite3.Connection, table_name: str, rows: list[tuple[int, str]]
) -> None:
    """Insert parsed txt rows into the target physical table."""
    if not rows:
        return

    quoted = _quote_identifier(table_name)
    query = f"""
        INSERT INTO {quoted} (line_number, value)
        VALUES (?, ?)
        """  # nosec B608
    conn.executemany(
        query,
        rows,
    )


def _map_source_txt_name_to_generation_class(source_txt_name: str) -> str | None:
    """Map one imported txt filename to a canonical generation class key.

    The source filename stem is normalized to lowercase ``snake_case`` before
    matching against known pattern hints for each Generation tab class.

    Args:
        source_txt_name: Imported ``*.txt`` source filename.

    Returns:
        Canonical generation class key, or ``None`` when no mapping is known.
    """
    normalized = re.sub(r"[^a-z0-9]+", "_", Path(source_txt_name).stem.lower()).strip("_")
    for class_key, patterns in GENERATION_CLASS_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            return class_key
    return None


def _extract_syllable_option_from_source_txt_name(source_txt_name: str) -> str | None:
    """Extract normalized syllable option key from one source txt filename.

    Supported values are keys like ``2syl``, ``3syl``, ``4syl``, and ``all``
    derived from common source filename conventions (for example
    ``nltk_first_name_2syl.txt`` or ``nltk_first_name_all.txt``).

    Args:
        source_txt_name: Imported ``*.txt`` source filename.

    Returns:
        Normalized syllable option key, or ``None`` when no known mode exists.
    """
    normalized = re.sub(r"[^a-z0-9]+", "_", Path(source_txt_name).stem.lower()).strip("_")
    if "_all" in normalized or normalized.endswith("all"):
        return "all"

    match = re.search(r"_(\d+)syl(?:_|$)", normalized)
    if match:
        return f"{match.group(1)}syl"

    return None


def _syllable_option_sort_key(option_key: str) -> tuple[int, int, str]:
    """Return deterministic sort key for syllable option keys.

    Numeric options (for example ``2syl``) are sorted by number first, followed
    by non-numeric options such as ``all``.
    """
    if option_key == "all":
        return (1, 9999, option_key)

    match = re.fullmatch(r"(\d+)syl", option_key)
    if match:
        return (0, int(match.group(1)), option_key)

    return (2, 9999, option_key)


def _list_generation_syllable_options(
    conn: sqlite3.Connection, *, class_key: str, package_id: int
) -> list[dict[str, str]]:
    """List syllable options for one package within one generation class.

    Args:
        conn: Open SQLite connection.
        class_key: Canonical generation class key.
        package_id: Imported package id.

    Returns:
        Sorted syllable option dictionaries with ``key`` and ``label`` values.

    Raises:
        ValueError: If ``class_key`` is not one of the supported generation
            classes.
    """
    if class_key not in GENERATION_CLASS_KEYS:
        raise ValueError(f"Unsupported generation class_key: {class_key!r}")

    rows = conn.execute(
        """
        SELECT source_txt_name
        FROM package_tables
        WHERE package_id = ?
        ORDER BY source_txt_name COLLATE NOCASE
        """,
        (package_id,),
    ).fetchall()

    option_keys: set[str] = set()
    for row in rows:
        source_txt_name = str(row["source_txt_name"])
        mapped_class = _map_source_txt_name_to_generation_class(source_txt_name)
        if mapped_class != class_key:
            continue

        option_key = _extract_syllable_option_from_source_txt_name(source_txt_name)
        if option_key is None:
            continue
        option_keys.add(option_key)

    sorted_keys = sorted(option_keys, key=_syllable_option_sort_key)
    return [{"key": key, "label": GENERATION_SYLLABLE_LABELS.get(key, key)} for key in sorted_keys]


def _validate_generation_syllable_key(syllable_key: str) -> str:
    """Validate and normalize one generation syllable mode key.

    Accepted values are ``all`` or a numeric ``Nsyl`` shape (for example
    ``2syl``). Invalid values fail fast so API callers receive a clear,
    deterministic validation error.

    Args:
        syllable_key: Raw syllable key string from API query.

    Returns:
        Lower-cased, validated syllable key.

    Raises:
        ValueError: If the key does not match supported syllable modes.
    """
    normalized = syllable_key.strip().lower()
    if normalized == "all":
        return normalized
    if re.fullmatch(r"\d+syl", normalized):
        return normalized
    raise ValueError(f"Unsupported generation syllable_key: {syllable_key!r}")


def _list_generation_matching_tables(
    conn: sqlite3.Connection, *, class_key: str, package_id: int, syllable_key: str
) -> list[dict[str, Any]]:
    """List imported txt tables matching one generation class+syllable filter.

    The filter is based on each ``package_tables.source_txt_name`` value:
    filename patterns are mapped to canonical class keys and syllable keys, and
    only exact matches are returned.

    Args:
        conn: Open SQLite connection.
        class_key: Canonical generation class key.
        package_id: Imported package id.
        syllable_key: Validated syllable option key (for example ``2syl``).

    Returns:
        Matching table metadata dictionaries with ``table_name`` and
        ``row_count`` values.

    Raises:
        ValueError: If ``class_key`` or ``syllable_key`` is unsupported.
    """
    if class_key not in GENERATION_CLASS_KEYS:
        raise ValueError(f"Unsupported generation class_key: {class_key!r}")
    normalized_syllable_key = _validate_generation_syllable_key(syllable_key)

    rows = conn.execute(
        """
        SELECT source_txt_name, table_name, row_count
        FROM package_tables
        WHERE package_id = ?
        ORDER BY source_txt_name COLLATE NOCASE
        """,
        (package_id,),
    ).fetchall()

    matches: list[dict[str, Any]] = []
    for row in rows:
        source_txt_name = str(row["source_txt_name"])
        mapped_class = _map_source_txt_name_to_generation_class(source_txt_name)
        if mapped_class != class_key:
            continue

        mapped_syllable = _extract_syllable_option_from_source_txt_name(source_txt_name)
        if mapped_syllable != normalized_syllable_key:
            continue

        matches.append(
            {
                "source_txt_name": source_txt_name,
                "table_name": str(row["table_name"]),
                "row_count": int(row["row_count"]),
            }
        )

    return matches


def _count_distinct_values_across_tables(
    conn: sqlite3.Connection, table_names: Sequence[str]
) -> int:
    """Count distinct ``value`` strings across one or more imported txt tables.

    Args:
        conn: Open SQLite connection.
        table_names: Physical table names to include in the distinct count.

    Returns:
        Count of unique ``value`` strings across all listed tables.
    """
    if not table_names:
        return 0

    unique_values: set[str] = set()
    for table_name in table_names:
        quoted = _quote_identifier(table_name)
        query = f"SELECT value FROM {quoted}"  # nosec B608
        rows = conn.execute(query).fetchall()
        for row in rows:
            unique_values.add(str(row["value"]))
    return len(unique_values)


def _get_generation_selection_stats(
    conn: sqlite3.Connection, *, class_key: str, package_id: int, syllable_key: str
) -> dict[str, int]:
    """Compute size/uniqueness limits for one Generation card selection.

    Args:
        conn: Open SQLite connection.
        class_key: Canonical generation class key.
        package_id: Imported package id.
        syllable_key: Syllable mode key selected by the user.

    Returns:
        Dictionary with:
        - ``max_items``: Total available rows across matching table(s).
        - ``max_unique_combinations``: Distinct values across matching table(s).
    """
    matching_tables = _list_generation_matching_tables(
        conn,
        class_key=class_key,
        package_id=package_id,
        syllable_key=syllable_key,
    )
    if not matching_tables:
        return {"max_items": 0, "max_unique_combinations": 0}

    max_items = sum(int(item["row_count"]) for item in matching_tables)
    table_names = [str(item["table_name"]) for item in matching_tables]
    max_unique_combinations = _count_distinct_values_across_tables(conn, table_names)
    return {
        "max_items": max_items,
        "max_unique_combinations": max_unique_combinations,
    }


def _list_generation_package_options(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return per-class package options for Generation tab dropdown cards.

    The response is intentionally grouped by canonical generation class. Each
    class includes packages that currently have at least one imported txt source
    file mapping to that class.

    Args:
        conn: Open SQLite connection.

    Returns:
        List of class dictionaries with package option entries.
    """
    rows = conn.execute("""
        SELECT
            p.id AS package_id,
            p.package_name,
            t.source_txt_name
        FROM imported_packages AS p
        INNER JOIN package_tables AS t ON t.package_id = p.id
        ORDER BY p.package_name COLLATE NOCASE, p.id, t.source_txt_name COLLATE NOCASE
        """).fetchall()

    per_class: dict[str, dict[int, dict[str, Any]]] = {
        class_key: {} for class_key, _ in GENERATION_NAME_CLASSES
    }
    for row in rows:
        class_key = _map_source_txt_name_to_generation_class(str(row["source_txt_name"]))
        if class_key is None:
            continue

        package_id = int(row["package_id"])
        package_name = str(row["package_name"])
        source_txt_name = str(row["source_txt_name"])

        existing = per_class[class_key].get(package_id)
        if existing is None:
            per_class[class_key][package_id] = {
                "package_id": package_id,
                "package_name": package_name,
                "source_txt_names": [source_txt_name],
            }
            continue

        existing["source_txt_names"].append(source_txt_name)

    result: list[dict[str, Any]] = []
    for class_key, label in GENERATION_NAME_CLASSES:
        packages = list(per_class[class_key].values())
        packages.sort(key=lambda item: (str(item["package_name"]).lower(), int(item["package_id"])))
        for package in packages:
            deduped_sources = sorted({str(name) for name in package["source_txt_names"]})
            package["source_txt_names"] = deduped_sources
        result.append({"key": class_key, "label": label, "packages": packages})

    return result


def _list_packages(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return imported package list for the Database View tab."""
    rows = conn.execute("""
        SELECT id, package_name, imported_at
        FROM imported_packages
        ORDER BY id DESC
        """).fetchall()
    return [
        {
            "id": int(row["id"]),
            "package_name": str(row["package_name"]),
            "imported_at": str(row["imported_at"]),
        }
        for row in rows
    ]


def _list_package_tables(conn: sqlite3.Connection, package_id: int) -> list[dict[str, Any]]:
    """Return txt tables for one package id."""
    rows = conn.execute(
        """
        SELECT id, source_txt_name, table_name, row_count
        FROM package_tables
        WHERE package_id = ?
        ORDER BY source_txt_name
        """,
        (package_id,),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "source_txt_name": str(row["source_txt_name"]),
            "table_name": str(row["table_name"]),
            "row_count": int(row["row_count"]),
        }
        for row in rows
    ]


def _get_package_table(conn: sqlite3.Connection, table_id: int) -> dict[str, Any] | None:
    """Return one package table metadata row by id."""
    row = conn.execute(
        """
        SELECT id, package_id, source_txt_name, table_name, row_count
        FROM package_tables
        WHERE id = ?
        """,
        (table_id,),
    ).fetchone()
    if row is None:
        return None

    return {
        "id": int(row["id"]),
        "package_id": int(row["package_id"]),
        "source_txt_name": str(row["source_txt_name"]),
        "table_name": str(row["table_name"]),
        "row_count": int(row["row_count"]),
    }


def _fetch_text_rows(
    conn: sqlite3.Connection,
    table_name: str,
    *,
    offset: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch paginated rows from one physical txt table.

    Args:
        conn: Open SQLite connection.
        table_name: Validated physical table name.
        offset: Zero-based row offset.
        limit: Maximum rows to return.

    Returns:
        List of ``{"line_number": int, "value": str}`` mappings.
    """
    quoted = _quote_identifier(table_name)
    query = f"""
        SELECT line_number, value
        FROM {quoted}
        ORDER BY line_number, id
        LIMIT ? OFFSET ?
        """  # nosec B608
    rows = conn.execute(
        query,
        (limit, offset),
    ).fetchall()
    return [
        {
            "line_number": int(row["line_number"]),
            "value": str(row["value"]),
        }
        for row in rows
    ]


def _parse_required_int(
    query: dict[str, list[str]],
    key: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse a required integer query parameter."""
    values = query.get(key, [])
    if not values or not values[0].strip():
        raise ValueError(f"Missing required query parameter: {key}")
    return _coerce_int(values[0], key=key, minimum=minimum, maximum=maximum)


def _parse_optional_int(
    query: dict[str, list[str]],
    key: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse an optional integer query parameter."""
    values = query.get(key, [])
    if not values or not values[0].strip():
        return default
    return _coerce_int(values[0], key=key, minimum=minimum, maximum=maximum)


def _coerce_int(
    raw: str,
    *,
    key: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Convert string to bounded integer with useful error messages."""
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Query parameter '{key}' must be an integer.") from exc

    if minimum is not None and value < minimum:
        raise ValueError(f"Query parameter '{key}' must be >= {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"Query parameter '{key}' must be <= {maximum}.")
    return value


def _port_is_available(host: str, port: int) -> bool:
    """Return ``True`` when a host/port can be bound by this process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(host: str = "127.0.0.1", start: int = 8000, end: int = 8999) -> int:
    """Find the first available TCP port in ``start..end``.

    Raises:
        OSError: When no free port is available in the given range.
    """
    for port in range(start, end + 1):
        if _port_is_available(host, port):
            return port
    raise OSError(f"No free ports available in range {start}-{end}.")


def resolve_server_port(host: str, configured_port: int | None) -> int:
    """Resolve runtime port using manual config or auto-discovery.

    Args:
        host: Bind host for availability checks.
        configured_port: Optional explicit port from config/CLI.

    Returns:
        Concrete port to bind.

    Raises:
        OSError: If a configured port is unavailable or no auto port is free.
    """
    if configured_port is not None:
        if not _port_is_available(host, configured_port):
            raise OSError(f"Configured port {configured_port} is already in use.")
        return configured_port
    return find_available_port(host=host, start=8000, end=8999)


def create_handler_class(verbose: bool, db_path: Path) -> type[WebAppHandler]:
    """Create handler class bound to runtime verbosity and DB path."""

    class BoundHandler(WebAppHandler):
        pass

    BoundHandler.verbose = verbose
    BoundHandler.db_path = db_path
    return BoundHandler


def start_http_server(settings: ServerSettings) -> tuple[HTTPServer, int]:
    """Create a configured ``HTTPServer`` instance."""
    port = resolve_server_port(settings.host, settings.port)
    handler_class = create_handler_class(settings.verbose, settings.db_path)
    server = HTTPServer((settings.host, port), handler_class)
    return server, port


def run_server(settings: ServerSettings) -> int:
    """Run the server until interrupted.

    Args:
        settings: Effective runtime settings from config and CLI overrides.

    Returns:
        Process-style exit code (``0`` on normal shutdown).
    """
    server, port = start_http_server(settings)

    if settings.verbose:
        print(f"Serving Pipeworks Name Generator UI at http://{settings.host}:{port}")
        print(f"SQLite DB path: {settings.db_path}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if settings.verbose:
            print("\\nStopping server...")
    finally:
        server.server_close()

    return 0


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for this server."""
    parser = argparse.ArgumentParser(
        prog="pipeworks-name-webapp",
        description="Run the simple Pipeworks Name Generator web server.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("server.ini"),
        help="Path to INI config file (default: server.ini)",
    )
    parser.add_argument("--host", type=str, default=None, help="Override server host.")
    parser.add_argument("--port", type=int, default=None, help="Override server port.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable verbose startup/request logs.",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = create_argument_parser()
    return parser.parse_args(list(argv) if argv is not None else None)


def build_settings_from_args(args: argparse.Namespace) -> ServerSettings:
    """Build effective settings from INI config and CLI overrides."""
    config_path = args.config if isinstance(args.config, Path) else Path(args.config)
    loaded = load_server_settings(config_path)
    verbose_override = False if args.quiet else None
    return apply_runtime_overrides(
        loaded,
        host=args.host,
        port=args.port,
        db_path=None,
        verbose=verbose_override,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for running this server."""
    try:
        args = parse_arguments(argv)
        settings = build_settings_from_args(args)
        return run_server(settings)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
