# pocketsearch
pocketsearch is a pure-Python full text indexing search library based on sqlite and the [FTS5](https://www.sqlite.org/fts5.html) extension. It provides

- A simple API (inspired by the ORM layer of the Django web framework) for defining schemas and searching - no need to write SQL
- Multi-field indices using schemas including text, numeric and date/datetime search
- Prefix, phrase and initial token queries
- Spell checking and query auto correction
- Boolean search queries
- Highlightning search results and extracting snippets
- Autocomplete features

It does not have any external dependencies other than Python itself. pocketsearch has been tested on Python 3.8, 
3.9, 3.10 and Python 3.11.

# Quick start

Install using PIP:

```Shell
pip install pocketsearch
```

to install the package.

Create an search index using a PocketWriter and store it to my_db.db:

```Python
import pocketsearch
with pocketsearch.PocketWriter(db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(text="Hello world")
```

Open a search index using a PocketReader:

```Python
import pocketsearch
with pocketsearch.PocketReader(db_name="my_db.db") as pocket_reader:
    for result in pocket_reader.search(text="Hello world"):
        print(result.text)
```

Read the complete documentation at https://pocketsearch.readthedocs.io/


# Status
The package is currently in Beta status.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Unit tests main](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-main.yml/badge.svg)
![Unit tests development](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-development.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/pocketsearch/badge/?version=latest)](https://pocketsearch.readthedocs.io/en/latest/?badge=latest)




