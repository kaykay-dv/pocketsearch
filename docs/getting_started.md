# Getting started

By default, pocketsearch creates an **in-memory database** using a default 
search index schema containing only one field called 'text':

```Python
from pocketsearch import PocketSearch
pocket_search = PocketSearch()
pocket_search.insert(text="Hello World !")
pocket_search.search(text="hello")[0].text
'Hello World !'
```

Be aware that the search methods limits results to 10 by default. Results 
are ordered by the rank of the search result which is calculated by the 
FTS extension in sqlite (see https://www.sqlite.org/fts5.html#the_bm25_function for more details) 
showing how relevant a document is to a given query. 

The API also supports iteration:

```Python
for document in pocket_search.search(text="hello"):
    print(document.text)
```

There is also support for slicing:

```Python
pocket_search.search(text="hello")[1:3]
```

Counting results can be done by

```Python
pocket_search.search(text="hello").count()
1
```
