# Getting started

By default, pocketsearch creates an **in-memory database** using a default 
search index schema containing only one field called 'text':

```Python
import pocketsearch
with pocketsearch.QuickPocket() as index:
    index.insert(text="Hello world !")
    for document in index.search(text="world"):
        print(document.text)
```

Be aware that the search methods limits results to 10 by default. Results 
are ordered by the rank of the search result which is calculated by the 
FTS extension in sqlite (see the [B25 function](https://www.sqlite.org/fts5.html#the_bm25_function) for more details) 
showing how relevant a document is to a given query. 

There is  support for slicing:

```Python
# returns the first three results
index.search(text="hello")[1:3]
```

Counting results can be done by

```Python
index.search(text="hello").count()
1
```
