# Change log

## 0.9.0
* Improved error error message when using unknown lookups
* Introduced initial token queries using the allow_initial_token (^) lookup.
* Added prefix indicies (https://www.sqlite.org/fts5.html#prefix_indexes)

## Version 0.8.0
* Removed duplicate reference to "rank" in sql queries
* Added highlight sql function to highlight terms in search results
* Added snippet sql function to extract snippets from search results

## Version 0.7.1
* Fixed broken non-FTS index generation
* Fixed problem when multiple order_by fields are declared
* .to_sql() method of Field now raises proper exception if no data_type property is set
* Code clean up
* Document table is only generated if it does not exist
* Split up unit tests testing union searches

## Version 0.7
* Introduced .optimize method for running VACUUM ANALYSE in sqlite database.
* Introduced write_buffer concept to reduce number of commits

## Version 0.6
* Introduces IndexReader classes

## Version 0.5
* Initial version
