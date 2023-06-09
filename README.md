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

By default, pocketsearch creates an in-memory database using a default 
search index schema containing only one field called 'text':

```Python
from pocketsearch import PocketSearch

pocket_search = PocketSearch()
pocket_search.insert(text="Hello World !")
print(pocket_search.search(text="hello")[0].text)
Hello World !

```

The FTS5 engines supports AND/OR queries. By 
default they are disabled in the API, if you want to make boolean 
queries, you have to use a lookup parameter in your query: 

```Python
from pocketsearch import PocketSearch

pocket_search = PocketSearch()
pocket_search.insert(text="Hello World !")
print(pocket_search.search(text__allow_boolean="hello OR world")[0].text)
Hello World !
```

Please note, that AND as well as OR are case-sensitive in this context.

If you want to search for substrings, you can use prefix queries, by 
providing the allow_prefix lookup:

```Python
print(pocket_search.search(text__allow_prefix="hel*")[0].text)
```

Lookups can also be combined:

```Python
print(pocket_search.search(text__allow_prefix__allow_boolean="hel* OR wor*")[0].text)
Hello World !
```

# Contribute
Pull requests are welcome. If you come across any issues, please report them 
at https://github.com/kaykay-dv/pocketsearch/issues

