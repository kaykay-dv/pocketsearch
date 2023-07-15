# Advanced options

## Tokenization

In a search index tokenizers control how documents are split into individual "tokens", thus 
words. pocketsearch uses the internal *unicode61 tokenizer* provided by the FTS5 engine. 
If you want to customize the behavior of the tokenizer you can override the meta class 
of your schema:

```Python
from pocketsearch import Schema, PocketSearch, Unicode61

class FileContents(Schema):

    class Meta:
        tokenizer = Unicode61(remove_diacritics="1",
                              categories=None,
                              separators="")

    text = Text(index=True)
    filename = Text(is_id_field=True)
```

Following options are available:

* **remove_diacritics** - default is "2" - By default the tokenizer removes all diacritics (e.g. characters as **è** or **ä** become **e and **a** respectivley )from characters. If you want to keep diacritics, set to "0".
* **categories** - defines characters that are NOT separation characters through unicode categories.
* **separators** - define additional characters that should be considered as separation characters.

Please consult [the chapter on tokenization](https://www.sqlite.org/fts5.html#unicode61_tokenizer) in FTS5 to gain a deeper 
understanding on how the categories and separators option can be used.


## Index meta data

It is possible to get information on the tokens that are stored in an index:

```Python
list(pocket_search.tokens())
[{'token': 'the', 'num_documents': 2, 'total_count': 4}
{'token': 'is', 'num_documents': 3, 'total_count': 3}
{'token': 'fence', 'num_documents': 1, 'total_count': 2}
{'token': 'beyond', 'num_documents': 1, 'total_count': 1}
{'token': 'captial', 'num_documents': 1, 'total_count': 1}
{'token': 'england', 'num_documents': 1, 'total_count': 1}
{'token': 'europe', 'num_documents': 1, 'total_count': 1}
{'token': 'fox', 'num_documents': 1, 'total_count': 1}
{'token': 'france', 'num_documents': 1, 'total_count': 1}
{'token': 'he', 'num_documents': 1, 'total_count': 1}
{'token': 'in', 'num_documents': 1, 'total_count': 1}
{'token': 'jumped', 'num_documents': 1, 'total_count': 1}
{'token': 'now', 'num_documents': 1, 'total_count': 1}
{'token': 'of', 'num_documents': 1, 'total_count': 1}
{'token': 'over', 'num_documents': 1, 'total_count': 1}
{'token': 'paris', 'num_documents': 1, 'total_count': 1}]
```

* **token represents** the actual token that is stored in the index.
* **num_documents** represents the number of documents where the token occurs at least one time.
* **total_count** is the total number of occurrences in the index.

## Prefix indices

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

## Behind the scenes: how searching works

pocketsearch uses the [FTS5 extension of sqlite](https://www.sqlite.org/fts5.html). 

Internally, it:

* Creates two tables, one named "document" and one virtual table "document_idx" - the latter holds the full-text-search enabled files.
* The document_idx table is populated through triggers on the document table. 
* It uses the unicode61 tokenizer as default.

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


