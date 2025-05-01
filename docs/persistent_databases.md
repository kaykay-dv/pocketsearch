## PocketReader and PocketWriter classes

Use the PocketReader and PocketWriter context manager classes to create on-disk search indexes.

### Writing to an index

```Python
from pocketsearch import PocketWriter
with pocketsearch.PocketWriter(db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(text="Hello world")
```

The connection will be closed implicitly after the context manager has been left and any changes committed to the database.
If an exception occurrs, any changes will be rolled backed. 

Be aware that PocketWriters acquire an exclusive connection to the database, thus PocketWriters are considered thread-safe.
This means, a PocketWriter instance holds a lock on the database and other PocketWriter instances have to wait until the connection has been closed.
Note that PocketWriter instances may run in a time-out when waiting more than 5 seconds for a connection. In that case an exception is raised.

### Reading from an index

In the same way you can create a PocketReader instance to interact with the search  index in read-only mode:

```Python
from pocketsearch import PocketReader
with pocketsearch.PocketReader(db_name="my_db.db") as pocket_reader:
    pocket_reader.search(text="Hello world")
```

Unlike its PocketWriter counterpart, PocketReaders do not require exclusive access to the database. 





