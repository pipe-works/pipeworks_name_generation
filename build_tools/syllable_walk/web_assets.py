"""Static web assets for the simplified syllable walker web interface.

This module contains HTML and CSS templates embedded as Python strings for the
simplified web interface that focuses on selections browsing and basic walks.

The embedded assets provide:
- HTML_TEMPLATE: Single-page application with selections browser and walk generator
- CSS_CONTENT: Minimal stylesheet using system preferences for dark/light mode
"""

# HTML template for the simplified web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Syllable Walker</title>
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Syllable Walker</h1>
            <p>Browse name selections and explore phonetic space</p>
        </header>

        <section class="run-selector">
            <label for="run-select">Pipeline Run:</label>
            <select id="run-select" onchange="selectRun()">
                <option value="">Loading runs...</option>
            </select>
            <span id="run-info" class="run-info"></span>
        </section>

        <section class="selections-section">
            <h2>Name Selections</h2>
            <div class="tab-bar" id="selection-tabs">
                <!-- Tabs populated dynamically -->
            </div>
            <div id="selection-content" class="selection-content">
                <p class="placeholder">Select a run to view selections</p>
            </div>
            <div id="selection-meta" class="selection-meta"></div>
        </section>

        <section class="walk-section">
            <h2>Quick Walk</h2>
            <div class="walk-controls">
                <div class="control-row">
                    <label for="start-syllable">Start:</label>
                    <input type="text" id="start-syllable" placeholder="random">
                </div>
                <div class="control-row">
                    <label for="walk-profile">Profile:</label>
                    <select id="walk-profile">
                        <option value="clerical">Clerical (Conservative)</option>
                        <option value="dialect" selected>Dialect (Balanced)</option>
                        <option value="goblin">Goblin (Chaotic)</option>
                        <option value="ritual">Ritual (Extreme)</option>
                    </select>
                </div>
                <button id="walk-btn" onclick="generateWalk()" disabled>Generate Walk</button>
            </div>
            <div id="walk-result" class="walk-result">
                <p class="placeholder">Select a run first</p>
            </div>
        </section>
    </div>

    <script>
        // State
        let runs = [];
        let currentRun = null;
        let currentSelections = {};
        let activeTab = null;

        // Load available runs on page load
        async function loadRuns() {
            try {
                const response = await fetch('/api/runs');
                const data = await response.json();
                runs = data.runs;
                currentRun = data.current_run;

                const select = document.getElementById('run-select');
                select.innerHTML = '';

                if (runs.length === 0) {
                    select.innerHTML = '<option value="">No runs found</option>';
                    return;
                }

                runs.forEach(run => {
                    const option = document.createElement('option');
                    option.value = run.path;
                    option.textContent = run.display_name;
                    option.dataset.runId = run.path.split('/').pop();
                    select.appendChild(option);
                });

                // Select first run by default
                if (runs.length > 0) {
                    select.value = runs[0].path;
                    await selectRun();
                }
            } catch (error) {
                console.error('Error loading runs:', error);
                document.getElementById('run-select').innerHTML =
                    '<option value="">Error loading runs</option>';
            }
        }

        // Handle run selection
        async function selectRun() {
            const select = document.getElementById('run-select');
            const selectedOption = select.selectedOptions[0];
            if (!selectedOption || !selectedOption.dataset.runId) return;

            const runId = selectedOption.dataset.runId;
            const runData = runs.find(r => r.path.endsWith(runId));
            if (!runData) return;

            // Update run info
            const infoEl = document.getElementById('run-info');
            infoEl.textContent = `${runData.syllable_count.toLocaleString()} syllables`;

            // Update selection tabs
            updateSelectionTabs(runData);

            // Load walker for this run
            await loadWalker(runId);
        }

        // Update selection tabs based on available selections
        function updateSelectionTabs(runData) {
            const tabBar = document.getElementById('selection-tabs');
            tabBar.innerHTML = '';
            currentSelections = runData.selections;

            const nameClasses = Object.keys(currentSelections);

            if (nameClasses.length === 0) {
                tabBar.innerHTML = '<span class="no-selections">No selections available</span>';
                document.getElementById('selection-content').innerHTML =
                    '<p class="placeholder">No selection files found for this run</p>';
                document.getElementById('selection-meta').innerHTML = '';
                return;
            }

            nameClasses.forEach((nameClass, index) => {
                const tab = document.createElement('button');
                tab.className = 'tab' + (index === 0 ? ' active' : '');
                tab.textContent = formatNameClass(nameClass);
                tab.onclick = () => selectTab(nameClass, runData.path.split('/').pop());
                tabBar.appendChild(tab);
            });

            // Auto-select first tab
            if (nameClasses.length > 0) {
                selectTab(nameClasses[0], runData.path.split('/').pop());
            }
        }

        // Format name class for display
        function formatNameClass(nameClass) {
            return nameClass.split('_').map(w =>
                w.charAt(0).toUpperCase() + w.slice(1)
            ).join(' ');
        }

        // Handle tab selection
        async function selectTab(nameClass, runId) {
            activeTab = nameClass;

            // Update tab styling
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
                if (tab.textContent === formatNameClass(nameClass)) {
                    tab.classList.add('active');
                }
            });

            // Load selection data
            const contentEl = document.getElementById('selection-content');
            const metaEl = document.getElementById('selection-meta');
            contentEl.innerHTML = '<p class="loading">Loading...</p>';
            metaEl.innerHTML = '';

            try {
                const response = await fetch(`/api/runs/${runId}/selections/${nameClass}`);
                const data = await response.json();

                if (data.error) {
                    contentEl.innerHTML = `<p class="error">${data.error}</p>`;
                    return;
                }

                // Render selections table
                renderSelections(data);

                // Render metadata
                renderSelectionMeta(data.metadata);

            } catch (error) {
                contentEl.innerHTML = `<p class="error">Error: ${error.message}</p>`;
            }
        }

        // Render selections as a table
        function renderSelections(data) {
            const contentEl = document.getElementById('selection-content');
            const selections = data.selections || [];

            if (selections.length === 0) {
                contentEl.innerHTML = '<p class="placeholder">No names in this selection</p>';
                return;
            }

            let html = `
                <table class="selections-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Name</th>
                            <th>Score</th>
                            <th>Syllables</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            selections.forEach((sel, idx) => {
                const syllables = sel.syllables ? sel.syllables.join(' + ') : '-';
                html += `
                    <tr>
                        <td class="rank">${idx + 1}</td>
                        <td class="name">${sel.name}</td>
                        <td class="score">${sel.score}</td>
                        <td class="syllables">${syllables}</td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            contentEl.innerHTML = html;
        }

        // Render selection metadata
        function renderSelectionMeta(meta) {
            const metaEl = document.getElementById('selection-meta');

            if (!meta) {
                metaEl.innerHTML = '';
                return;
            }

            const admitted = meta.admitted || 0;
            const rejected = meta.rejected || 0;
            const total = meta.total_evaluated || (admitted + rejected);

            let html = `<span>${admitted} admitted / ${rejected} rejected (${total} evaluated)</span>`;

            // Show rejection reasons if any
            if (meta.rejection_reasons && Object.keys(meta.rejection_reasons).length > 0) {
                const reasons = Object.entries(meta.rejection_reasons)
                    .map(([reason, count]) => `${reason}: ${count}`)
                    .join(', ');
                html += `<span class="rejection-reasons">Rejections: ${reasons}</span>`;
            }

            metaEl.innerHTML = html;
        }

        // Load walker for the selected run
        async function loadWalker(runId) {
            const walkBtn = document.getElementById('walk-btn');
            const resultEl = document.getElementById('walk-result');

            walkBtn.disabled = true;
            resultEl.innerHTML = '<p class="loading">Loading syllables...</p>';

            try {
                const response = await fetch('/api/select-run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({run_id: runId})
                });

                const data = await response.json();

                if (data.error) {
                    resultEl.innerHTML = `<p class="error">${data.error}</p>`;
                    return;
                }

                walkBtn.disabled = false;
                resultEl.innerHTML = `<p class="ready">Ready (${data.syllable_count.toLocaleString()} syllables from ${data.source})</p>`;

            } catch (error) {
                resultEl.innerHTML = `<p class="error">Error: ${error.message}</p>`;
            }
        }

        // Generate a walk
        async function generateWalk() {
            const walkBtn = document.getElementById('walk-btn');
            const resultEl = document.getElementById('walk-result');
            const startInput = document.getElementById('start-syllable');
            const profileSelect = document.getElementById('walk-profile');

            walkBtn.disabled = true;
            resultEl.innerHTML = '<p class="loading">Generating walk...</p>';

            try {
                const response = await fetch('/api/walk', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        start: startInput.value || null,
                        profile: profileSelect.value,
                        steps: 5
                    })
                });

                const data = await response.json();

                if (data.error) {
                    resultEl.innerHTML = `<p class="error">${data.error}</p>`;
                    walkBtn.disabled = false;
                    return;
                }

                // Render walk
                const path = data.walk.map(s => s.syllable).join(' &rarr; ');
                resultEl.innerHTML = `<div class="walk-path">${path}</div>`;

                walkBtn.disabled = false;

            } catch (error) {
                resultEl.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                walkBtn.disabled = false;
            }
        }

        // Initialize on page load
        loadRuns();
    </script>
</body>
</html>
"""

# CSS stylesheet for the simplified web interface
CSS_CONTENT = """
/* System preference for dark/light mode */
:root {
    --bg: #f8f9fa;
    --bg-secondary: #ffffff;
    --bg-tertiary: #e9ecef;
    --text: #212529;
    --text-secondary: #6c757d;
    --accent: #4a6fa5;
    --accent-hover: #3a5a8a;
    --border: #dee2e6;
    --success: #28a745;
    --error: #dc3545;
}

@media (prefers-color-scheme: dark) {
    :root {
        --bg: #1a1d23;
        --bg-secondary: #22262e;
        --bg-tertiary: #2a2e38;
        --text: #e8eaed;
        --text-secondary: #8e929b;
        --accent: #6b8fbc;
        --accent-hover: #5a7fa8;
        --border: #3a3e47;
        --success: #3fb950;
        --error: #f85149;
    }
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 20px;
}

.container {
    max-width: 900px;
    margin: 0 auto;
}

header {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
}

header h1 {
    font-size: 1.8em;
    margin-bottom: 5px;
}

header p {
    color: var(--text-secondary);
}

section {
    background: var(--bg-secondary);
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    border: 1px solid var(--border);
}

section h2 {
    font-size: 1.2em;
    margin-bottom: 15px;
    color: var(--text);
}

/* Run Selector */
.run-selector {
    display: flex;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}

.run-selector label {
    font-weight: 600;
}

.run-selector select {
    flex: 1;
    min-width: 200px;
    padding: 8px 12px;
    background: var(--bg-tertiary);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 0.95em;
}

.run-info {
    color: var(--text-secondary);
    font-size: 0.9em;
}

/* Selection Tabs */
.tab-bar {
    display: flex;
    gap: 5px;
    margin-bottom: 15px;
    flex-wrap: wrap;
}

.tab {
    padding: 8px 16px;
    background: var(--bg-tertiary);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
    transition: background 0.2s;
}

.tab:hover {
    background: var(--border);
}

.tab.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
}

.no-selections {
    color: var(--text-secondary);
    font-style: italic;
}

/* Selection Content */
.selection-content {
    max-height: 400px;
    overflow-y: auto;
}

.selections-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95em;
}

.selections-table th,
.selections-table td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
}

.selections-table th {
    background: var(--bg-tertiary);
    font-weight: 600;
    position: sticky;
    top: 0;
}

.selections-table .rank {
    width: 50px;
    color: var(--text-secondary);
}

.selections-table .name {
    font-weight: 500;
}

.selections-table .score {
    width: 70px;
    text-align: center;
}

.selections-table .syllables {
    color: var(--text-secondary);
    font-family: monospace;
}

.selection-meta {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid var(--border);
    font-size: 0.85em;
    color: var(--text-secondary);
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
}

.rejection-reasons {
    color: var(--error);
}

/* Walk Section */
.walk-controls {
    display: flex;
    gap: 15px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 15px;
}

.control-row {
    display: flex;
    align-items: center;
    gap: 8px;
}

.control-row label {
    font-weight: 500;
}

.control-row input,
.control-row select {
    padding: 8px 12px;
    background: var(--bg-tertiary);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 0.95em;
}

.control-row input {
    width: 120px;
}

.walk-controls button {
    padding: 8px 20px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s;
}

.walk-controls button:hover:not(:disabled) {
    background: var(--accent-hover);
}

.walk-controls button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.walk-result {
    background: var(--bg-tertiary);
    padding: 15px;
    border-radius: 4px;
    min-height: 50px;
}

.walk-path {
    font-size: 1.2em;
    font-weight: 500;
    line-height: 1.8;
}

/* Utility classes */
.placeholder {
    color: var(--text-secondary);
    font-style: italic;
}

.loading {
    color: var(--accent);
}

.ready {
    color: var(--success);
}

.error {
    color: var(--error);
}

/* Responsive */
@media (max-width: 600px) {
    .run-selector {
        flex-direction: column;
        align-items: stretch;
    }

    .walk-controls {
        flex-direction: column;
        align-items: stretch;
    }

    .control-row {
        justify-content: space-between;
    }

    .control-row input,
    .control-row select {
        flex: 1;
    }
}
"""
