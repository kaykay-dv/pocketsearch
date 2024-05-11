import os
import pocketsearch
import requests
import tarfile
from io import BytesIO


if not(os.path.exists("data")):
    # Prepare data
    url = 'https://wt-public.emm4u.eu/Resources/DCEP-2013/strip/DCEP-strip-EN-pub.tar.bz2'
    print(f"Downloading {url} to ./data")
    response = requests.get(url,stream=True)
    if response.status_code == 200:
        # Open the tarfile from the downloaded content
        with tarfile.open(fileobj=BytesIO(response.content), mode='r:bz2') as tar:
            # Specify the directory where you want to extract the contents
            print(f"Unpacking {url} to ./data")
            tar.extractall(path='data')
            print("Extraction completed successfully.")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")

# Index directories:
reader = pocketsearch.FileSystemReader(base_dir=".")
with pocketsearch.PocketWriter(db_name="data/index.db",schema=reader.FSSchema) as writer:
    writer.build(reader,verbose=True)
    print("Building spell checker index")
    writer.spell_checker().build()