# Spell checker

pocketsearch provides a simple implementation of a SpellChecker that can be used to 
correct misspelled tokens in a query. By default spell checking is turned off.
In order to support spellchecking, you have to to setup your schema as follows:

## Enabling spell checking

```Python
from pocketsearch import Schema, Text

class Example(Schema):

    class Meta:
        spell_check = True

    title = Text(index=True) # spellchecked
    body = Text(index=True) # spellchecked
    category = Text() # not spellchecked, as it is not part of the fulltext-search index

```

Any field of type **Text** where index is set to True will be considered for spellchecking.

A separate search index is built behind the curtains once the connection is closed:

```Python
import pocketsearch

with pocketsearch.PocketWriter(schema=Example,db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(text="Hello world")

## Using spellchecking

We can now open the search index again and use spelling suggestions:

```Python
import pocketsearch
# now the database is written and the spellchecker is available
with pocketsearch.PocketReader(schema=Example,db_name="my_db.db") as pocket_reader
    pocket_reader.suggest("hllo") # will provide ["hello"]
    pocket_reader.suggest("wrld") # will provide ["world"]
```

Spellchecking is done as follows:

* A separate pocketsearch instance is hold in the background 
* The token table of the original pocketsearch instance is scanned and tokens are divided into bigrams
* Bigrams are stored in the spellchecker index
* . suggest will search the bigrams order them by rank and additionally calculated the Levensthein distance for the top 15 suggestions.

## Limitations

* Currently the spell checking index is entirely rebuilt when inserting, updating or 
deleting data.



