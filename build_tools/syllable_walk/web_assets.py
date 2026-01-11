"""Static web assets for the syllable walker web interface.

This module contains HTML and CSS templates embedded as Python strings. Assets are
embedded rather than served as separate files to maintain simplicity and avoid
requiring additional file distribution when the package is installed.

The embedded assets provide:
- HTML_TEMPLATE: Complete single-page application interface
- CSS_CONTENT: Full stylesheet for the web interface
"""

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Syllable Walker - Interactive Explorer</title>
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <div>
                    <h1>Syllable Walker</h1>
                    <p>Explore phonetic feature space through cost-based random walks</p>
                </div>
                <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
                    <span class="theme-icon">☀️</span>
                </button>
            </div>
        </div>

        <div class="mode-selector">
            <button class="mode-btn active" data-mode="single" onclick="switchMode('single')">
                Single View
            </button>
            <button class="mode-btn" data-mode="split" onclick="switchMode('split')">
                Split Compare
            </button>
        </div>

        <div class="dataset-selector" id="single-dataset-selector">
            <div class="dataset-label">Dataset:</div>
            <select id="dataset-select" onchange="loadDataset()">
                <option value="">Loading datasets...</option>
            </select>
            <div id="dataset-loading" class="dataset-loading" style="display: none;">
                <div class="mini-spinner"></div>
                <span>Switching dataset...</span>
            </div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="total-syllables">-</div>
                <div class="stat-label">Total Syllables</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="total-walks">0</div>
                <div class="stat-label">Walks Generated</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="current-profile">-</div>
                <div class="stat-label">Current Profile</div>
            </div>
        </div>

        <div class="content" id="content-container">
            <!-- Single Panel View (default) -->
            <div id="single-panel" class="panel-container">
                <div class="controls">
                    <h2 style="margin-bottom: 20px; color: #212529;">Walk Parameters</h2>

                    <div class="control-group">
                        <label for="start-syllable">Starting Syllable</label>
                        <input type="text" id="start-syllable" placeholder="e.g., ka, bak, or leave empty for random">
                        <div class="help-text">Leave empty for a random starting point</div>
                    </div>

                    <div class="control-group">
                        <label for="profile">Walk Profile</label>
                        <select id="profile">
                            <option value="clerical">Clerical (Conservative)</option>
                            <option value="dialect" selected>Dialect (Balanced)</option>
                            <option value="goblin">Goblin (Chaotic)</option>
                            <option value="ritual">Ritual (Maximum Exploration)</option>
                            <option value="custom">Custom Parameters</option>
                        </select>
                        <div class="profile-info" id="profile-description">
                            Moderate exploration, neutral frequency bias
                        </div>
                    </div>

                    <div id="custom-params" style="display: none;">
                        <div class="control-group">
                            <label for="steps">Steps</label>
                            <input type="number" id="steps" value="5" min="1" max="20">
                        </div>

                        <div class="control-group">
                            <label for="max-flips">Max Feature Flips</label>
                            <input type="number" id="max-flips" value="2" min="1" max="3">
                            <div class="help-text">Maximum phonetic distance per step</div>
                        </div>

                        <div class="control-group">
                            <label for="temperature">Temperature</label>
                            <input type="number" id="temperature" value="0.7" min="0.1" max="5" step="0.1">
                            <div class="help-text">Higher = more random exploration</div>
                        </div>

                        <div class="control-group">
                            <label for="frequency-weight">Frequency Weight</label>
                            <input type="number" id="frequency-weight" value="0.0" min="-2" max="2" step="0.1">
                            <div class="help-text">Positive favors common, negative favors rare</div>
                        </div>
                    </div>

                    <div class="control-group">
                        <label for="seed">Random Seed (optional)</label>
                        <input type="number" id="seed" placeholder="Leave empty for random">
                        <div class="help-text">For reproducible walks</div>
                    </div>

                    <button class="btn" id="generate-btn" onclick="generateWalk()">
                        Generate Walk
                    </button>
                </div>

                <div class="results">
                    <div id="walk-output">
                        <div class="loading">
                            <p>Click "Generate Walk" to begin exploring</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Split Panel View -->
            <div id="split-panels" class="split-container" style="display: none;">
                <!-- Panel A -->
                <div class="panel panel-a">
                    <div class="panel-header">
                        <h3>Dataset A</h3>
                        <div class="panel-dataset-selector">
                            <select id="dataset-select-a" onchange="loadDatasetA()">
                                <option value="">Loading datasets...</option>
                            </select>
                        </div>
                    </div>

                    <div class="panel-stats">
                        <div class="panel-stat">
                            <div class="panel-stat-value" id="syllables-a">-</div>
                            <div class="panel-stat-label">Syllables</div>
                        </div>
                        <div class="panel-stat">
                            <div class="panel-stat-value" id="walks-a">0</div>
                            <div class="panel-stat-label">Walks</div>
                        </div>
                    </div>

                    <div class="panel-controls">
                        <div class="control-group">
                            <label for="start-syllable-a">Starting Syllable</label>
                            <input type="text" id="start-syllable-a" placeholder="e.g., ka">
                        </div>

                        <div class="control-group">
                            <label for="profile-a">Walk Profile</label>
                            <select id="profile-a" onchange="updateProfileA()">
                                <option value="clerical">Clerical</option>
                                <option value="dialect" selected>Dialect</option>
                                <option value="goblin">Goblin</option>
                                <option value="ritual">Ritual</option>
                            </select>
                        </div>

                        <div class="control-group">
                            <label for="seed-a">Seed</label>
                            <input type="number" id="seed-a" placeholder="Optional">
                        </div>

                        <button id="generate-btn-a" class="btn btn-panel" onclick="generateWalkA()">
                            Generate Walk A
                        </button>
                    </div>

                    <div class="panel-results">
                        <div id="walk-output-a">
                            <div class="loading">
                                <p>Select dataset and generate walk</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Panel B -->
                <div class="panel panel-b">
                    <div class="panel-header">
                        <h3>Dataset B</h3>
                        <div class="panel-dataset-selector">
                            <select id="dataset-select-b" onchange="loadDatasetB()">
                                <option value="">Loading datasets...</option>
                            </select>
                        </div>
                    </div>

                    <div class="panel-stats">
                        <div class="panel-stat">
                            <div class="panel-stat-value" id="syllables-b">-</div>
                            <div class="panel-stat-label">Syllables</div>
                        </div>
                        <div class="panel-stat">
                            <div class="panel-stat-value" id="walks-b">0</div>
                            <div class="panel-stat-label">Walks</div>
                        </div>
                    </div>

                    <div class="panel-controls">
                        <div class="control-group">
                            <label for="start-syllable-b">Starting Syllable</label>
                            <input type="text" id="start-syllable-b" placeholder="e.g., ka">
                        </div>

                        <div class="control-group">
                            <label for="profile-b">Walk Profile</label>
                            <select id="profile-b" onchange="updateProfileB()">
                                <option value="clerical">Clerical</option>
                                <option value="dialect" selected>Dialect</option>
                                <option value="goblin">Goblin</option>
                                <option value="ritual">Ritual</option>
                            </select>
                        </div>

                        <div class="control-group">
                            <label for="seed-b">Seed</label>
                            <input type="number" id="seed-b" placeholder="Optional">
                        </div>

                        <button id="generate-btn-b" class="btn btn-panel" onclick="generateWalkB()">
                            Generate Walk B
                        </button>
                    </div>

                    <div class="panel-results">
                        <div id="walk-output-b">
                            <div class="loading">
                                <p>Select dataset and generate walk</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // State variables
        let displayMode = 'single';  // 'single' or 'split'
        let walkCount = 0;
        let availableDatasets = [];
        let currentDatasetPath = null;

        // Split mode state
        let datasetPathA = null;
        let datasetPathB = null;
        let walkCountA = 0;
        let walkCountB = 0;
        let serverLoadedDataset = null;  // Track which dataset is currently loaded on server

        // Theme handling
        function initTheme() {
            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = savedTheme || (prefersDark ? 'dark' : 'light');

            document.documentElement.setAttribute('data-theme', theme);
            updateThemeIcon(theme);
        }

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeIcon(next);
        }

        function updateThemeIcon(theme) {
            const icon = document.querySelector('.theme-icon');
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        // Initialize theme on load
        initTheme();

        const profileDescriptions = {
            clerical: "Conservative, favors common syllables, minimal phonetic change",
            dialect: "Moderate exploration, neutral frequency bias",
            goblin: "Chaotic, favors rare syllables, high phonetic variation",
            ritual: "Maximum exploration, strongly favors rare syllables",
            custom: "Use custom parameters below"
        };

        const profileParams = {
            clerical: { steps: 5, max_flips: 1, temperature: 0.3, frequency_weight: 1.0 },
            dialect: { steps: 5, max_flips: 2, temperature: 0.7, frequency_weight: 0.0 },
            goblin: { steps: 5, max_flips: 2, temperature: 1.5, frequency_weight: -0.5 },
            ritual: { steps: 5, max_flips: 3, temperature: 2.5, frequency_weight: -1.0 }
        };

        // Load available datasets
        async function loadAvailableDatasets() {
            try {
                const response = await fetch('/api/datasets');
                const data = await response.json();

                availableDatasets = data.datasets;
                currentDatasetPath = data.current;

                // Initialize server-loaded dataset tracker
                serverLoadedDataset = data.current;

                const select = document.getElementById('dataset-select');
                select.innerHTML = '';

                if (availableDatasets.length === 0) {
                    select.innerHTML = '<option value="">No datasets found</option>';
                    return;
                }

                availableDatasets.forEach(dataset => {
                    const option = document.createElement('option');
                    option.value = dataset.path;
                    option.textContent = dataset.name;
                    if (dataset.path === currentDatasetPath) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });

                // Load stats for current dataset
                loadStats();
            } catch (error) {
                console.error('Error loading datasets:', error);
                document.getElementById('dataset-select').innerHTML =
                    '<option value="">Error loading datasets</option>';
            }
        }

        // Load statistics
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('total-syllables').textContent =
                    data.total_syllables.toLocaleString();
                // Track what's loaded on server
                serverLoadedDataset = data.current_dataset;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        // Load a different dataset
        async function loadDataset() {
            const select = document.getElementById('dataset-select');
            const newPath = select.value;

            if (!newPath || newPath === currentDatasetPath) {
                return;
            }

            const loadingIndicator = document.getElementById('dataset-loading');
            const generateBtn = document.getElementById('generate-btn');

            try {
                // Show loading indicator
                loadingIndicator.style.display = 'flex';
                generateBtn.disabled = true;

                const response = await fetch('/api/load-dataset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: newPath })
                });

                const data = await response.json();

                if (data.error) {
                    alert('Error loading dataset: ' + data.error);
                    // Revert selection
                    select.value = currentDatasetPath;
                } else {
                    // Update current path
                    currentDatasetPath = newPath;
                    serverLoadedDataset = newPath;  // Track server state

                    // Update stats
                    document.getElementById('total-syllables').textContent =
                        data.total_syllables.toLocaleString();

                    // Reset walk count
                    walkCount = 0;
                    document.getElementById('total-walks').textContent = '0';

                    // Clear output
                    document.getElementById('walk-output').innerHTML =
                        '<div class="loading"><p>Dataset loaded! Click "Generate Walk" to begin exploring</p></div>';
                }
            } catch (error) {
                console.error('Error switching dataset:', error);
                alert('Error switching dataset: ' + error.message);
                select.value = currentDatasetPath;
            } finally {
                loadingIndicator.style.display = 'none';
                generateBtn.disabled = false;
            }
        }

        // Initialize on page load
        loadAvailableDatasets();

        // Profile change handler
        document.getElementById('profile').addEventListener('change', function() {
            const profile = this.value;
            document.getElementById('profile-description').textContent = profileDescriptions[profile];
            document.getElementById('current-profile').textContent =
                profile.charAt(0).toUpperCase() + profile.slice(1);

            if (profile === 'custom') {
                document.getElementById('custom-params').style.display = 'block';
            } else {
                document.getElementById('custom-params').style.display = 'none';
                const params = profileParams[profile];
                document.getElementById('steps').value = params.steps;
                document.getElementById('max-flips').value = params.max_flips;
                document.getElementById('temperature').value = params.temperature;
                document.getElementById('frequency-weight').value = params.frequency_weight;
            }
        });

        // Initialize profile
        document.getElementById('profile').dispatchEvent(new Event('change'));

        async function generateWalk() {
            const btn = document.getElementById('generate-btn');
            const output = document.getElementById('walk-output');

            btn.disabled = true;
            output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating walk...</p></div>';

            const params = {
                start: document.getElementById('start-syllable').value || null,
                profile: document.getElementById('profile').value,
                steps: parseInt(document.getElementById('steps').value),
                max_flips: parseInt(document.getElementById('max-flips').value),
                temperature: parseFloat(document.getElementById('temperature').value),
                frequency_weight: parseFloat(document.getElementById('frequency-weight').value),
                seed: document.getElementById('seed').value ? parseInt(document.getElementById('seed').value) : null
            };

            try {
                const response = await fetch('/api/walk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });

                const data = await response.json();

                if (data.error) {
                    output.innerHTML = `<div class="error">${data.error}</div>`;
                } else {
                    displayWalk(data);
                    walkCount++;
                    document.getElementById('total-walks').textContent = walkCount;
                }
            } catch (error) {
                output.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        }

        function displayWalk(data) {
            const path = data.walk.map(s => s.syllable).join(' → ');

            let html = `
                <div class="walk-display">
                    <h3 style="margin-bottom: 15px; color: #495057;">Walk Path</h3>
                    <div class="walk-path">${path}</div>
                </div>
                <div class="walk-details">
                    <h3 style="margin-bottom: 15px; color: #495057;">Syllable Details</h3>
            `;

            data.walk.forEach((syllable, idx) => {
                html += `
                    <div class="syllable-card">
                        <div>
                            <span style="color: #6c757d; margin-right: 10px;">${idx + 1}.</span>
                            <span class="syllable-text">${syllable.syllable}</span>
                        </div>
                        <div class="syllable-freq">freq: ${syllable.frequency}</div>
                    </div>
                `;
            });

            html += '</div>';
            document.getElementById('walk-output').innerHTML = html;
        }

        // Mode switching
        function switchMode(mode) {
            displayMode = mode;

            // Update button states
            document.querySelectorAll('.mode-btn').forEach(btn => {
                if (btn.dataset.mode === mode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // Show/hide panels and top stats bar
            const statsBar = document.querySelector('.stats');
            if (mode === 'single') {
                document.getElementById('single-panel').style.display = 'grid';
                document.getElementById('split-panels').style.display = 'none';
                document.getElementById('single-dataset-selector').style.display = 'flex';
                statsBar.style.display = 'flex';
            } else {
                document.getElementById('single-panel').style.display = 'none';
                document.getElementById('split-panels').style.display = 'grid';
                document.getElementById('single-dataset-selector').style.display = 'none';
                statsBar.style.display = 'none';  // Hide top stats in split mode

                // Populate split panel dataset selectors if not done yet
                if (datasetPathA === null && availableDatasets.length > 0) {
                    populateSplitDatasetSelectors();
                }
            }
        }

        // Populate dataset selectors for split panels
        function populateSplitDatasetSelectors() {
            const selectA = document.getElementById('dataset-select-a');
            const selectB = document.getElementById('dataset-select-b');

            selectA.innerHTML = '';
            selectB.innerHTML = '';

            availableDatasets.forEach(dataset => {
                const option_a = document.createElement('option');
                option_a.value = dataset.path;
                option_a.textContent = dataset.name;
                selectA.appendChild(option_a);

                const option_b = document.createElement('option');
                option_b.value = dataset.path;
                option_b.textContent = dataset.name;
                selectB.appendChild(option_b);
            });

            // Select first dataset by default
            if (availableDatasets.length > 0) {
                datasetPathA = availableDatasets[0].path;
                selectA.value = datasetPathA;
                // Update stats from cached data (no API call needed!)
                document.getElementById('syllables-a').textContent =
                    availableDatasets[0].syllable_count.toLocaleString();
            }

            // Select second dataset if available, otherwise same as first
            if (availableDatasets.length > 1) {
                datasetPathB = availableDatasets[1].path;
                selectB.value = datasetPathB;
                // Update stats from cached data
                document.getElementById('syllables-b').textContent =
                    availableDatasets[1].syllable_count.toLocaleString();
            } else if (availableDatasets.length > 0) {
                datasetPathB = availableDatasets[0].path;
                selectB.value = datasetPathB;
                // Update stats from cached data
                document.getElementById('syllables-b').textContent =
                    availableDatasets[0].syllable_count.toLocaleString();
            }
        }

        // Update stats for panel A from cached dataset info
        function updateDatasetStatsA() {
            const dataset = availableDatasets.find(ds => ds.path === datasetPathA);
            if (dataset) {
                document.getElementById('syllables-a').textContent =
                    dataset.syllable_count.toLocaleString();
            }
        }

        // Update stats for panel B from cached dataset info
        function updateDatasetStatsB() {
            const dataset = availableDatasets.find(ds => ds.path === datasetPathB);
            if (dataset) {
                document.getElementById('syllables-b').textContent =
                    dataset.syllable_count.toLocaleString();
            }
        }

        // Load dataset A (when user changes selection)
        function loadDatasetA() {
            const select = document.getElementById('dataset-select-a');
            datasetPathA = select.value;
            updateDatasetStatsA();

            // Reset walk count and output
            walkCountA = 0;
            document.getElementById('walks-a').textContent = '0';
            document.getElementById('walk-output-a').innerHTML =
                '<div class="loading"><p>Generate walk to begin exploring</p></div>';
        }

        // Load dataset B (when user changes selection)
        function loadDatasetB() {
            const select = document.getElementById('dataset-select-b');
            datasetPathB = select.value;
            updateDatasetStatsB();

            // Reset walk count and output
            walkCountB = 0;
            document.getElementById('walks-b').textContent = '0';
            document.getElementById('walk-output-b').innerHTML =
                '<div class="loading"><p>Generate walk to begin exploring</p></div>';
        }

        // Update profile A
        function updateProfileA() {
            const profile = document.getElementById('profile-a').value;
            // Profile parameters automatically applied during walk generation
        }

        // Update profile B
        function updateProfileB() {
            const profile = document.getElementById('profile-b').value;
            // Profile parameters automatically applied during walk generation
        }

        // Generate walk for panel A
        async function generateWalkA() {
            const btn = document.getElementById('generate-btn-a');
            const output = document.getElementById('walk-output-a');

            btn.disabled = true;

            try {
                // Only load dataset if it's different from what's currently loaded
                if (serverLoadedDataset !== datasetPathA) {
                    output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading dataset...</p></div>';

                    const loadResponse = await fetch('/api/load-dataset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: datasetPathA })
                    });

                    const loadData = await loadResponse.json();

                    if (loadData.error) {
                        output.innerHTML = `<div class="error">Error loading dataset: ${loadData.error}</div>`;
                        btn.disabled = false;
                        return;
                    }

                    // Update server-loaded dataset tracker to exact path we sent
                    serverLoadedDataset = datasetPathA;
                }

                // Dataset is loaded, now generate walk
                output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating walk...</p></div>';

                const profile = document.getElementById('profile-a').value;
                const params = {
                    start: document.getElementById('start-syllable-a').value || null,
                    profile: profile,
                    ...profileParams[profile],
                    seed: document.getElementById('seed-a').value ?
                        parseInt(document.getElementById('seed-a').value) : null
                };

                const response = await fetch('/api/walk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });

                const data = await response.json();

                if (data.error) {
                    output.innerHTML = `<div class="error">${data.error}</div>`;
                } else {
                    displayWalkPanel(data, 'a');
                    walkCountA++;
                    document.getElementById('walks-a').textContent = walkCountA;
                }
            } catch (error) {
                output.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        }

        // Generate walk for panel B
        async function generateWalkB() {
            const btn = document.getElementById('generate-btn-b');
            const output = document.getElementById('walk-output-b');

            btn.disabled = true;

            try {
                // Only load dataset if it's different from what's currently loaded
                if (serverLoadedDataset !== datasetPathB) {
                    output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading dataset...</p></div>';

                    const loadResponse = await fetch('/api/load-dataset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: datasetPathB })
                    });

                    const loadData = await loadResponse.json();

                    if (loadData.error) {
                        output.innerHTML = `<div class="error">Error loading dataset: ${loadData.error}</div>`;
                        btn.disabled = false;
                        return;
                    }

                    // Update server-loaded dataset tracker to exact path we sent
                    serverLoadedDataset = datasetPathB;
                }

                // Dataset is loaded, now generate walk
                output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating walk...</p></div>';

                const profile = document.getElementById('profile-b').value;
                const params = {
                    start: document.getElementById('start-syllable-b').value || null,
                    profile: profile,
                    ...profileParams[profile],
                    seed: document.getElementById('seed-b').value ?
                        parseInt(document.getElementById('seed-b').value) : null
                };

                const response = await fetch('/api/walk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(params)
                });

                const data = await response.json();

                if (data.error) {
                    output.innerHTML = `<div class="error">${data.error}</div>`;
                } else {
                    displayWalkPanel(data, 'b');
                    walkCountB++;
                    document.getElementById('walks-b').textContent = walkCountB;
                }
            } catch (error) {
                output.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        }

        // Display walk for split panel
        function displayWalkPanel(data, panel) {
            const path = data.walk.map(s => s.syllable).join(' → ');

            let html = `
                <div class="walk-display">
                    <div class="walk-path">${path}</div>
                </div>
                <div class="walk-details">
            `;

            data.walk.forEach((syllable, idx) => {
                html += `
                    <div class="syllable-card">
                        <div>
                            <span style="color: #6c757d; margin-right: 10px;">${idx + 1}.</span>
                            <span class="syllable-text">${syllable.syllable}</span>
                        </div>
                        <div class="syllable-freq">freq: ${syllable.frequency}</div>
                    </div>
                `;
            });

            html += '</div>';
            document.getElementById(`walk-output-${panel}`).innerHTML = html;
        }
    </script>
</body>
</html>
"""

# CSS stylesheet for the web interface
CSS_CONTENT = """/* ========================================
   CSS VARIABLES FOR THEMING
   ======================================== */
:root[data-theme="light"] {
    --bg-primary: #f8f9fa;
    --bg-secondary: #ffffff;
    --bg-tertiary: #f1f3f5;
    --bg-accent: #e9ecef;

    --text-primary: #212529;
    --text-secondary: #495057;
    --text-tertiary: #6c757d;

    --border-primary: #dee2e6;
    --border-secondary: #ced4da;

    --accent-primary: #4a6fa5;
    --accent-secondary: #6c8ebb;
    --accent-hover: #3a5a8a;

    --stat-value: #2c5282;
    --stat-label: #6c757d;

    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 20px rgba(0, 0, 0, 0.1);
}

:root[data-theme="dark"] {
    --bg-primary: #1a1d23;
    --bg-secondary: #22262e;
    --bg-tertiary: #2a2e38;
    --bg-accent: #32363f;

    --text-primary: #e8eaed;
    --text-secondary: #b8bcc4;
    --text-tertiary: #8e929b;

    --border-primary: #3a3e47;
    --border-secondary: #4a4e57;

    --accent-primary: #6b8fbc;
    --accent-secondary: #8aa8cc;
    --accent-hover: #5a7fa8;

    --stat-value: #8aa8cc;
    --stat-label: #8e929b;

    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 10px 20px rgba(0, 0, 0, 0.4);
}

/* ========================================
   RESET
   ======================================== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

/* ========================================
   BASE
   ======================================== */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    padding: 20px;
    transition: background-color 0.2s, color 0.2s;
}

/* ========================================
   CONTAINER
   ======================================== */
.container {
    max-width: 1200px;
    margin: 0 auto;
    background: var(--bg-secondary);
    border-radius: 8px;
    box-shadow: var(--shadow-lg);
    overflow: hidden;
    border: 1px solid var(--border-primary);
}

/* ========================================
   HEADER
   ======================================== */
.header {
    background: var(--bg-secondary);
    color: var(--text-primary);
    padding: 30px;
    border-bottom: 1px solid var(--border-primary);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.header h1 {
    font-size: 2em;
    margin-bottom: 8px;
    font-weight: 600;
    color: var(--text-primary);
}

.header p {
    font-size: 1em;
    color: var(--text-secondary);
}

.theme-toggle {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    padding: 10px 15px;
    font-size: 1.2em;
    cursor: pointer;
    transition: background-color 0.2s, border-color 0.2s;
    flex-shrink: 0;
}

.theme-toggle:hover {
    background: var(--bg-accent);
    border-color: var(--border-secondary);
}

.theme-icon {
    display: inline-block;
}

/* ========================================
   MODE SELECTOR
   ======================================== */
.mode-selector {
    background: var(--bg-secondary);
    padding: 15px 30px;
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    gap: 10px;
    justify-content: center;
}

.mode-btn {
    padding: 10px 25px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-secondary);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 0.95em;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.mode-btn:hover {
    border-color: var(--accent-primary);
    background: var(--bg-accent);
}

.mode-btn.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #ffffff;
}

/* ========================================
   DATASET SELECTOR
   ======================================== */
.dataset-selector {
    background: var(--bg-secondary);
    padding: 20px 30px;
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    align-items: center;
    gap: 15px;
}

.dataset-label {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.95em;
    min-width: 70px;
}

.dataset-selector select {
    flex: 1;
    padding: 10px 15px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-secondary);
    border-radius: 6px;
    font-size: 0.95em;
    color: var(--text-primary);
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}

.dataset-selector select:hover {
    border-color: var(--accent-secondary);
}

.dataset-selector select:focus {
    outline: none;
    border-color: var(--accent-primary);
    background: var(--bg-accent);
}

.dataset-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--accent-primary);
    font-size: 0.9em;
}

.mini-spinner {
    border: 2px solid var(--border-primary);
    border-top: 2px solid var(--accent-primary);
    border-radius: 50%;
    width: 16px;
    height: 16px;
    animation: spin 0.8s linear infinite;
}

/* ========================================
   STATS BAR
   ======================================== */
.stats {
    display: flex;
    justify-content: space-around;
    background: var(--bg-tertiary);
    padding: 20px;
    border-bottom: 1px solid var(--border-primary);
}

.stat {
    text-align: center;
}

.stat-value {
    font-size: 2em;
    font-weight: 600;
    color: var(--stat-value);
}

.stat-label {
    color: var(--stat-label);
    font-size: 0.85em;
    margin-top: 5px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* ========================================
   MAIN CONTENT GRID
   ======================================== */
.content {
    padding: 30px;
    background: var(--bg-secondary);
}

.panel-container {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 30px;
}

/* ========================================
   SPLIT-PANE LAYOUT
   ======================================== */
.split-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.panel {
    background: var(--bg-tertiary);
    border-radius: 8px;
    border: 1px solid var(--border-secondary);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.panel-a {
    border-left: 3px solid var(--accent-primary);
}

.panel-b {
    border-left: 3px solid #6c8ebb;
}

.panel-header {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 15px;
    border-bottom: 1px solid var(--border-primary);
}

.panel-header h3 {
    color: var(--text-primary);
    font-size: 1.2em;
    margin: 0;
    font-weight: 600;
}

.panel-dataset-selector select {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-secondary);
    border-radius: 6px;
    font-size: 0.9em;
    color: var(--text-primary);
    cursor: pointer;
    transition: border-color 0.2s;
}

.panel-dataset-selector select:hover {
    border-color: var(--accent-secondary);
}

.panel-dataset-selector select:focus {
    outline: none;
    border-color: var(--accent-primary);
}

.panel-stats {
    display: flex;
    justify-content: space-around;
    background: var(--bg-secondary);
    padding: 15px;
    border-radius: 6px;
    gap: 10px;
    border: 1px solid var(--border-primary);
}

.panel-stat {
    text-align: center;
}

.panel-stat-value {
    font-size: 1.5em;
    font-weight: 600;
    color: var(--stat-value);
}

.panel-stat-label {
    color: var(--stat-label);
    font-size: 0.75em;
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.panel-controls {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.panel-results {
    flex: 1;
    min-height: 200px;
}

.panel-results .walk-display {
    background: var(--bg-secondary);
    padding: 20px;
    border-radius: 6px;
    margin-bottom: 15px;
    border: 1px solid var(--border-primary);
}

.panel-results .walk-path {
    font-size: 1.1em;
    font-weight: 500;
    color: var(--text-primary);
    line-height: 1.6;
    word-wrap: break-word;
}

.panel-results .syllable-card {
    background: var(--bg-secondary);
    padding: 12px;
    margin: 8px 0;
    border-radius: 6px;
    border-left: 3px solid var(--accent-primary);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid var(--border-primary);
}

.btn-panel {
    padding: 12px;
    font-size: 0.95em;
}

/* ========================================
   CONTROLS PANEL
   ======================================== */
.controls {
    background: var(--bg-tertiary);
    padding: 25px;
    border-radius: 8px;
    border: 1px solid var(--border-primary);
    height: fit-content;
}

.control-group {
    margin-bottom: 20px;
}

.control-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text-primary);
    font-size: 0.9em;
}

.control-group input,
.control-group select {
    width: 100%;
    padding: 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-secondary);
    border-radius: 6px;
    font-size: 1em;
    color: var(--text-primary);
    transition: border-color 0.2s, background 0.2s;
}

.control-group input::placeholder {
    color: var(--text-tertiary);
}

.control-group input:focus,
.control-group select:focus {
    outline: none;
    border-color: var(--accent-primary);
    background: var(--bg-accent);
}

.control-group .help-text {
    font-size: 0.8em;
    color: var(--text-tertiary);
    margin-top: 6px;
    line-height: 1.4;
}

.profile-info {
    background: var(--bg-accent);
    padding: 15px;
    border-radius: 6px;
    margin-top: 10px;
    font-size: 0.85em;
    color: var(--text-secondary);
    border-left: 3px solid var(--accent-primary);
}

/* ========================================
   PRIMARY BUTTON
   ======================================== */
.btn {
    width: 100%;
    padding: 15px;
    background: var(--accent-primary);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-size: 1.05em;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s, box-shadow 0.2s;
}

.btn:hover {
    background: var(--accent-hover);
    box-shadow: var(--shadow-md);
}

.btn:active {
    box-shadow: var(--shadow-sm);
}

.btn:disabled {
    background: var(--bg-accent);
    color: var(--text-tertiary);
    cursor: not-allowed;
    box-shadow: none;
}

/* ========================================
   RESULTS
   ======================================== */
.results {
    background: transparent;
}

/* ========================================
   WALK DISPLAY
   ======================================== */
.walk-display {
    background: var(--bg-tertiary);
    padding: 25px;
    border-radius: 8px;
    margin-bottom: 20px;
    border: 1px solid var(--border-primary);
}

.walk-path {
    font-size: 1.3em;
    font-weight: 500;
    color: var(--text-primary);
    line-height: 1.8;
    word-wrap: break-word;
}

/* ========================================
   SYLLABLE DETAILS
   ======================================== */
.walk-details {
    margin-top: 20px;
}

.syllable-card {
    background: var(--bg-tertiary);
    padding: 15px;
    margin: 10px 0;
    border-radius: 6px;
    border-left: 3px solid var(--accent-primary);
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background-color 0.2s;
    border: 1px solid var(--border-primary);
}

.syllable-card:hover {
    background: var(--bg-accent);
}

.syllable-text {
    font-size: 1.15em;
    font-weight: 500;
    color: var(--text-primary);
}

.syllable-freq {
    background: var(--accent-primary);
    color: #ffffff;
    padding: 5px 14px;
    border-radius: 4px;
    font-size: 0.85em;
    font-weight: 500;
}

/* ========================================
   LOADING & SPINNER
   ======================================== */
.loading {
    text-align: center;
    padding: 40px;
    color: var(--text-tertiary);
}

.spinner {
    border: 4px solid var(--border-primary);
    border-top: 4px solid var(--accent-primary);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 20px auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* ========================================
   ERROR STATE
   ======================================== */
.error {
    background: #f8d7da;
    color: #721c24;
    padding: 15px;
    border-radius: 6px;
    margin: 20px 0;
    border-left: 3px solid #d9534f;
}

:root[data-theme="dark"] .error {
    background: #2a1b1d;
    color: #f2b8bd;
}

/* ========================================
   RESPONSIVE
   ======================================== */
@media (max-width: 1200px) {
    .split-container {
        grid-template-columns: 1fr;
    }

    .panel {
        max-width: 100%;
    }
}

@media (max-width: 768px) {
    .panel-container {
        grid-template-columns: 1fr;
    }

    .header-content {
        flex-direction: column;
        text-align: center;
    }

    .stats {
        flex-direction: column;
        gap: 15px;
    }

    .mode-selector {
        flex-direction: column;
        gap: 10px;
    }

    .mode-btn {
        width: 100%;
    }

    .split-container {
        grid-template-columns: 1fr;
    }

    .panel-stats {
        flex-direction: column;
        gap: 10px;
    }
}
"""
