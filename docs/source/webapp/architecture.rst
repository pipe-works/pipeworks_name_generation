Architecture
============

Current module layout:

- ``pipeworks_name_generation/webapp/server.py``
  Thin public entrypoint that wires CLI/runtime helpers and exposes the
  existing callable surface used by tests and scripts.
- ``pipeworks_name_generation/webapp/handler.py``
  ``BaseHTTPRequestHandler`` implementation focused on transport and dispatch.
- ``pipeworks_name_generation/webapp/endpoint_adapters.py``
  Route adapter functions that bridge dispatch to domain route modules.
- ``pipeworks_name_generation/webapp/route_registry.py``
  Central route-to-handler method mapping for GET/POST dispatch.
- ``pipeworks_name_generation/webapp/routes/*``
  Route-level behavior grouped by domain (static, import, generation, database).
- ``pipeworks_name_generation/webapp/storage.py``
  Compatibility facade that preserves legacy helper imports.
- ``pipeworks_name_generation/webapp/db/*``
  Concrete SQLite connection, schema, metadata repository, table-store, and
  importer helpers.
- ``pipeworks_name_generation/webapp/generation.py``
  Generation-domain mapping, selection stats, and deterministic sampling.
- ``pipeworks_name_generation/webapp/http/*``
  Request parsing and response transport utilities.
- ``pipeworks_name_generation/webapp/runtime.py``
  Port resolution and server process lifecycle helpers.
- ``pipeworks_name_generation/webapp/cli.py``
  Argument parsing and config->settings composition.
- ``pipeworks_name_generation/webapp/frontend/*``
  Template and static UI assets loaded at runtime.

Design constraints:

- Keep generation deterministic by using request-local ``random.Random(seed)``.
- Keep route handlers thin and side-effect boundaries explicit.
- Keep SQLite access in dedicated helpers to make query behavior testable.
- Initialize SQLite schema once at server startup; request handlers operate
  against an already-prepared database.
- Handler fallback initialization still exists for direct test harness usage and
  runs once per bound handler class.
