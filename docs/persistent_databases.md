# Reading and writing search indices

By default, a pocketsearch instance is created in-memory. If you want to store 
your database on disk you have to provide a filename for the database and provide the writeable keyword argument:

```Python
pocket_search = PocketSearch(db_name="my_db.db",writeable=True)
pocket_search.insert(text="Hello world")
pocket_search.close()
```

Invoking the .close method will commit any unwritten changes to the index and close 
the database connection to the index. If you want to keep the connection open and 
commit changes use

```Python
pocket_search.commit()
```

If you want to open the database at a later stage for searching open it in 
read-only mode:

```Python
pocket_search = PocketSearch(db_name="my_db.db")
pocket_search.search(text="Hello world")
```

or making it explicit:

```Python
pocket_search = PocketSearch(db_name="my_db.db",writeable=False)
pocket_search.search(text="Hello world")
```

Be aware that any attempt to write to a search index opened in read-only mode will 
result in an Exception.

## PocketReader and PocketWriter classes

The **preferred way** to handle writing and reading search indices is to use the PocketReader
and PocketWriter context manager classes:

### Writing to an index

```Python
from pocketsearch import PocketWriter
with pocketsearch.PocketWriter(db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(text="Hello world")
```

The connection will be closed implicitly after the context manager has been left and any changes committed to the database.
If an exception occurrs, any changes will be rolled backed. 

Be aware that PocketWriters acquire a mutual exclusive connection to the database, thus PocketWriters are considered thread-safe.
Having said that, if a PocketWriter writes any other threads have to wait until the exclusion connection has been released. If a 
time out has been reached reached an exception is thrown. 

### Reading from an index

In the same way you can create a PocketReader instance to interact with the search 
index in read-only mode:

```Python
from pocketsearch import PocketReader
with pocketsearch.PocketReader(db_name="my_db.db") as pocket_reader:
    pocket_reader.search(text="Hello world")
```






