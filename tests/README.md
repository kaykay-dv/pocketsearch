# Introduction
This part of the repository contains experiments made with the pocketsearch library investigating 

* Time to build up an index
* RAM consumption during indexing

If you want to try the experiments on your own, make sure to install the requirements first:

```Python
pip install -r requirements.txt
```

> **_NOTE:_** Please note that the test data is not part of this repository and has to be downloaded from the referenced sources.

#  wikipedia.py
This experiment investigates indexing a dump of English Wikipedia abstracts (see 
https://en.wikipedia.org/wiki/Wikipedia:Database_download for more information).
The input data (retrieved on 10/06/2023) is roughly 1 GB in size. 

## Setup

Create a folder called ".data", download https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz and extract it 
to this directory. Then run:

```Python
python wikipedia.py
```

It will produce 2 pngs illustrating index runtime and RAM usage.

## Results

Run on an Apple M1 (8GB RAM)) using Python 3.8 this yields following results:

- It indexes more then 6.6 million abstracts
- ~ 15.000 abstracts are indexed per second (using the write_buffer_size option of PocketSearch's constructor)

The following diagram illustrates the number of documents indexed at time intervals 
(sample rate 1000 documents) in orange and RAM consumption in MB (blue line):

![Performance metrics](https://github.com/kaykay-dv/pocketsearch/blob/development/tests/wikipedia_avg_docs_indexed.png "Performance metrics")

> **_NOTE:_** Please be careful when generalizing these results. Indexing performance may vary depending on the nature of data you are actually written 
to the index and many other factors.

## Queries

Some queries run against the index (search for title OR text):

| Query        | Query time (in s) | 
|--------------|-----------|
| London         | 0.18s   |
| England        | 0.34s  |



