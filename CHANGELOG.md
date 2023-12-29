# Change log

## Version 0.21.0
* Added support for having multiple connections to in-memory databases (https://github.com/kaykay-dv/pocketsearch/issues/54)
* Added more stable support when using punctuation characters in queries (https://github.com/kaykay-dv/pocketsearch/issues/55)
* Added custom timestamp and date converters for sqlite date/timestamp data types to address Python 3.12 deprecation warning (https://github.com/kaykay-dv/pocketsearch/issues/52)
* Code clean up

**Breaking changes**
* Versions < 0.21 did not support multiple in-memory databases. The second in-memory database trying to establish a connection (with the first one still holding an active connection) would run into a connection time out.

## Version 0.20.1
* Small changes to README - now includes gettings started examples
* Added Python 3.12 to list of supported Python versions

## Version 0.20.0
* Added connection pool class and made PocketWriter instances thread-safe (https://github.com/kaykay-dv/pocketsearch/issues/44)
* Added possibility to use "legacy" (tables already defined in a sqlite3 database) tables (https://github.com/kaykay-dv/pocketsearch/issues/42)
* Fixed a bug resulting in SQL errors when using the @ symbol at certain places (https://github.com/kaykay-dv/pocketsearch/issues/49)
* Added proper handling for empty string queries (https://github.com/kaykay-dv/pocketsearch/issues/43)
* Added possiblity to define own "id" fields (https://github.com/kaykay-dv/pocketsearch/issues/42)
* Fixed a bug in SQL trigger definitions

**Breaking changes**
* PocketWriters are now using transactions. If an exception is raised the transaction is rolled back. (https://github.com/kaykay-dv/pocketsearch/issues/45)
* Building the spell checker dictionary has now to be invoked explicitly (https://github.com/kaykay-dv/pocketsearch/issues/46)
* Table creation (FTS5 tables) are now wrapped in an own transaction (https://github.com/kaykay-dv/pocketsearch/issues/45)

## Version 0.12.0
* Added context managers PocketReader and PocketWriter
* Added Spell Checker
* Fixed typos in the documentation
* Error that is thrown if a schema field does not have a data type is thrown earlier during schema creation
* Schema field objects are now (shallow-) copied when a schema instance is created to avoid side-effects when multiple schema instances are in use.
* Made PocketSearch._close a public method

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
