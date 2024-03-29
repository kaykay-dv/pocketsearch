# Spell checker

pocketsearch provides a simple implementation of a SpellChecker that can be used to 
correct misspelled tokens in a query. By default spell checking is turned **off**.
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

A spell checking dicitionary is built based on fields where index is set to True.

```Python
import pocketsearch

with pocketsearch.PocketWriter(schema=Example,db_name="my_db.db") as pocket_writer:
    pocket_writer.insert(title="Hello",body="World",category="Default")
    # Build spell checking dictionary:
    pocketwriter.spell_checker().build()
```

The spell checking dictionary is always built from scratch (thus any previous entries are deleted) when 
the .build method is invoked.

## Using spellchecking

We can now open the search index again and use spelling suggestions:

```Python
import pocketsearch
# now the database is written and the spellchecker is available
with pocketsearch.PocketReader(schema=Example,db_name="my_db.db") as pocket_reader:
    pocket_reader.suggest("hllo") 
```

.suggest returns a dictionary with possible corrections sorted by their edit distance 
to the token in the database:

```Python
pocket_reader.suggest("hllo")
{'hllo': [('hello', 1)]}
```

```Python
pocket_reader.suggest("wrld") 
{'wrld': [('world', 1)]}
```

```Python
pocket_reader.suggest("hllo wrld")
{'hllo': [('hello', 1)],'wrld': [('world', 1)]}
```

Spellchecking is done as follows:

* A separate pocketsearch instance is built in the background 
* The token table of the original pocketsearch instance is scanned and tokens are divided into [bigrams](https://en.wikipedia.org/wiki/Bigram)
* Bigrams are stored in the spellchecker dictionary
* .suggest tokenizes the query and splits each token into bigrams
* . suggest will then search the bigrams order them by rank and additionally calculate the [Levensthein distance](https://en.wikipedia.org/wiki/Levenshtein_distance) retrieving top 10 suggestions.





