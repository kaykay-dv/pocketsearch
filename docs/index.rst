.. pocketsearch documentation master file, created by
   sphinx-quickstart on Sat Jul 15 14:56:46 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pocketsearch's documentation!
========================================

pocketsearch is a pure-Python full text indexing search library based on sqlite and its `FTS5 extension <https://www.sqlite.org/fts5.html>`_ .

It provides

- A simple API (inspired by the ORM layer of the Django web framework) for defining schemas and searching - no need to write SQL
- Multi-field indices using schemas including text, numeric and date/datetime search
- Prefix, phrase and initial token queries
- Boolean search queries
- Highlightning search results and extracting snippets
- Autocomplete features

It does not have any external dependencies other than Python itself. pocketsearch has been tested on Python 3.8, 
Python 3.9, Python 3.10 and Python 3.11.

.. toctree::
   :maxdepth: 2

   installation.md
   getting_started.md
   persistent_databases.md
   schemas.md
   searching.md
   boolean_searching.md
   searching_non_text_data.md
   formatting.md
   advanced.md
   contribute.md
   license.md


