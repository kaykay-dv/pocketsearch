# Searching non-text data

## Searching numeric data

You can also search for numeric data:

```Python
class Product(Schema):

    price = Int()
    description = Text(index=True) # Full text index
    category = Text()  # not part of FT index
```

```Python
pocket_search = PocketSearch(schema=Product)
# Create some sensible test data before proceeding ...
# Matches products with price=3
pocket_search.search(price=3)
# Matches products with price greater than 3
pocket_search.search(price__gt=3)
# Matches products with price lower than 3
pocket_search.search(price__lt=3)
# Matches products with price lower than equal 3
pocket_search.search(price__lte=3)
# Matches products with price greater than equal 3
pocket_search.search(price__gte=3)
# Matches products with price greater than equal 3 AND where the description contains "apple".
pocket_search.search(price__gte=3,description="apple")
```

You can also provide an index for numeric data by setting ...

```Python
price = Int(index=True)
```

... to speed up queries.

## Searching date fields

pocketsearch also provides some (experimental) support for searching dates:

```Python
class AllFields(Schema):

    published=Datetime()

pocket_search = PocketSearch(schema=Product)
# Search documents published in year 2023
pocket_search.search(published__year=2023)
# Search document published after 2020
pocket_search.search(published__year__gt=2023)
# Search documents published in month 6
pocket_search.search(published__month=6)
# Search documents published on 21/6/2023:
pocket_search.search(published__month=21,published__month=6,published_year=2023)
```

> **_NOTE:_**  In search results, datefields are automatically converted to datetime and date objects respectivley. 