# Boolean searches

## AND/OR queries on a single field

The FTS5 engines supports AND/OR queries. By 
default they are disabled in the .search method, if you want to make boolean 
queries, you have to use a so-called **lookup parameter** in your query: 

```Python
from pocketsearch import PocketSearch

pocket_search = PocketSearch()
pocket_search.insert(text="Hello World !")
# Search for hello OR world:
pocket_search.search(text__allow_boolean="hello OR world")[0].text
# Search for hello AND world:
pocket_search.search(text__allow_boolean="hello AND world")[0].text
# The following is equivalent to the previous query:
pocket_search.search(text__allow_boolean="hello world")[0].text
```

## AND on multiple fields

For the following example we assume a schema "FileContents":

```Python
from pocketsearch import Schema, PocketSearch

class FileContents(Schema):

    text = Text(index=True)
    filename = Text(is_id_field=True)
```

By providing multiple keyword arguments we can search for individual fields:

```Python
# Searches field text for "world"
pocket_search.search(text="world")
# Searches documents that contain "world" 
# in text AND have "a.txt" as a filename.
pocket_search.search(text="world",filename="a.txt")
```

## OR queries on multiple fields

When providing multiple keywords, pocketsearch will automatically convert the 
input into an AND query. If you want to perform OR queries on multiple fields 
you have to use so-called Q objects (Query objects):

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




