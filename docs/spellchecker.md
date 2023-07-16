# Spell checker

pocketsearch provides a simple implementation of a SpellChecker that can be used to 
correct misspelled tokens in a query. In order to support spellchecking, you have 
to to setup your schema as follows:

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

with pocketsearch.PocketWriter(db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(text="Hello world")
# now the database is written and the spellchecker is available
with pocketsearch.PocketReader(db_name="my_db.db") as pocket_reader
    pocket_reader.suggest("hllo") # will provide ["hello"]
    pocket_reader.suggest("hllo wrld") # will provide ["hello","world"]
```

Spellchecking is done as follows:

* A separate pocketsearch instance is hold in the background 
* The token table of the original pocketsearch instance is scanned and tokens are divided into bigrams
* Bigrams are stored in the spellchecker index
* . suggest will search the bigrams order them by rank and additionally calculated the Levensthein distance for the top 15 suggestions.





