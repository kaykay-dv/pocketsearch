# Basic searches

## The .search method

The **.search** method is used to conduct basic searches.

```Python
from pocketsearch import PocketSearch
# Create in-memory pocketsearch instance
pocket_search = PocketSearch()
# Create two documents
pocket_search.insert(text="Hello World !")
pocket_search.insert(text="Hello All !")
```

Each search returns an object of type SearchResult that acts like an 
ordinary Python list supporting indexing and slicing. Each search result 
contain a list of Document objects whereas the properties of each 
Document object correspond to the fields defined in the schema:

The .search method accept keyword arguments whereas each keyword argument
must correspond to a field defined in the schema.

```Python
# Return first result
pocket_search.search(text="hello")[0]
# Return second result
pocket_search.search(text="hello")[1]
# Return 'text' field of document 0
pocket_search.search(text="hello")[0].text
# Returns length of SearchResult
len(pocket_search.search(text="hello"))
```

When not providing any keyword arguments 10 results (if available) are 
returned (in the order as they have been inserted in the index)

```Python
pocket_search.search()[0].text
'Hello World !'
pocket_search.search()[1].text
'Hello All !'
```

The .search method supports iteration:

```Python
for document in pocket_search.search(text="hello"):
    print(document.text)
```

> **_NOTE:_** The actual search in the database is only conducted when 
the results are either accessed through iteration, indexing or slicing.

Thus,

```Python
# No search is performed when assigning 
# the results to a variable
results = pocket_search.search(text="Hello")
# When accessing the first result, 
# the query is performed in the database:
results[0].text
'Hello World !'
```

### Counting results

In order to count results, invoke the .count method on the results:

```Python
# Return the number of documents matching the given query:
pocket_search.search(text="Hello").count()
```

> **_NOTE:_** Using Python's built-in **len** function will not return 
the actual number of search results. By default the number of results 
is limited to 10 (unless you increase this by slicing), so len will 
return the size of the slicing window.

## Prefix queries

If you want to search for substrings, you can use prefix queries, by 
providing the allow_prefix lookup:

```Python
pocket_search.search(text__allow_prefix="hel*")[0].text
```

This will match any tokens in the text that start with "hel".

## Initial token queries

If you want to search only the first token at the begining of a field, use the 
allow_initial_token lookup:

```Python
pocket_search.search(text__allow_initial_token="^hello")
```

This will only match results that have 'hello' at the very beginning of the field text.

## Phrase queries

If you want to search for phrases, use quotation marks:

```Python
pocket_search.search(text='"this is" "a phrase"').count()
```



