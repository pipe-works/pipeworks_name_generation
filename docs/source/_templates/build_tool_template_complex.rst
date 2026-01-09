===============
[Tool Name]
===============

.. currentmodule:: build_tools.[tool_name]

Overview
--------

.. automodule:: build_tools.[tool_name]
   :no-members:

Core Concepts
-------------

[For complex tools only: Explain fundamental concepts users need to understand]

**Concept 1:**

Description of first key concept.

**Concept 2:**

Description of second key concept.

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.[tool_name].cli
   :func: create_argument_parser
   :prog: python -m build_tools.[tool_name]

Output Format
-------------

[Describe output files, naming conventions, and data structures]

**Example output structure:**

.. code-block:: text

    output/
    ├── file1.txt
    └── file2.json

**File descriptions:**

- ``file1.txt``: Description of what this file contains
- ``file2.json``: Description of what this file contains

Integration Guide
-----------------

[Explain how this tool fits in the build pipeline and when to use it]

**Example workflow:**

.. code-block:: bash

    # Step 1: Previous tool
    python -m build_tools.previous_tool --input data/

    # Step 2: This tool
    python -m build_tools.[tool_name] --input output/ --output processed/

    # Step 3: Next tool
    python -m build_tools.next_tool --input processed/

**When to use this tool:**

- Use case 1: Description
- Use case 2: Description

Advanced Topics
---------------

[For complex tools: Performance considerations, algorithm details, web interfaces, etc.]

**Performance:**

Performance benchmarks and optimization tips.

**Algorithm Details:**

Explanation of underlying algorithms or approaches.

**Troubleshooting:**

Common issues and their solutions.

Notes
-----

[Important caveats, limitations, or considerations]

**Important:**

- Note 1: Explanation
- Note 2: Explanation

**Build-time tool:**

This is a build-time tool only - not used during runtime name generation.

API Reference
-------------

.. automodule:: build_tools.[tool_name]
   :members:
   :undoc-members:
   :show-inheritance:
