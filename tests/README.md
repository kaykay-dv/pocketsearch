== Introduction ==
This part of the repository contains experiments made with the pocketsearch library investigating 

* Time to build up an index
* RAM consumption during indexing
* Query time

If you want to try the experiments on your own, make sure to install the requirements first:

```Python
pip install -r reqiurements.txt
```

> **_NOTE:_** Please note that the test data is not part of this repository and has to be downloaded from the referenced sources.

#  wikipedia.py
This experiment investigates indexing a dump of English Wikipedia abstracts (see 
https://en.wikipedia.org/wiki/Wikipedia:Database_download for more information).
The input data (retrieved on 01-02-2023) is roughly 1 GB in size. 

## Setup

It can be run using

```Python
python wikipedia.py
```

## Results

Run on an Apple M1 (8GB RAM)) using Python 3.8 this yields following results:

- It indexes more then 6.6 million abstracts
- ~ 2.000 abstracts are indexed per seconds

The following diagram illustrates the number of documents indexed at time intervals 
(sample rate 1000 documents) in orange and RAM consumption in MB (blue line):




