# Ordering results

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

**+** indicates ascending order, **-** descending order. If not explicitly given, 
ascending order is assumed. 

> **_NOTE:_** If order_by is not explicitly set, results are order by rank in descending order.

FTS5 returns a field called **rank** with each query indicating how relevant a document is to 
a given query. The field can be accessed in the search results:

```Python
pocket_search.search(text="hello")[0].rank
-0.007665
```

## Ordering by multiple fields

The following examples will order the results (1) by rank and then by text in descending order:

```Python
pocket_search.search(text__allow_boolean="hello OR world").order_by("rank","-text")
```

