HTTP Examples
=============

Example requests and responses for the webapp JSON API.

Import package pair
-------------------

Request:

.. code-block:: text

   POST /api/import
   Content-Type: application/json

   {
     "metadata_json_path": "/path/to/goblin_flower-latin_selections_metadata.json",
     "package_zip_path": "/path/to/goblin_flower-latin_selections.zip"
   }

Success response:

.. code-block:: json

   {
     "message": "Imported package 'Goblin Flower Latin' with 8 txt table(s).",
     "package_id": 12,
     "package_name": "Goblin Flower Latin",
     "tables": [
       {
         "source_txt_name": "nltk_first_name_2syl.txt",
         "table_name": "pkg_12_goblin_flower_latin_nltk_first_name_2syl_1",
         "row_count": 9065
       }
     ]
   }

List generation package options
-------------------------------

Request:

.. code-block:: text

   GET /api/generation/package-options

Success response:

.. code-block:: json

   {
     "name_classes": [
       {
         "key": "first_name",
         "label": "First Name",
         "packages": [
           {
             "package_id": 12,
             "package_name": "Goblin Flower Latin",
             "source_txt_names": [
               "nltk_first_name_2syl.txt",
               "nltk_first_name_3syl.txt",
               "nltk_first_name_all.txt"
             ]
           }
         ]
       }
     ]
   }

List imported packages
----------------------

Request:

.. code-block:: text

   GET /api/database/packages

Success response:

.. code-block:: json

   {
     "packages": [
       {
         "id": 12,
         "package_name": "Goblin Flower Latin",
         "imported_at": "2026-02-08T00:00:00+00:00"
       }
     ],
     "db_path": "/path/to/name_packages.sqlite3"
   }

List tables for a package
-------------------------

Request:

.. code-block:: text

   GET /api/database/package-tables?package_id=12

Success response:

.. code-block:: json

   {
     "tables": [
       {
         "id": 1,
         "source_txt_name": "nltk_first_name_2syl.txt",
         "table_name": "pkg_12_goblin_flower_latin_nltk_first_name_2syl_1",
         "row_count": 9065
       }
     ]
   }

Fetch table rows
----------------

Request:

.. code-block:: text

   GET /api/database/table-rows?table_id=1&offset=0&limit=2

Success response:

.. code-block:: json

   {
     "table": {
       "id": 1,
       "package_id": 12,
       "source_txt_name": "nltk_first_name_2syl.txt",
       "table_name": "pkg_12_goblin_flower_latin_nltk_first_name_2syl_1",
       "row_count": 9065
     },
     "rows": [
       {"line_number": 1, "value": "alfa"},
       {"line_number": 2, "value": "briar"}
     ],
     "offset": 0,
     "limit": 2,
     "total_rows": 9065
   }

Generate names
--------------

Request:

.. code-block:: text

   POST /api/generate
   Content-Type: application/json

   {
     "class_key": "first_name",
     "package_id": 12,
     "syllable_key": "2syl",
     "generation_count": 5,
     "seed": 42,
     "unique_only": true,
     "output_format": "json"
   }

Success response:

.. code-block:: json

   {
     "message": "Generated 5 name(s) from imported package data.",
     "source": "sqlite",
     "class_key": "first_name",
     "package_id": 12,
     "syllable_key": "2syl",
     "generation_count": 5,
     "unique_only": true,
     "output_format": "json",
     "seed": 42,
     "names": [
       "alfa",
       "briar",
       "cinder",
       "dara",
       "elra"
     ]
   }

Validation error example
------------------------

.. code-block:: json

   {
     "error": "Field 'package_id' must be >= 1."
   }
