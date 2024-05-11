DCEP is the Digital Corpus of the European Parliament comprising a variety of documents including (but not limited to) press releases, session and 
legislative documents - for more information refer to the [official website](https://joint-research-centre.ec.europa.eu/language-technology-resources/dcep-digital-corpus-european-parliament_en).

This directory uses the English corpus (containing roughly 160000 documents) and consists of 2 scripts:

create_index.py downloads the archive from the official website and 
extracts to a local directory ./data

It then creates a PocketSearch index using the IndexBuilder class and builds a spell checking dictionary:

```Python
# Index directories:
reader = pocketsearch.FileSystemReader(base_dir=".")
with pocketsearch.PocketWriter(db_name="data/index.db",
                               schema=reader.FSSchema) as writer:
    writer.build(reader,verbose=True)
    print("Building spell checker index")
    writer.spell_checker().build()
```

Depending on your machine, this will take roughly 1 minute to build. 

You can then use the **search_index.py** script to interactivley search the generated index:

```Python

```





