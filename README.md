# pocketsearch
A simple search engine for Python using sqlite3. It has no external requirements (besides Python itself) and runs on Python 3.8, Python 3.9, Python 3.10 and Python 3.11

# Status
![Unit tests main](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-main.yml/badge.svg)
![Unit tests development](https://github.com/kaykay-dv/pocketsearch/actions/workflows/unittests-development.yml/badge.svg)

# Installation

Run 

```Shell
pip install pocketsearch
```

to install the packacke.

# Getting started

```Python
from pocketsearch import PocketSearch

pocket_search = PocketSearch()
pocket_search.insert(text="Hello World !")
print(pocket_search.search("hello")[0].text)
'Hello World !'

```