Development
===========

Local run:

.. code-block:: bash

   python -m pipeworks_name_generation.webapp --config server.ini

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
- Database logic is implemented under ``pipeworks_name_generation/webapp/db``;
  ``webapp/storage.py`` exists as a compatibility facade for older imports.
