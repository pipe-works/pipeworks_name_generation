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
            <h1>Syllable Walker</h1>
            <p>Explore phonetic feature space through cost-based random walks</p>
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

                        <button class="btn btn-panel" onclick="generateWalkA()">
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

                        <button class="btn btn-panel" onclick="generateWalkB()">
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

            // Show/hide panels
            if (mode === 'single') {
                document.getElementById('single-panel').style.display = 'grid';
                document.getElementById('split-panels').style.display = 'none';
                document.getElementById('single-dataset-selector').style.display = 'flex';
            } else {
                document.getElementById('single-panel').style.display = 'none';
                document.getElementById('split-panels').style.display = 'grid';
                document.getElementById('single-dataset-selector').style.display = 'none';

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
                loadDatasetStatsA();
            }

            // Select second dataset if available, otherwise same as first
            if (availableDatasets.length > 1) {
                datasetPathB = availableDatasets[1].path;
                selectB.value = datasetPathB;
                loadDatasetStatsB();
            } else if (availableDatasets.length > 0) {
                datasetPathB = availableDatasets[0].path;
                selectB.value = datasetPathB;
                loadDatasetStatsB();
            }
        }

        // Load dataset stats for panel A
        async function loadDatasetStatsA() {
            try {
                const response = await fetch('/api/load-dataset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: datasetPathA })
                });
                const data = await response.json();
                if (!data.error) {
                    document.getElementById('syllables-a').textContent = data.total_syllables.toLocaleString();
                }
            } catch (error) {
                console.error('Error loading dataset A stats:', error);
            }
        }

        // Load dataset stats for panel B
        async function loadDatasetStatsB() {
            try {
                const response = await fetch('/api/load-dataset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: datasetPathB })
                });
                const data = await response.json();
                if (!data.error) {
                    document.getElementById('syllables-b').textContent = data.total_syllables.toLocaleString();
                }
            } catch (error) {
                console.error('Error loading dataset B stats:', error);
            }
        }

        // Load dataset A
        async function loadDatasetA() {
            const select = document.getElementById('dataset-select-a');
            datasetPathA = select.value;
            await loadDatasetStatsA();

            // Reset walk count and output
            walkCountA = 0;
            document.getElementById('walks-a').textContent = '0';
            document.getElementById('walk-output-a').innerHTML =
                '<div class="loading"><p>Generate walk to begin exploring</p></div>';
        }

        // Load dataset B
        async function loadDatasetB() {
            const select = document.getElementById('dataset-select-b');
            datasetPathB = select.value;
            await loadDatasetStatsB();

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
            const btn = event.target;
            const output = document.getElementById('walk-output-a');

            btn.disabled = true;
            output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating walk...</p></div>';

            // Load dataset A first
            await fetch('/api/load-dataset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: datasetPathA })
            });

            const profile = document.getElementById('profile-a').value;
            const params = {
                start: document.getElementById('start-syllable-a').value || null,
                profile: profile,
                ...profileParams[profile],
                seed: document.getElementById('seed-a').value ?
                    parseInt(document.getElementById('seed-a').value) : null
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
            const btn = event.target;
            const output = document.getElementById('walk-output-b');

            btn.disabled = true;
            output.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating walk...</p></div>';

            // Load dataset B first
            await fetch('/api/load-dataset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: datasetPathB })
            });

            const profile = document.getElementById('profile-b').value;
            const params = {
                start: document.getElementById('start-syllable-b').value || null,
                profile: profile,
                ...profileParams[profile],
                seed: document.getElementById('seed-b').value ?
                    parseInt(document.getElementById('seed-b').value) : null
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
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #0f1218 0%, #151a23 100%);
    color: #d6d9e0;
    min-height: 100vh;
    padding: 20px;
}

/* ========================================
   CONTAINER
   ======================================== */
.container {
    max-width: 1200px;
    margin: 0 auto;
    background: #1b1f2a;
    border-radius: 12px;
    box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
    overflow: hidden;
    border: 1px solid #262b38;
}

/* ========================================
   HEADER
   ======================================== */
.header {
    background: linear-gradient(135deg, #232a3a 0%, #1b2130 100%);
    color: #eef0f4;
    padding: 30px;
    text-align: center;
    border-bottom: 1px solid #2b3142;
}

.header h1 {
    font-size: 2.4em;
    margin-bottom: 10px;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.header p {
    font-size: 1.05em;
    color: #b8bcc6;
}

/* ========================================
   MODE SELECTOR
   ======================================== */
.mode-selector {
    background: #1b1f2a;
    padding: 15px 30px;
    border-bottom: 1px solid #262b38;
    display: flex;
    gap: 10px;
    justify-content: center;
}

.mode-btn {
    padding: 10px 25px;
    background: #0f1218;
    border: 2px solid #2b3142;
    border-radius: 6px;
    color: #cfd3dc;
    font-size: 0.95em;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}

.mode-btn:hover {
    border-color: #6a74ff;
    background: #161a23;
}

.mode-btn.active {
    background: linear-gradient(135deg, #4f5bd5 0%, #6a74ff 100%);
    border-color: #6a74ff;
    color: #ffffff;
}

/* ========================================
   DATASET SELECTOR
   ======================================== */
.dataset-selector {
    background: #1b1f2a;
    padding: 20px 30px;
    border-bottom: 1px solid #262b38;
    display: flex;
    align-items: center;
    gap: 15px;
}

.dataset-label {
    font-weight: 600;
    color: #cfd3dc;
    font-size: 0.95em;
    min-width: 70px;
}

.dataset-selector select {
    flex: 1;
    padding: 10px 15px;
    background: #0f1218;
    border: 1px solid #2b3142;
    border-radius: 6px;
    font-size: 0.95em;
    color: #e6e8ee;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}

.dataset-selector select:hover {
    border-color: #9aa4ff;
}

.dataset-selector select:focus {
    outline: none;
    border-color: #9aa4ff;
    background: #121623;
}

.dataset-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #9aa4ff;
    font-size: 0.9em;
}

.mini-spinner {
    border: 2px solid #2b3142;
    border-top: 2px solid #9aa4ff;
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
    background: #161a23;
    padding: 20px;
    border-bottom: 1px solid #262b38;
}

.stat {
    text-align: center;
}

.stat-value {
    font-size: 2em;
    font-weight: 600;
    color: #9aa4ff;
}

.stat-label {
    color: #8c92a3;
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
    background: #161a23;
    border-radius: 8px;
    border: 2px solid #2b3142;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.panel-a {
    border-color: #6a74ff;
}

.panel-b {
    border-color: #ff6a88;
}

.panel-header {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 15px;
    border-bottom: 1px solid #262b38;
}

.panel-header h3 {
    color: #eef0f4;
    font-size: 1.2em;
    margin: 0;
}

.panel-dataset-selector select {
    width: 100%;
    padding: 8px 12px;
    background: #0f1218;
    border: 1px solid #2b3142;
    border-radius: 6px;
    font-size: 0.9em;
    color: #e6e8ee;
    cursor: pointer;
    transition: border-color 0.2s;
}

.panel-dataset-selector select:hover {
    border-color: #9aa4ff;
}

.panel-dataset-selector select:focus {
    outline: none;
    border-color: #9aa4ff;
}

.panel-stats {
    display: flex;
    justify-content: space-around;
    background: #1b1f2a;
    padding: 15px;
    border-radius: 6px;
    gap: 10px;
}

.panel-stat {
    text-align: center;
}

.panel-stat-value {
    font-size: 1.5em;
    font-weight: 600;
    color: #9aa4ff;
}

.panel-stat-label {
    color: #8c92a3;
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
    background: #1b1f2a;
    padding: 20px;
    border-radius: 6px;
    margin-bottom: 15px;
}

.panel-results .walk-path {
    font-size: 1.1em;
    font-weight: 600;
    color: #eef0f4;
    line-height: 1.6;
    word-wrap: break-word;
}

.panel-results .syllable-card {
    background: #1b1f2a;
    padding: 12px;
    margin: 8px 0;
    border-radius: 6px;
    border-left: 3px solid #6a74ff;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.btn-panel {
    padding: 12px;
    font-size: 0.95em;
}

/* ========================================
   CONTROLS PANEL
   ======================================== */
.controls {
    background: #161a23;
    padding: 25px;
    border-radius: 8px;
    border: 1px solid #262b38;
    height: fit-content;
}

.control-group {
    margin-bottom: 20px;
}

.control-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #cfd3dc;
    font-size: 0.9em;
}

.control-group input,
.control-group select {
    width: 100%;
    padding: 10px;
    background: #0f1218;
    border: 1px solid #2b3142;
    border-radius: 6px;
    font-size: 1em;
    color: #e6e8ee;
    transition: border-color 0.2s, background 0.2s;
}

.control-group input:focus,
.control-group select:focus {
    outline: none;
    border-color: #9aa4ff;
    background: #121623;
}

.control-group .help-text {
    font-size: 0.8em;
    color: #8c92a3;
    margin-top: 6px;
    line-height: 1.4;
}

.profile-info {
    background: #1f2534;
    padding: 15px;
    border-radius: 6px;
    margin-top: 10px;
    font-size: 0.85em;
    color: #cfd3dc;
    border-left: 3px solid #9aa4ff;
}

/* ========================================
   PRIMARY BUTTON
   ======================================== */
.btn {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #4f5bd5 0%, #6a74ff 100%);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-size: 1.05em;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
}

.btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(106, 116, 255, 0.35);
}

.btn:active {
    transform: translateY(0);
    box-shadow: none;
}

.btn:disabled {
    background: #3a3f52;
    color: #8c92a3;
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
    background: #161a23;
    padding: 25px;
    border-radius: 8px;
    margin-bottom: 20px;
    border: 1px solid #262b38;
}

.walk-path {
    font-size: 1.4em;
    font-weight: 600;
    color: #eef0f4;
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
    background: #1b1f2a;
    padding: 15px;
    margin: 10px 0;
    border-radius: 6px;
    border-left: 3px solid #6a74ff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: transform 0.15s, background 0.15s;
}

.syllable-card:hover {
    transform: translateX(4px);
    background: #20263a;
}

.syllable-text {
    font-size: 1.25em;
    font-weight: 600;
    color: #eef0f4;
}

.syllable-freq {
    background: #6a74ff;
    color: #ffffff;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}

/* ========================================
   LOADING & SPINNER
   ======================================== */
.loading {
    text-align: center;
    padding: 40px;
    color: #8c92a3;
}

.spinner {
    border: 4px solid #2b3142;
    border-top: 4px solid #6a74ff;
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
    background: #2a1b1d;
    color: #f2b8bd;
    padding: 15px;
    border-radius: 6px;
    margin: 20px 0;
    border-left: 3px solid #d9534f;
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
