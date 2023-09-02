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
| Blob         | Blob  |
| Numeric      | Numeric  |
| Date         | Date  |
| Datetime     | Datetime  |

## Field options

Following options are available for fields:

* **index** - if the field is a Text field, a full text search index is created, otherwise a standard sqlite3 index is created
* **is_id_field** - a schema can **optionally** be flagged as IDField. This is not the internal id of a document in an index, but 
can be used to track unique ids coming from external data sources. For instance, if you are indexing files, you can flag the 
file name in your index as id field. It is used by the .insert_or_update method to decide if a document should be 
inserted or an existing document should be updated.

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

If you want to explicitly define an "id" field or use another name you can do so by adding it to the schema:

```Python
    class Example(Schema):

        record_id = IdField()
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
**id** field. (unless you have renamed it to something else ). 
This id can be retrieved through search:

```Python
# Assuming default id field:
pocket_search.search(f1=32)[0].id
1
# Assuming you have renamed it as illustrated in the example above:
pocket_search.search(f1=32)[0].record_id
1
```

Using the **id** of a document, you can run updates on a given document by 
providing the **rowid** keyword argument to the .update method:

```Python
# Updating f1 field to 48:
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

## Using legacy tables

(Added in version 0.13.0)

Sometimes, we already have an existing sqlite3 table with data that we want to put into a search index. 
Assume we have a table document defined in a database called "legacy.db":

```SQL
CREATE TABLE document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,    
    body TEXT,                       
    title TEXT,
    length float
)
```

```Python
We can now define a schema: 

    class LegacyTableSchema(Schema):

        title = Text(index=True)
        body = Text(index=True)
        length = Real()
```

In order to add fields "body" and "title" to a search index, we can explicitly provide the "index_name" 
keyword argument:

```Python
with PocketWriter(index_name="document",db_name="legacy.db",schema=self.LegacyTableSchema):
    pass
```

This will create a search index on top of the document table leaving the legacy table unchanged. Please 
note, that when we provide an index keyword argument to any other field than a text field, it will be ignored 
as legacy tables are never changed. 
Internally PocketSearch will add triggers to the existing database, so whenever something is added, updated or 
deleted, the search index will be updated too. The fields defined in the schema and fields defined in the legacy table must match, 
otherwise an exception is raised.

> **_NOTE:_** The PocketWriter class will automatically populate the search index with all documents found in the legacy table, 
so the first execution may take some time depending on the size of the table. 

## Schema migrations

PocketSearch does not provide means to update an existing schema, thus adding or removing fields. 
If you want to change the definition of a schema, it is suggested to create a new schema class, add the fields and copy the 
contents from the old schema to the new schema:

```Python
class Article(Schema):
    body=Text(index=True)
```

Assuming you have already inserted data, you could now change your schema by adding a field:

```Python
class Article(Schema):
    title=Text(index=True)
    body=Text(index=True)
```

We now create a new index and copy all existing data to the new index:

```Python
with PocketReader(index_name="document",db_name="legacy.db",schema=self.Article) as reader:
    # Copy all data from the "document" index to a new "document_v2" index:
    with PocketWriter(index_name="document_v2",db_name="legacy.db",schema=self.Article) as writer:
        for article in reader.search():
            writer.insert(title='some default',body=article.body)
```

> **_NOTE:_** Currently there is no way to remove the old index through the library. You have to 
delete the associated tables directly in the database.
 

