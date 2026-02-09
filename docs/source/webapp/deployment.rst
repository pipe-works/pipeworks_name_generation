Deployment (API-Only, Nginx + systemd)
======================================

This guide describes a **generic** production-style deployment for the
Pipeworks Name Generator API using:

- ``systemd`` for process management
- ``nginx`` as a reverse proxy
- explicit CORS allowlists
- SQLite for storage

It avoids environment-specific secrets and uses placeholders you should
replace with your own paths, usernames, and hostnames.

Overview
--------

Recommended layout:

- Run the API on **localhost only** (e.g. ``127.0.0.1:8100``)
- Terminate TLS in Nginx
- Use a **dedicated subdomain** for the name generator API (preferred)
- Configure CORS in Nginx using a strict allowlist

Prerequisites
-------------

- Python 3.12+ available on the host
- A clone of the repository on the server
- A writable data directory for SQLite
- ``nginx`` installed and serving HTTPS (Certbot or equivalent)
- Firewall permits 443/tcp inbound

Configuration File
------------------

Create an INI config for the server:

.. code-block:: ini

   [server]
   host = 127.0.0.1
   port = 8100

   db_path = /var/lib/pipeworks-namegen/name_packages.sqlite3
   favorites_db_path = /var/lib/pipeworks-namegen/user_favorites.sqlite3

   verbose = true
   api_only = true

Ensure the DB directory exists and is writable by the service user.

systemd Unit
------------

Create a service file at ``/etc/systemd/system/pipeworks-namegen.service``.
Replace paths and the Python interpreter as needed (venv or pyenv).

.. code-block:: ini

   [Unit]
   Description=Pipeworks Name Generator API
   After=network.target

   [Service]
   Type=simple
   User=YOUR_USER
   Group=YOUR_GROUP
   WorkingDirectory=/opt/pipeworks_name_generation
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/opt/pipeworks_name_generation/.venv/bin/python \
       -m pipeworks_name_generation.webapp.api \
       --config /opt/pipeworks_name_generation/server.ini
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target

Enable and start:

.. code-block:: bash

   sudo systemctl daemon-reload
   sudo systemctl enable --now pipeworks-namegen
   sudo systemctl status pipeworks-namegen

Nginx Reverse Proxy (CORS + TLS)
--------------------------------

The following pattern keeps CORS strict and centralized. Add the map in an
``http`` context (e.g. ``/etc/nginx/conf.d/namegen_cors_map.conf``):

.. code-block:: nginx

   map $http_origin $namegen_cors_origin {
       default "";
       "https://example.com" $http_origin;
       "https://www.example.com" $http_origin;
   }

   limit_req_zone $binary_remote_addr zone=namegen_api_limit:10m rate=20r/s;

Then define a dedicated server block (``/etc/nginx/sites-available/name.api.example.org``):

.. code-block:: nginx

   server {
       server_name name.api.example.org;

       location = / {
           return 301 /api/health;
       }

       location / {
           limit_req zone=namegen_api_limit burst=50 nodelay;

           if ($request_method !~ ^(GET|POST|OPTIONS)$) { return 405; }

           if ($request_method = OPTIONS) {
               add_header Access-Control-Allow-Origin $namegen_cors_origin always;
               add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
               add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
               add_header Access-Control-Max-Age 86400 always;
               add_header Vary "Origin" always;
               return 204;
           }

           add_header Access-Control-Allow-Origin $namegen_cors_origin always;
           add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
           add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
           add_header Vary "Origin" always;

           proxy_pass http://127.0.0.1:8100;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;

           proxy_connect_timeout 60s;
           proxy_send_timeout 60s;
           proxy_read_timeout 60s;

           client_max_body_size 50m;
       }

       add_header X-Content-Type-Options "nosniff" always;
       add_header X-Frame-Options "DENY" always;
       add_header X-XSS-Protection "1; mode=block" always;
       add_header Referrer-Policy "strict-origin-when-cross-origin" always;
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
       server_tokens off;

       listen 443 ssl;
       listen [::]:443 ssl ipv6only=on;
       ssl_certificate /etc/letsencrypt/live/name.api.example.org/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/name.api.example.org/privkey.pem;
       include /etc/letsencrypt/options-ssl-nginx.conf;
       ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
   }

   server {
       if ($host = name.api.example.org) {
           return 301 https://$host$request_uri;
       }
       listen 80;
       listen [::]:80;
       server_name name.api.example.org;
       return 404;
   }

Enable the site and reload Nginx:

.. code-block:: bash

   sudo ln -s /etc/nginx/sites-available/name.api.example.org /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx

Verification
------------

Local health check:

.. code-block:: bash

   curl -i http://127.0.0.1:8100/api/health

Public health check:

.. code-block:: bash

   curl -i https://name.api.example.org/api/health

CORS check:

.. code-block:: bash

   curl -i -H "Origin: https://example.com" https://name.api.example.org/api/health

Operational Notes
-----------------

- **CORS only affects browsers.** Server-to-server requests ignore CORS.
- **CORS is not authentication.** Use auth or network allowlists to protect private APIs.
- ``/api/import`` expects **server-local** file paths for metadata and ZIPs.
- Consider restricting endpoints in Nginx if you do not want public imports.
- If you see ``Configured port <X> is already in use``, stop the existing
  process and restart the systemd service.

.. warning::

   ``/api/import`` can be abused if left public. If your API is internet-facing,
   consider blocking or restricting it at the reverse proxy.

   Example (block public import endpoints):

   .. code-block:: nginx

      location = /api/import {
          deny all;
      }

   Example (allow only a trusted IP range):

   .. code-block:: nginx

      location = /api/import {
          allow 10.0.0.0/8;
          deny all;
      }

CORS FAQ
--------

**Q: Do I need CORS for curl, Python scripts, or server-to-server calls?**

No. CORS is enforced by **web browsers only**. Command-line tools and backend
services are not restricted by CORS.

**Q: Why does my browser fail but curl works?**

When a browser page calls your API from a different origin, the browser requires
CORS headers. Curl does not.

**Q: What should I put in the allowlist?**

Only the exact origins that will run browser JavaScript against the API
(``https://example.com`` and ``https://www.example.com`` are common). Avoid
wildcards in production.

Troubleshooting
---------------

Check service status:

.. code-block:: bash

   systemctl status pipeworks-namegen

View logs:

.. code-block:: bash

   journalctl -u pipeworks-namegen -b --no-pager

Check who is listening on the port:

.. code-block:: bash

   sudo ss -ltnp | rg 8100
