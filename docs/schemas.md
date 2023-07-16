# Defining Schemas

By default PocketSearch assumes that your search instance has only one field called text (the DefaultSchema).
However, a search index may have an arbitrary list of fields that can be searched. Schemas 
are defined through Schema classes:

```Python
from pocketsearch import Schema, PocketSearch
from pocketsearch import Text, Int, Real, Numeric, Blob, Date, Datetime

class FileContents(Schema):

    text = Text(index=True)
    filename = Text(is_id_field=True)
```

If we want to use this schema, we have to provide it to the PocketSearch instance:

```Python
# create pocketsearch instance and provide schema 
pocket_search.PocketSearch(schema=FileContents)
pocket_search.insert(text="Hello world",filename="a.txt")
```

## Field types

Following fields are available:

| Field        | SQLite data type | 
|--------------|-----------|
| Text         | TEXT   |
| Int          | INTEGER  |
| Real         | REAL  |
| Numeric      | Numeric  |
| Date         | Date  |
| Datetime     | Datetime  |

## Field options

Following options are available for fields:

* **index** - if the field is a Text field, a full text search index is created, otherwise a standard sqlite3 index is created
* **is_id_field** - a schema can only have one IDField. It is used by the .insert_or_update method to decide if a document should be inserted or an existing document should be updated.

With respect to naming your fields following restrictions apply:

* Fields **must not** start with an underscore.
* Fields **must not** contain double underscores.

Moreover field names may not be composed of reserved SQL keywords.

> **_NOTE:_**  While not explicitly set, pocketsearch automatically adds an "id" field to the schema (using the INTEGER data type plus the AUTOINCREMENT option of sqlite). It is used as the primary key for each document. The ID field is used to delete or 
update documents.

Here is an example on how to use field definitions:

```Python
    class Example(Schema):

        f1 = Int(index=True) 
        f2 = Text(index=True)
        f3 = Blob()
        f4 = Real()
        f5 = Datetime()
        f6 = Date()
```

## Selecting data using custom schemas

When you open a database in readonly mode that has a custom schema, you have to 
make sure, to provide the schema when creating the object:

```Python
pocketsearch = PocketSearch(schema=Example)
```

or using PocketReaders:

```Python
with PocketReader(schema=Example) as pocket_reader:
    pocket_reader.search(f2='some text')
```

## Inserting data

When inserting or updating data, provide the fields you want to populate as 
keyword arguments: 

```Python
pocketsearch = PocketSearch(schema=Example)
pocket_search.insert(f1=32,
                     f2='text',
                     f3='abc'.encode("utf-8"),
                     f4=2/3,
                     f5=datetime.datetime.now(),
                     f6=datetime.date.today())
```

> **_NOTE:_**  pocketsearch does not have a notion of mandatory and optional fields.
When using the .insert method you have to provide values for **all** fields.

## Updating data

When storing schemas, pocketsearch associates each document with a unique numeric 
id. This id can be retrieved through search:

```Python
pocket_search.search(f1=32)[0].id
1
```

Using the **id** of a document, you can run updates on a given document:

```Python
pocket_search.update(rowid=1, f1=48)
```

If want to update more fields, simply provide them as keyword arguments:

```Python
pocket_search.update(rowid=1, f1=48, f2='updated text')
```

## Insert or update method

The insert_or_update method allows you to either insert a document if it does 
not already exist or update its existing record in the database. For this to work,
the schema must at least define one field where the **is_id_field** option is set:

```Python
# If text.txt does not exist, a new document will be created:
pocket_search.insert_or_update(filename="text.txt",content="A")
# Now, the existing document will be updated with the new content:
pocket_search.insert_or_update(filename="text.txt",content="B")
```

## Deleting data

To delete a document, use:

```Python
pocket_search.delete(rowid=1)
```

If you want to delete the entire index use:

```Python
pocket_search.delete_all()
```

## Speeding up inserts: Write buffers

By default a commit to the database is executed after each modification to the database. 
If you want to speed up inserts, you can use the write_buffer_size option:

```Python
# Commit is done after 500 documents have been inserted:
pocketsearch.PocketSearch(db_name="my_db.db",write_buffer_size=500)
# Close the connection and write out any items left in the buffer
pocketsearch.close()
```

Alternativley you can use the PocketWriter context manager:

```Python
# Commit is done after 500 documents have been inserted using a PocketWriter
with pocketsearch.PocketWriter(db_name="my_db.db",write_buffer_size=500) as pocket_writer:
    pocket_writer.insert(text="Hello world")
```

The buffer applies to following operation in the database:

* Inserting documents
* Updating documents
* Deleting documents

## Improving performance: Write buffers

By default a commit to the database is executed after each modification to the database. 
If you want to speed up inserts, you can use the write_buffer_size option:

```Python
# Commit is done after 500 documents have been inserted:
pocketsearch.PocketSearch(db_name="my_db.db",write_buffer_size=500)
# Close the connection and write out any items left in the buffer
pocketsearch.close()
```

Alternativley you can use the PocketWriter context manager:

```Python
# Commit is done after 500 documents have been inserted using a PocketWriter
with pocketsearch.PocketWriter(db_name="my_db.db",write_buffer_size=500) as pocket_writer:
    pocket_writer.insert(text="Hello world")
```

The buffer applies to following operation in the database:

* Inserting documents
* Updating documents
* Deleting documents
