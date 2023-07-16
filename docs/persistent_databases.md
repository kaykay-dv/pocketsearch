# Reading and writing search indices

By default, a pocketsearch instance is created in-memory. If you want to store 
your database on disk you have to provide a filename for the database and provide the writeable keyword argument:

```Python
pocket_search = PocketSearch(db_name="my_db.db",writeable=True)
pocket_search.insert(text="Hello world")
pocket_search.close()
```

Invoking the .close method will commit any unwritten changes to the index and close 
the database connection to the index.

If you want to open the database at a later stage for searching open it in 
read-only mode:

```Python
pocket_search = PocketSearch(db_name="my_db.db")
pocket_search.search(text="Hello world")
```

## PocketReader and PocketWriter classes

An alternative way to handle writing and reading search indices is to use the PocketReader
and PocketWriter context manager classes:

```Python
from pocketsearch import PocketWriter
with pocketsearch.PocketWriter(db_name="my_db.db") as pocket_search:
    pocket_search.insert(text="Hello world")
```

The connection will be closed implicitly after the context manager has been left. 

In the same way you can open create PocketReader instance to interact with the search 
index in read-only mode:

```Python
from pocketsearch import PocketReader
with pocketsearch.PocketReader(db_name="my_db.db") as pocket_search:
    pocket_search.search(text="Hello world")
```

Again, the connection will be closed after context manager has been left.

