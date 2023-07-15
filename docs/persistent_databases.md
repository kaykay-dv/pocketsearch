# Making your database persistent

If you want to store your database on disk you have to provide a filename 
for the database and provide the writeable keyword argument:

```Python
pocket_search = PocketSearch(db_name="my_db.db",writeable=True)
# now, all operations will be done on the my_db database that is stored in the 
# current working directory.
```

 