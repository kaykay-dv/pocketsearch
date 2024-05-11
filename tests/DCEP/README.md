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

```bash
(venv) % python search_index.py 
DCEP Search - 162608 documents (CTRL+C to quit)> commission
Counting took 0.12 s
Found 141669 hits for commission:
./data/DCEP/strip/xml/EN/WQ/27213056__WQ__E-2010-7934__EN.txt : Question for written answer E-7934/2010
to the *Commission*
Rule 117
Martin Ehrenhauser (NI)
(5...
./data/DCEP/strip/xml/EN/WQA/18419573__WQA__E-2008-0147__EN.txt : Answer given by Mr Verheugen on behalf of the *Commission*
(18 March 2008)
Under the European...
./data/DCEP/strip/xml/EN/IMP-CONTRIB/20943323__IMP-CONTRIB__20081216-DLI-44594__EN.txt : DMAG European Parliament EUROMED Algeria - links European *Commission* External relations Bilateral Trade Relations European Union in...
./data/DCEP/strip/xml/EN/WQA/32378003__WQA__E-2011-008937__EN.txt : Joint answer given by Mr Šefčovič on behalf of the *Commission*
Written questions : E-008937/11...
./data/DCEP/strip/xml/EN/WQ/15171198__WQ__E-2007-3923__EN.txt : WRITTEN QUESTION E-3923/07
by Anna Záborská (PPE‑DE)
to the *Commission*
(1 August 2007...
./data/DCEP/strip/xml/EN/WQ/2305560__WQ__E-2003-1991__EN.txt : ...Did the *Commission* allow the Belgian police to interview the last *Commission* officials to have seen...
./data/DCEP/strip/xml/EN/WQ/1405826__WQ__E-2001-3713__EN.txt : ...A former *Commission* employee is, of course, not the property of the *Commission*. But there must...
./data/DCEP/strip/xml/EN/WQA/30644466__WQA__E-2011-002544__EN.txt : Answer given by Mr Potočnik on behalf of the *Commission*
(4 May 2011)
Poultry litter management...
./data/DCEP/strip/xml/EN/WQ/27088515__WQ__E-2010-7883__EN.txt : Question for written answer E-7883/2010
to the *Commission*
Rule 117
Silvana Koch-Mehrin (ALDE...
./data/DCEP/strip/xml/EN/WQ/20597768__WQ__E-2008-6316__EN.txt : ...The European Economic and Trade Office in Taiwan
The European *Commission*’s office in Taipei, Taiwan...
```





