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

From a database perspective, the new document will be immediately available 
to the search index, as each insert is followed by a database commit.

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
```

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
# Schemas

A search index may have an arbitrary list of fields that can be searched. Schemas 
are defined through Schema classes:

```Python
from pocketsearch import Schema, PocketSearch

class FileContents(Schema):

    text = Text(index=True)
    filename = Text(is_id_field=True)

# create pocketsearch instance and provide schema
pocket_search.PocketSearch(schema=FileContents)
pocket_search.insert(text="Hello world",filename="a.txt")
```

Following fields are available:

| Field        | SQLite data type | 
|--------------|-----------|
| Text         | TEXT   |
| Int          | INTEGER  |
| Real         | REAL  |
| Numeric      | Numeric  |
| Blob         | Blob  |
| Date         | Date  |
| Datetime     | Datetime  |

Following options are available for fields:

* index - if the field is a Text field, a full text search index is created, otherwise a standard sqlite3 index is created
* is_id_field - a schema can only have one IDField. It is used by the .insert_or_update method to decide if a document should be inserted or an existing document should be updated.

With respect to naming your fields following restrictions apply:

* Fields may not start with an underscore.
* Fields may not contain double underscores.

Once the schema is created, you can query multiple fields:

```Python
# Searches field text for "world"
pocket_search.search(text="world")
# Searches documents that contain "world" in text and have "a.txt" is a filename.
# Please note: as "filename" has not set its index option, only exact matches 
# will be considered.
pocket_search.search(text="world",filename="a.txt")
```

Please note that by default an AND query is performed, thus only documents are
matched where text contains the word "world" and the filename is "a.txt"

# Searching numeric data

You can also search for numeric data:

```Python
class Product(Schema):

    price = Int()
    description = Text(index=True) # Full text index
    category = Text()  # not part of FT index
```

```Python
pocket_search = PocketSearch(schema=Product)
# Create some sensible test data before proceeding ...
# Matches products with price=3
pocket_search.search(price=3)
# Matches products with price greater than 3
pocket_search.search(price__gt=3)
# Matches products with price lower than 3
pocket_search.search(price__lt=3)
# Matches products with price lower than equal 3
pocket_search.search(price__lte=3)
# Matches products with price greater than equal 3
pocket_search.search(price__gte=3)
# Matches products with price greater than equal 3 AND where the description contains "apple".
pocket_search.search(price__gte=3,description="apple")
```

# Searching data fields

pocketsearch also provides some (experimental) support for searching dates:

```Python
class AllFields(Schema):

    published=Datetime()

pocket_search = PocketSearch(schema=self.Product)
# Search documents published in year 2023
pocket_search.search(published__year=2023)
# Search document published after 2020
pocket_search.search(published__year__gt=2023)
# Search documents published in month 6
pocket_search.search(published__month=6)
# Search documents published on 21/6/2023:
pocket_search.search(published__month=21,published__month=6,published_year=2023)
```

# Contribute
Pull requests are welcome. If you come across any issues, please report them 
at https://github.com/kaykay-dv/pocketsearch/issues

