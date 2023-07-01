# pocketsearch
pocketsearch is a pure-Python full text indexing search engine based on sqlite and the [FTS5](https://www.sqlite.org/fts5.html) extension. It provides

- A simple API (inspired by the ORM layer of the Django web framework) for defining schemas and searching
- Support for multi-field indices including text, numeric and date search
- Support for prefix and initial token queries

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

From a database perspective, the new document will be immediately available 
to the search index, as each insert is followed by a database commit.

Be aware that the search methods limits results to 10 by default. Results 
are ordered by the rank of the search result which is calculated by the 
FTS extension in sqlite (see https://www.sqlite.org/fts5.html#the_bm25_function for more details) 
showing how relevant a document is to a given query. 

The API also supports iteration:

```Python
for document in pocket_search.search(text="hello"):
    print(document.text)
```

There is also supported for slicing:

```Python
pocket_search.search(text="hello")[1:3]
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

Please note, that prefix queries might get very slow as the index grows. To 
optimize performance, you can use prefix indices as described in the chapter 
on "schemas" in this README.

## Initial token queries

If you want to search only the first token at the begining of a document, use the 
allow_initial_token lookup:

```Python
pocket_search.search(text__allow_initial_token="^hello")
```

This will only match results that have 'hello' at the very beginning. 

## Phrase queries

If you want to search for phrases, use quotation marks:

```Python
pocket_search.search(text='"this is" "a phrase"').count()
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

## Highlighting and extracting snippets from results

FTS5 provides 2 functions to highlight tokens found in text and extracting snippets from a text. 
There are 2 methods to support this in pocketsearch:

```Python
pocket_search.search(text="hello").highlight("text")[0].text
*Hello* World !
```

The keyword arguments marker_start and marker_end allow you to control how highlighting is done:

```Python
pocket_search.search(text="hello").highlight("text",marker_start="[",marker_end="]")[0].text
[Hello] World !
```

The positional arguments of the highlight method represent the fields you want to hightlight. 

If you have very long text, you might want to only show a snippet with all terms found in your +
search results. This can be done with the snippet method. Assuming we have the article 
on Wikipedia article on [inverted indices](https://en.wikipedia.org/wiki/Inverted_index) in our database we can extract snippets like this:

```Python
pocket_search.search(text="inverted file").snippet("text",snippet_length=16)[0].text
'In computer science, an *inverted* index (also referred to as a postings list, postings *file*, or...'
```

Similar to the highlight method, the snippet method highlights tokens found. snippet_length defines 
the maximum number of tokens that should be contained in the snippet. It must be greater than 0 and lesser 
than 64. You can change the markers by providing text_before and text_after arguments:

```Python
pocket_search.search(text="inverted file").snippet("text",snippet_length=16,text_before="<",text_after=">")[0].text
```

# Schemas

A search index may have an arbitrary list of fields that can be searched. Schemas 
are defined through Schema classes:

```Python
from pocketsearch import Schema, PocketSearch
from pocketsearch import Text, Int, Real, Numeric, Blob, Date, Datetime

class FileContents(Schema):

    text = Text(index=True)
    filename = Text(is_id_field=True)

# create pocketsearch instance and provide schema
pocket_search.PocketSearch(schema=FileContents)
pocket_search.insert(text="Hello world",filename="a.txt")
```

## Fields

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

* **index** - if the field is a Text field, a full text search index is created, otherwise a standard sqlite3 index is created
* **is_id_field** - a schema can only have one IDField. It is used by the .insert_or_update method to decide if a document should be inserted or an existing document should be updated.

With respect to naming your fields following restrictions apply:

* Fields may not start with an underscore.
* Fields may not contain double underscores.

Moreover field names may not be composed of reserved SQL keywords.

> **_NOTE:_**  While not explicitly set, pocketsearch automatically adds an "id" field to the schema (using the INTEGER data type plus the AUTOINCREMENT option of sqlite). It is used as the primary key for each document. The ID field is used to delete or 
update documents.

## Queries on multi-field indices

Once the schema is created, you can query multiple fields:

```Python
# Searches field text for "world"
pocket_search.search(text="world")
# Searches documents that contain "world" in text AND have "a.txt" is a filename.
# Please note: as "filename" has not set its index option, only exact matches 
# will be considered.
pocket_search.search(text="world",filename="a.txt")
```

> **_NOTE:_**  When using multiple fields in search, the default boolean operation is AND.

### AND/OR queries on multiple fields

Similar to the Django web framework, you can use "Q Objects" to express OR queries on multiple fields:

```Python
from pocketsearch import Q
# Search for documents where text="world" OR filename="a.txt"
q = pocket_search.search(Q(text="world") | Q(filename="a.txt"))
# Search for documents where text="world" AND filename="a.txt"
q = pocket_search.search(Q(text="world") & Q(filename="a.txt"))
```

Please note, that you either have to use one notation or the other. You cannot mix 
Q objects with keyword arguments and you can only provide one field per Q object:

```Python
# This will NOT work:
pocket_search.search(Q(text="world") , filename="a.txt")
# This will work neither:
pocket_search.search(Q(text="world",filename="a.txt"))
```


## Setting prefix indices
To speed up prefix queries, you can setup prefix indices:

```Python
    class PrefixIndex1(Schema):
        '''
        Simple schema that sets a prefix index for 
        2,3 and 4 characters
        '''
        class Meta:
            prefix_index=[2,3,4]
        body = Text(index=True)
```

This will create prefix indices for 2,3 and 4 character prefixes.

# Inserting, updating and deleting data

## Handling updates and deletes

Using the id of a document, you can run updates:

```Python
pocket_search.update(rowid=1, text="The updated text.")
```

If want to update more fields, simply provide them as keyword arguments.

To delete a document, use:

```Python
pocket_search.delete(rowid=1)
```

## Using index readers to insert data

Normally we have a data source at hand (e.g. files in a file system or a source database) that we use to read 
data from. IndexReader classes can be used to build an index from such a data source. Assume, you want to 
index text files from a directory, we first define a schema:

```Python
class FileSchema(Schema):

        text = Text(index=True)
        filename = Text(is_id_field=True) 
```

Next, we create a PocketSearch and 

```Python
from pocketsearch import FileSystemReader
pocket_search = PocketSearch(schema=FileSchema)
reader = FileSystemReader(base_dir="/some/directory", file_extensions=[".txt"])
pocket_search.build(reader)
```

This will build the index. If a document has already been seen it will be updated, a new document will be 
inserted otherwise. 

Currently, the FileSystemReader is the only implementation provided, however you can easily implement your own 
by implementing the abstract class IndexError implementing a .read method. The .read method should return an 
iterable containing dictionaries whereas the dictionary's keys correspond to schema fields and its values 
the data you want to insert for the document. 

## Optimizing the index for query performance
If you have inserted a large volume of new documents, it might be sensible 
to optimize the index for query performance. This can be achieved by 
running VACUUM ANALYSE on the database, pocketsearch has a convenience 
method for this, that can be run e.g. after the indexing process is 
complete:

```Python
pocket_search = PocketSearch(db_name="my_db.db",writeable=True)
pocket_search.optimize()
```

Note, that this will close the current database connection and establish a new one. 

# More search options

## Searching numeric data

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

You can also provide an index for numeric data by setting ...

```Python
price = Int(index=True)
```

... to speed up queries.

## Searching date fields

pocketsearch also provides some (experimental) support for searching dates:

```Python
class AllFields(Schema):

    published=Datetime()

pocket_search = PocketSearch(schema=Product)
# Search documents published in year 2023
pocket_search.search(published__year=2023)
# Search document published after 2020
pocket_search.search(published__year__gt=2023)
# Search documents published in month 6
pocket_search.search(published__month=6)
# Search documents published on 21/6/2023:
pocket_search.search(published__month=21,published__month=6,published_year=2023)
```

> **_NOTE:_**  In search results, datefields are automatically converted to datetime and date objects respectivley. 


# Making your database persistent

The previous examples use an in-memory sqlite database. If you want to actually store 
the database, you have to provide a name:

```Python
pocket_search = PocketSearch(db_name="my_db.db",writeable=True)
# now, all operations will be done on the my_db database that is stored in the 
# current working directory.
```

When working with search indices that are stored on disk, *it is important to 
provide the writeable argument*, as any PocketSearch instance that works 
with file sqlite databases, is in read-only mode by default (unlike their 
in-memory counterpart.). 

# Behind the scenes: how searching works

pocketsearch uses the FTS5 extension of sqlite. More information can be found here:
https://www.sqlite.org/fts5.html

Internally, it:

* Creates two tables, one named "document" and one virtual table "document_idx" - the latter holds the full-text-search enabled files.
* The document_idx table is populated through triggers on the document table. 
* It uses the unicode61 tokenizer as default.

If you want to change the tokenizer, you can do so by overriding the Meta class of a schema:


```Python
from pocketsearch import Schema, PocketSearch

class FileContents(Schema):

    class Meta:
        '''
        Additional options for setting up FTS5
        See https://www.sqlite.org/fts5.html for more information.
        If a value is set to None, we leave it up to sqlite to
        set proper defaults.
        '''
        sqlite_tokenize = "unicode61" # change to available tokenizer of your choice
        sqlite_remove_diacritics = None
        sqlite_categories = None
        sqlite_tokenchars = None
        sqlite_separators = None    

    text = Text(index=True)
    filename = Text(is_id_field=True)
```

# Multiple indices in one database

You can have multiple indices in one database (only databases written to disk) by setting 
the "index_name" option:

```Python
pocket_search = PocketSearch(db_name="my_db.db",index_name="Product",schema=Product)
```

# Contribute
Pull requests are welcome. If you come across any issues, please report them 
at https://github.com/kaykay-dv/pocketsearch/issues

