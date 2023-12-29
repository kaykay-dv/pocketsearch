import pocketsearch
import time

with pocketsearch.PocketReader(db_name="data/index.db",
                               schema=pocketsearch.FileSystemReader.FSSchema) as reader:
    while True:
        inp  = input("DCEP Search (CTRL+C to quit)> ")
        start=time.time()
        hits = reader.search(text=inp).count()
        elapsed = round(time.time()-start,2)
        print(f"Counting took {elapsed} s")
        print(f"Found {hits} hits for {inp}:")
        if hits == 0:
            print("Did you mean: %s" % reader.suggest(inp))
        for item in reader.search(text=inp).snippet("text"):
            print(item.filename,":",item.text)
