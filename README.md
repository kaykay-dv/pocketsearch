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

Be ware that the search methods limits results to 10 by default. Results 
are ordered by the rank of the search result which is calculated by the 
FTS extension in sqlite and showing how relevant a document is to a 
given query. 

```

## AND/OR queries

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

## Counting results

By invoking the count method you get the number of search results:

```Python
print(pocket_search.search(text__allow_boolean="hello OR world").count())
1

## Prefix queries

If you want to search for substrings, you can use prefix queries, by 
providing the allow_prefix lookup:

```Python
print(pocket_search.search(text__allow_prefix="hel*")[0].text)
```

## Combining lookups

Lookups can also be combined:

```Python
print(pocket_search.search(text__allow_prefix__allow_boolean="hel* OR wor*")[0].text)
Hello World !
```

## Ordering results

By invoking the order method you can influence how your results are sorted. By default 
search results are sorted by relevance to the query.

```Python
# Order by text in ascending order
pocket_search.search(text__allow_boolean="hello OR world").order_by("text")
# This is equivalent to the previous call:
pocket_search.search(text__allow_boolean="hello OR world").order_by("+text")
# Order by text in descending order
pocket_search.search(text__allow_boolean="hello OR world").order_by("-text")
```

# Contribute
Pull requests are welcome. If you come across any issues, please report them 
at https://github.com/kaykay-dv/pocketsearch/issues

