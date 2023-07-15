# Change log

## Version 0.11.0
* Fixed https://github.com/kaykay-dv/pocketsearch/issues/36
* Fixed https://github.com/kaykay-dv/pocketsearch/issues/35
* Introduced Tokenizer classes to setup FTS5 supported tokenizers
* Added .tokens() method (https://github.com/kaykay-dv/pocketsearch/issues/32)
* Added more logger.debug statements to plain SQL
* Added logger.debug statements for table creation
* Added sphinx-documentation and moved documentation to readthedocs

**Deprecated**:

* Versions < 0.11 had buggy sqlite_* meta options. These have been removed. Currently 
a dedicated Unicode61 tokenizer class with options is provided.

## Version 0.10.0
* Added typeahead convenience method
* Added warning when invoking | operator on .search method
* Added debug log info to execute_sql statement
* Added logging to unit tests
* Fixed a bug that caused the usage of # in a query resulting in a SQL parse error
* When a NEAR operator is found in the query, the query is quoted.

## Version 0.9.0
* Introduced Q objects for AND/OR queries
* Introduced initial token queries using the allow_initial_token (^) lookup.
* Added prefix indices (https://www.sqlite.org/fts5.html#prefix_indexes)
* Changed the way queries are done against the FTS index. Rather than using column-based queries, we now use the <table_name> MATCH 'fieldname:query' syntax.
* Improved error message when using unknown lookups
* Retired tests for "union" queries

**Deprecated**:

* Combining .search methods (union queries) through the | operator is now DEPRECATED. (and will be removed in 1.0.0) - Initially it was provided as means to express AND/OR queries, however Q objects can be used instead now. 

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
