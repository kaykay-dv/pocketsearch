# Defining Schemas

A search index may have an arbitrary list of fields that can be searched. Schemas 
are defined through Schema classes:

```Python
from pocketsearch import Schema, PocketSearch
from pocketsearch import Text, Int, Real, Numeric, Blob, Date, Datetime

class FileContents(Schema):

    text = Text(index=True)
    filename = Text(is_id_field=True)

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

Using the **id** field of a document, you can run updates:

```Python
pocket_search.update(rowid=1, text="The updated text.")
```

If want to update more fields, simply provide them as keyword arguments.

## Deleting data

To delete a document, use:

```Python
pocket_search.delete(rowid=1)
```

If you want to delete the entire index use:

```Python
pocket_search.delete_all()
```

