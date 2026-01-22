=============
Name Selector
=============

.. currentmodule:: build_tools.name_selector

Overview
--------

.. automodule:: build_tools.name_selector
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.name_selector.cli
   :func: create_argument_parser
   :prog: python -m build_tools.name_selector

Output Format
-------------

Input/Output Contract
~~~~~~~~~~~~~~~~~~~~~

**Inputs:**

- ``<run_directory>/candidates/{prefix}_candidates_{N}syl.json`` - From name_combiner
- ``data/name_classes.yml`` - Policy configuration (or custom path)

**Output:**

- ``<run_directory>/selections/{prefix}_{name_class}_{N}syl.json``

**Example directory structure after selection:**

.. code-block:: text

    _working/output/20260110_115453_pyphen/
    ├── candidates/
    │   └── pyphen_candidates_2syl.json      ← Input
    ├── selections/
    │   ├── pyphen_first_name_2syl.json      ← Generated output
    │   ├── pyphen_last_name_2syl.json
    │   ├── pyphen_place_name_2syl.json
    │   ├── pyphen_location_name_2syl.json
    │   ├── pyphen_object_item_2syl.json
    │   ├── pyphen_organisation_2syl.json
    │   └── pyphen_title_epithet_2syl.json
    ├── data/
    ├── meta/
    └── ...

Available Name Classes
~~~~~~~~~~~~~~~~~~~~~~

The default policy file (``data/name_classes.yml``) defines these name classes:

.. list-table::
   :header-rows: 1
   :widths: 20 20 15 45

   * - Name Class
     - Optimization
     - Syllables
     - Key Constraints
   * - ``first_name``
     - Addressability
     - 2-3
     - Prefers vowel endings, avoids heavy clusters
   * - ``last_name``
     - Durability
     - 2-3
     - Prefers stop endings, avoids vowel endings
   * - ``place_name``
     - Stability
     - 2-4
     - Prefers clusters, vowel endings
   * - ``location_name``
     - Meaning Compression
     - 1-3
     - Prefers heavy clusters, all texture features
   * - ``object_item``
     - Distinction
     - 1-2
     - Prefers short vowels, stop endings
   * - ``organisation``
     - Cadence
     - 2-4
     - All texture features, long vowels, nasal/stop endings
   * - ``title_epithet``
     - Authority
     - 1-2
     - Heavy clusters, long vowels, avoids short vowels

Output Structure
~~~~~~~~~~~~~~~~

The selector produces JSON with this structure:

.. code-block:: json

   {
     "metadata": {
       "source_candidates": "pyphen_candidates_2syl.json",
       "name_class": "first_name",
       "policy_description": "Direct social address...",
       "policy_file": "data/name_classes.yml",
       "mode": "hard",
       "order": "alphabetical",
       "seed": 42,
       "total_evaluated": 10000,
       "admitted": 7420,
       "rejected": 2580,
       "rejection_reasons": {
         "ends_with_stop": 2580
       },
       "score_distribution": {
         "0": 5000,
         "1": 2000,
         "2": 420
       },
       "output_count": 100,
       "generated_at": "2026-01-10T12:00:00Z"
     },
     "selections": [
       {
         "name": "kali",
         "syllables": ["ka", "li"],
         "features": {...},
         "score": 2,
         "rank": 1,
         "evaluation": {
           "preferred_hits": ["ends_with_vowel", "contains_liquid"],
           "tolerated_hits": [],
           "discouraged_hits": [],
           "rejection_reason": null
         }
       }
     ]
   }

Policy Configuration
~~~~~~~~~~~~~~~~~~~~

Policies are defined in YAML with the following structure:

.. code-block:: yaml

   version: "1.0"
   name_classes:
     first_name:
       description: "Direct social address. Optimized for addressability."
       syllable_range: [2, 3]
       features:
         starts_with_vowel: preferred
         ends_with_vowel: preferred
         ends_with_stop: discouraged
         contains_liquid: preferred
         # ... all 12 features

**Policy values:**

- ``preferred``: +1 score when feature is present
- ``tolerated``: 0 score (neutral)
- ``discouraged``: Reject (hard mode) or -10 score (soft mode)

Integration Guide
-----------------

The name selector is the governance layer of the Selection Policy Layer. It evaluates
candidates produced by the name_combiner against name class policies.

**Typical workflow:**

.. code-block:: bash

   # Generate candidates first
   python -m build_tools.name_combiner \
     --run-dir _working/output/20260110_115453_pyphen/ \
     --syllables 2 \
     --count 10000

   # Select for different name classes
   python -m build_tools.name_selector \
     --run-dir _working/output/20260110_115453_pyphen/ \
     --candidates candidates/pyphen_candidates_2syl.json \
     --name-class first_name \
     --count 100

   python -m build_tools.name_selector \
     --run-dir _working/output/20260110_115453_pyphen/ \
     --candidates candidates/pyphen_candidates_2syl.json \
     --name-class last_name \
     --count 100

   # Select for other name classes as needed
   python -m build_tools.name_selector \
     --run-dir _working/output/20260110_115453_pyphen/ \
     --candidates candidates/pyphen_candidates_2syl.json \
     --name-class organisation \
     --count 50

**When to use this tool:**

- After generating candidates with name_combiner
- When you need filtered, ranked name lists per class
- For generating production-ready name pools
- To analyze policy effectiveness via statistics output

**Evaluation modes:**

- **hard** (default): Candidates with discouraged features are rejected entirely
- **soft**: Candidates with discouraged features receive -10 penalty instead of rejection

**Ordering modes:**

- **alphabetical** (default): Names with equal scores are sorted alphabetically for deterministic output
- **random**: Names with equal scores are shuffled within score groups using a seeded RNG for variety while maintaining determinism

Notes
-----

**Scoring:**

- Preferred features: +1 each
- Tolerated features: 0
- Discouraged features: Reject (hard) or -10 (soft)

Names are ranked by total score (descending). Tiebreaking for equal scores can be:

- **Alphabetical** (default): Deterministic ordering by name for reproducibility
- **Random**: Shuffled within score groups using a seed for variety while maintaining determinism

**Syllable count filtering:**

The selector filters by syllable count from the policy's ``syllable_range`` before
scoring. Candidates outside the range are excluded regardless of feature scores.

**Statistics output:**

The CLI displays rejection statistics to help tune policies:

.. code-block:: text

   Evaluated: 10,000
   Admitted: 7,420 (74.2%)
   Rejected: 2,580
   Rejection reasons:
     ends_with_stop: 2,580

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.name_selector
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: build_tools.name_selector.name_class
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: build_tools.name_selector.policy
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: build_tools.name_selector.selector
   :members:
   :undoc-members:
   :show-inheritance:
