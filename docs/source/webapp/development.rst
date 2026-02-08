Development
===========

Local run:

.. code-block:: bash

   python -m pipeworks_name_generation.webapp.server --config server.ini

API-only run (no UI/static assets):

.. code-block:: bash

   python -m pipeworks_name_generation.webapp.api --config server.ini

API-only run via flag:

.. code-block:: bash

   python -m pipeworks_name_generation.webapp.server --config server.ini --api-only

Useful checks:

.. code-block:: bash

   ruff check pipeworks_name_generation/webapp tests/test_pipeworks_webapp_server.py
   pytest -q tests/test_pipeworks_webapp_server.py tests/test_pipeworks_webapp_config.py

Documentation build:

.. code-block:: bash

   make -C docs html

Packaging note:

- ``pyproject.toml`` includes ``webapp/frontend/templates`` and
  ``webapp/frontend/static`` as package data so UI assets are available from
  installed wheels.
- Server startup performs one-time SQLite schema initialization before request
  handling begins.
- Database logic is implemented under ``pipeworks_name_generation/webapp/db``
  and imported directly by route adapters and runtime wiring.
