# Autocomplete queries
The autocomplete feature is a convenience function that predicts the rest of an input based on the characters a user provides.

Here is an example:

```Python
# We provide 3 characters:
pocket_search.autocomplete(text="inv")[0]
'Inverted file'
```

Autocomplete works as follows:

* If only one token is entered the query is turned to a prefix query: ^inv* OR inv - thus the characters are searched at the beginning of the given field OR at any arbitrary position in the the field.
* If more tokens are provided (e.g. "inverted f" - separated by whitespaces), only the last token is turned to a prefix query. In this case the query becomes (^inverted OR inverted) AND f*

Some rules apply when using the autocomplete method:

* Look ups are not allowed (e.g. allow_boolean, etc.)
* Special operators are not allowed (e.g. ^ or *)
* You can only provide one field as keyword argument
* .autocomplete returns a Query objects, thus you can apply slicing, counting, order_by and highlighting as described above.