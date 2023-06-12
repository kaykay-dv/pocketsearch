# Change log

## Version 0.7.1
* Fixed broken non-FTS index generation
* Fixed problem when multiple order_by fields are declared
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
