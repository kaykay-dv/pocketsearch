# pocketsearch

A pure-Python full-text indexing search library based on SQLite and the [FTS5](https://www.sqlite.org/fts5.html) extension, supporting both on-disk and in-memory search indexes.

- A simple API (inspired by the ORM layer of the Django web framework) for defining schemas and searching - no need to write SQL
- Multi-field indices using schemas including text, numeric and date/datetime search
- Prefix, phrase and initial token queries
- Spell checking
- Boolean search queries
- Highlightning search results and extracting snippets
- Autocomplete features

Pocketsearch does not have any dependencies other than Python (3.8 or higher) itself. 

# Quick start

Install using PIP:

```Shell
pip install pocketsearch
```

Create a search index using a PocketWriter and store it to database my_db.db:

```Python
import pocketsearch
with pocketsearch.PocketWriter(db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(text="Hello world")
```

Open the search index using a PocketReader to perform searches:

```Python
import pocketsearch
with pocketsearch.PocketReader(db_name="my_db.db") as pocket_reader:
    for result in pocket_reader.search(text="Hello world"):
        print(result.text)
```

You can define custom schemas to create multi-field indices:

```Python
import pocketsearch as ps

class Product(ps.Schema):

    price = ps.Int()
    description = ps.Text(index=True) # part of full text (FT) index
    category = ps.Text()  # not part of FT index

with ps.PocketWriter(db_name="my_db.db",schema=Product) as pocket_writer:
    pocket_writer.insert(description="Apple",category="Fruit",price=3.21)
    pocket_writer.insert(description="Orange",category="Fruit",price=4.11)

with ps.PocketReader(db_name="my_db.db",schema=Product) as pocket_reader:
    # Search for products with a price greater than or equal 3:
    print(pocket_reader.search(price__gte=3).count())

```

Read the complete documentation at https://pocketsearch.readthedocs.io/

# In-memory search index

Use QuickPocket to run the whole search index in-memory:

```Python
import pocketsearch
with pocketsearch.QuickPocket() as index:
    index.insert(text="Hello world !")
    print(index.search(text="world").count())
```

Once the context manager is closed, the database will disappear too. 

You can use the PocketSearch class directly if you prefer:

```Python
import pocketsearch
index = pocketsearch.PocketSearch()
index.insert(text="Hello world !")
print(index.search(text="world").count())
```

# Use cases

pocketsearch is intended for projects looking for a server-less, seamless integration into existing Python projects with low to medium-sized document collections. 

Please refer to https://github.com/kaykay-dv/pocketsearch/tree/main/tests/DCEP to see how pocketsearch can be used to index more than 160,000 documents. 


# Status
The package is actively maintained as of May 2025.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Unit tests main](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-main.yml/badge.svg)
![Unit tests development](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-development.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/pocketsearch/badge/?version=latest)](https://pocketsearch.readthedocs.io/en/latest/?badge=latest)




