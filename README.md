# pocketsearch
pocketsearch is a pure-Python full text indexing search engine based on sqlite and the [FTS5](https://www.sqlite.org/fts5.html) extension. It provides

- A simple API (inspired by the ORM layer of the Django web framework) for defining schemas and searching - no need to write SQL
- Multi-field indices using schemas including text, numeric and date search
- Prefix, phrase and initial token queries
- Boolean search queries
- Highlightning search results and extracting snippets
- Autocomplete features

It does not have any external dependencies other than Python itself. pocketsearch has been tested on Python 3.8, 
Python 3.9, Python 3.10 and Python 3.11.

pocketsearch is currently being tested on data from Wikipedia, indexing more than 6 million abstracts. If you 
are interested in preliminary performance tests, have a look at https://github.com/kaykay-dv/pocketsearch/tree/development/tests.

# Status
The package is currently in Beta status.

![Unit tests main](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-main.yml/badge.svg)
![Unit tests development](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-development.yml/badge.svg)


# Installation

Run 

```Shell
pip install pocketsearch
```

to install the package.

# Documentation

Documentation can be found at https://pocketsearch.readthedocs.io/


