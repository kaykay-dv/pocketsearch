'''
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE FOR ANY DAMAGES OR OTHER LIABILITY,
WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import threading
import types
import re
import datetime
import sqlite3
import os
import time
import abc
import copy
import uuid
import logging

from .fields import (
    Blob,
    Date,
    Datetime,
    Field,
    IdField,
    Int,
    Numeric,
    Rank,
    Real,
    Text,
)
from .schema import DefaultSchema, Schema
from .sql_query_components import (
    And,
    BooleanFilter,
    Count,
    DateFilter,
    Filter,
    Function,
    Highlight,
    Join,
    LimitAndOffset,
    LOOKUPS,
    MatchFilter,
    Or,
    OrderBy,
    Select,
    Snippet,
    SQLQueryComponent,
    Table,
)
from .tokenizers import Tokenizer, Unicode61

logger = logging.getLogger(__name__)


def convert_timestamp(value):
    '''
    Convert native sqlite timestamp value to datetime object
    '''
    return datetime.datetime.strptime(value.decode("utf-8").split(".")[0], "%Y-%m-%d %H:%M:%S")


def convert_date(value):
    '''
    Convert native sqlite date value to datetime object
    '''
    return datetime.datetime.strptime(value.decode("utf-8"), "%Y-%m-%d").date()


sqlite3.register_converter('timestamp', convert_timestamp)
sqlite3.register_converter('date', convert_date)

def normalize(value):
    '''
    Default text normalization.
    '''
    value = re.sub(r'\b((?:[A-Za-z]\.){2,}(?:[A-Za-z]\.?)?)', lambda m: m.group(1).replace('.', ''), value)
    return value

class Timer:
    '''
    A helper class that displays
    a progress bar in console.
    '''

    def __init__(self, precision=5):
        self.start = time.time()
        self.stop = self.start
        self.precision = precision
        self.total_time = 0
        self.laps = []
        self.snapshots = 0

    def lap(self, name):
        '''
        Add a lap to the timer. A lap has a name and is automatically
        associated with the the current time.
        '''
        if len(self.laps) > 0:
            self.total_time += time.time()-self.laps[-1:][0][1]
        self.laps.append((name, time.time()))

    def get_its(self):
        '''
        Returns current number of iterations per second
        '''
        return round(1/((self.stop-self.start)/self.snapshots), self.precision)

    def snapshot(self, more_info=""):
        '''
        Prints out the current iteration and statistics on time consumed.
        more_info maybe used on what is actually done.
        '''
        self.stop = time.time()
        self.snapshots = self.snapshots+1
        its = self.get_its()
        out = "%s iterations %s it/s %s s elapsed %s%s" % (self.snapshots, its,
                                                           round(self.stop-self.start,
                                                                 self.precision),
                                                           more_info, " "*15)
        print(out, end="\r", flush=True)

    def done(self):
        '''
        Prints a newline on console.
        '''
        print()

    def __str__(self):
        s = "----\n"
        longest_string, lap_time = max(self.laps, key=lambda x: len(x[0]))
        for lap_name, lap_time in self.laps:
            lap_name_display = lap_name + \
                (len(longest_string)-len(lap_name)) * " "
            s = s+"%s %s s\n" % (lap_name_display,
                                 round(lap_time, self.precision))
        s = s+"Total time: %s\n" % self.total_time
        s = s+"----\n"
        return s


class SearchResult:
    '''
    A wrapper over a list holding search results
    '''

    def __init__(self):
        self.results = []

    def __getitem__(self, index):
        return self.results[index]

    def __len__(self):
        return len(self.results)

    def __add__(self, obj):
        self.results.append(obj)
        return self

    def __iter__(self):
        return iter(self.results)


class Document:
    '''
    Returned in the search results.
    '''

    def __init__(self, fields):
        self.fields = fields

    def __repr__(self):
        return "<Document: %s>" % "," .join(["(%s,%s)" % (f, getattr(self, f)) for f in self.fields])


FTS_OPERATORS = ["-", ".", "#", "NEAR", "@"]


class SQLQuery:
    '''
    Helper class that constructs the SQLQuery from
    individual SQLQueryComponent objects
    '''

    def __init__(self, search_instance):
        self.search_instance = search_instance
        self.v_select = []
        self.v_from_tables = []
        self.v_joins = []
        self.v_where = []
        self.v_where_fts = []
        self.v_order_by = []
        self.v_limit_and_offset = None
        self.query_args = []
        self.boolean_query = False
        self.connect_fts_clause = None

    def count(self):
        '''
        Add a count(*) expression to the current query
        '''
        self.v_select.clear()
        self.v_select.append(Count(sql_query=self))

    def select(self, field, clear=False):
        '''
        Adds field to the selected fields clause in the statement.
        If clear is set to True, any items that have been added
        prior will be cleared.
        '''
        if clear:
            self.v_select.clear()
        self.v_select.append(Select(field=field, sql_query=self))

    def highlight(self, field, marker_start, marker_end):
        '''
        Marks given field for highlightening results
        '''
        for select in self.v_select:
            if select.field.name == field.name:
                select.function = Highlight(
                    marker_start=marker_start, marker_end=marker_end)

    def snippet(self, field, text_before, text_after, snippet_length=16):
        '''
        Marks given field for extracting snippets
        '''
        for select in self.v_select:
            if select.field.name == field.name:
                select.function = Snippet(
                    text_before=text_before, text_after=text_after, snippet_length=snippet_length)

    def table(self, table_name, clear=False):
        '''
        Adds a reference to the from clause in the SQL statement.
        If clear is set to True, any items that have been added
        prior will be cleared.
        '''
        if clear:
            self.v_from_tables.clear()
        self.v_from_tables.append(Table(table_name=table_name, sql_query=self))

    def join(self, table_left, table_right, left_field, right_field, clear=False):
        '''
        Adds a join in the SQL statement.
        If clear is set to True, any items that have been added
        prior will be cleared.
        '''
        if clear:
            self.v_joins.clear()
        self.v_joins.append(Join(table_left=table_left,
                                 table_right=table_right,
                                 left_field=left_field,
                                 right_field=right_field,
                                 sql_query=self))

    def where(self, field, lookup, operator, clear=False):
        '''
        Set filter items.
        '''
        if clear:
            self.v_where.clear()
        else:
            if field.fts_enabled():
                filter_clazz = MatchFilter
            else:
                filter_clazz = BooleanFilter
            if field.__class__ is Date:
                filter_clazz = DateFilter
            if field.fts_enabled():
                if operator is not None:
                    if len(self.v_where) > 0 and len(self.v_where_fts) == 0:
                        self.connect_fts_clause = operator(self)
                    else:
                        self.v_where_fts.append(operator(self))
                self.v_where_fts.append(filter_clazz(
                    field=field, value=lookup.value, lookup=lookup, sql_query=self))
            else:
                if operator is not None:
                    if len(self.v_where_fts) > 0 and len(self.v_where) == 0:
                        self.connect_fts_clause = operator(self)
                    else:
                        self.v_where.append(operator(self))
                else:
                    if len(self.v_where) > 0:
                        self.v_where.append(And(self))
                self.v_where.append(filter_clazz(
                    field=field, value=lookup.value, lookup=lookup, sql_query=self))

    def order_by(self, field, sort_dir=None, clear=False):
        '''
        Adds an order_by clause to the current statement. sort_dir can either be "+" (ascending)
        or "-" (descending)
        '''
        if clear:
            self.v_order_by.clear()
        self.v_order_by.append(
            OrderBy(field=field, sort_dir=sort_dir, sql_query=self))

    def limit_and_offset(self, limit, offset):
        '''
        Set limit and offset of query
        '''
        self.v_limit_and_offset = LimitAndOffset(
            limit=limit, offset=offset, sql_query=self)

    def add_value(self, value):
        '''
        Adds a value to the SQL string. This value will be later added to
        the arguments list of the execute_sql method.
        '''
        self.query_args.append(value)

    def to_sql(self):
        '''
        Render statement as SQL string
        '''
        self.query_args = []
        stmt = ["SELECT"]
        stmt.append(",".join([s.to_sql() for s in self.v_select]))
        stmt.append("FROM")
        stmt.append(",".join([t.to_sql() for t in self.v_from_tables]))
        if self.v_joins or self.v_where:
            stmt.append("WHERE")
            stmt.append(" AND ".join([j.to_sql() for j in self.v_joins]))
            if self.v_where:
                stmt.append("AND (")
                stmt.append(" ".join([w.to_sql() for w in self.v_where]))
                stmt.append(" ) ")
            if self.v_where_fts:
                if self.connect_fts_clause:
                    stmt.append(self.connect_fts_clause.to_sql())
                else:
                    stmt.append(" AND ")
                table_name = "%s_fts" % self.search_instance.schema.name
                stmt.append(table_name)
                stmt.append("MATCH ?")
                val = " ".join([w.to_sql() for w in self.v_where_fts])
                self.add_value(val)
        if len(self.v_order_by) > 0:
            stmt.append("ORDER BY")
        stmt.append(",".join([o.to_sql() for o in self.v_order_by]))
        if self.v_limit_and_offset is not None:
            stmt.append(self.v_limit_and_offset.to_sql())
        return " ".join(stmt), self.query_args


class QExpr:

    def __init__(self, **kwargs):
        if len(kwargs) > 1:
            raise Query.QueryError(
                "Only one keyword argument allowed in Q objects.")
        self.kwargs = kwargs
        self.operator = None

    def __repr__(self):
        return "<QExpr:%s %s>" % (self.operator, self.kwargs)


class Q:
    '''
    Q classes are used to express OR queries applied to 
    multiple fields of a schema
    '''

    def __init__(self, **kwargs):
        self.q_exprs = [QExpr(**kwargs)]

    def __or__(self, obj):
        for q_expr in obj.q_exprs:
            q_expr.operator = Or
            self.q_exprs.append(q_expr)
        return self

    def __and__(self, obj):
        for q_expr in obj.q_exprs:
            q_expr.operator = And
            self.q_exprs.append(q_expr)
        return self

    def __repr__(self):
        return " ".join([str(ex) for ex in self.q_exprs])

    def __iter__(self):
        return iter(self.q_exprs)


class Query:
    '''
    The Query class is responsible for managing and constructing SQL queries
    against the index. Most of the work is delegated to the SQLQuery class
    which builds the actual SQL query.
    '''

    class QueryError(Exception):
        '''
        Raised if the query could not be correctly interpreted.
        '''

    def __init__(self, search_instance, arguments, q_arguments):
        self.search_instance = search_instance
        id_field = self.search_instance.schema.get_id_field() or "id"
        self.arguments = arguments
        self.sql_query = SQLQuery(search_instance=search_instance)
        self.unions = []
        for field in self.search_instance.schema.get_fields():
            self.sql_query.select(field=field)
        if len(arguments) > 0:
            for argument in arguments.values():
                for lookup in argument.lookups:
                    self.sql_query.where(
                        field=argument.field, lookup=lookup, operator=None)
        else:
            for q_expr in q_arguments:
                for argument in q_expr.arguments.values():
                    for lookup in argument.lookups:
                        self.sql_query.where(
                            field=argument.field, lookup=lookup, operator=q_expr.operator)
        self.sql_query.table(table_name=self.search_instance.schema.name)
        self.sql_query.table(table_name="%s_fts" %
                             self.search_instance.schema.name)
        self.sql_query.join(
            self.sql_query.v_from_tables[0], self.sql_query.v_from_tables[1], id_field, "rowid")
        self.sql_query.order_by("+rank")
        self.sql_query.limit_and_offset(limit=10, offset=0)
        self._default_order_by_set = True
        self._default_values_set = True
        self.is_aggregate_query = False

    def _defaults_set(self):
        # Returns true if any default parameters set for .values and .order_by
        # clauses have been changed
        return self._default_order_by_set & self._default_values_set

    def count(self):
        '''
        Sets the query object into count mode.
        '''
        self.is_aggregate_query = True
        self.sql_query.count()
        for query in self.unions:
            query.sql_query.count()
        return self._query()

    def order_by(self, *args):
        '''
        Add order by clauses. To indicate ascending or descending order,
        arguments should start with either "+" or ".".
        '''
        for a in args:
            if a.startswith("+") or a.startswith("-"):
                field = self.search_instance.schema.get_field(
                    a[1:], raise_exception=True)
                sort_dir = a[0]
            else:
                field = self.search_instance.schema.get_field(
                    a, raise_exception=True)
                sort_dir = "+"
            # If the _defaults_set parameter is True, only the default sort order
            # in the constructor has been yet. In that case we clear the order by
            # list and set the new order by clause.
            self.sql_query.order_by(
                field, sort_dir, clear=self._default_order_by_set)
            self._default_order_by_set = False
        return self

    def _adapt_union_queries(self):
        '''
        Re-organizes the structure of the order by
        and limit clauses.
        '''
        if len(self.unions) > 0:
            # Copy order by clause and limit / offsets to the last query in the union
            last_query = self.unions[len(self.unions)-1]
            if not self.is_aggregate_query:
                last_query.sql_query.v_order_by = copy.copy(
                    self.sql_query.v_order_by)
                last_query.sql_query.v_limit_and_offset = copy.copy(
                    self.sql_query.v_limit_and_offset)
            else:
                last_query.sql_query.v_order_by.clear()
        # Clear all other clauses
        for obj in self.unions[:-1]:
            obj.sql_query.v_order_by.clear()
            obj.sql_query.v_limit_and_offset = None
        self.sql_query.v_order_by.clear()
        self.sql_query.v_limit_and_offset = None

    def __or__(self, obj):
        logger.warning(
            "Applying | operator on .search method is deprecated since version 0.9. Consider using Q objects instead.")
        if not isinstance(obj, Query):
            raise self.QueryError(
                "Only instances of class Query can be used with the OR operator.")
        if not obj._defaults_set() or not self._defaults_set():
            raise self.QueryError(
                "You cannot use .values and .order_by methods in the context of a union.")
        self.unions.append(obj)
        return self

    def values(self, *args):
        '''
        Set the values you want to have in the search result list.
        '''
        for a in args:
            field = self.search_instance.schema.get_field(
                a, raise_exception=True)
            self.sql_query.select(field, clear=self._default_values_set)
            self._default_values_set = False
        # Propagate this to union queries as well:
        for query in self.unions:
            query.values(*args)
        return self

    def highlight(self, *args, marker_start="*", marker_end="*"):
        '''
        Marks given field for highlight
        '''
        for a in args:
            field_obj = self.search_instance.schema.get_field(
                a, raise_exception=True)
            if not field_obj.fts_enabled():
                raise self.QueryError(
                    "highlight can only be applied to Text fields with index set to True.")
            self.sql_query.highlight(
                field_obj, marker_start=marker_start, marker_end=marker_end)
        return self

    def snippet(self, *args, text_before="*", text_after="*", snippet_length=16):
        '''
        Marks given field for snippet
        '''
        if snippet_length <= 0 or snippet_length >= 64:
            raise self.QueryError(
                "snippet_length must be greater than 0 and lesser than 64.")
        for a in args:
            field_obj = self.search_instance.schema.get_field(
                a, raise_exception=True)
            if not field_obj.fts_enabled():
                raise self.QueryError(
                    "snippet can only be applied to Text fields with index set to True.")
            self.sql_query.snippet(field_obj, text_before=text_before,
                                   text_after=text_after, snippet_length=snippet_length)
        return self

    def _build_results(self, results):
        documents = SearchResult()
        for result in results:
            document = Document(result.keys())
            for field in result.keys():
                setattr(document, field, result[field])
            documents = documents + document
        return documents

    def _query(self):
        if len(self.unions) > 0:
            self._adapt_union_queries()
        stmt, query_args = self.sql_query.to_sql()
        for query in self.unions:
            u_stmt, u_ar = query.sql_query.to_sql()
            stmt += " UNION " + u_stmt
            query_args = query_args + u_ar
        if self.is_aggregate_query:
            count = 0
            for sub_count in self.search_instance.execute_sql(stmt, *query_args):
                count = count+sub_count["COUNT(*)"]
            return count
        return self._build_results(self.search_instance.execute_sql(stmt, *query_args))

    def __getitem__(self, index):
        self.is_aggregate_query = False
        if isinstance(index, slice):
            try:
                index_start = int(index.start)
                index_stop = int(index.stop)
            except Exception as exc:
                raise self.QueryError(
                    "Slicing arguments must be positive integers and not None.") from exc
            self.sql_query.limit_and_offset(
                limit=index_stop, offset=index_start)
            return self._query()
        else:
            try:
                self.sql_query.limit_and_offset(limit=1, offset=int(index))
            except Exception as exc:
                raise self.QueryError(
                    "Index arguments must be positive integers and not None.") from exc
        return self._query()[0]

    def __iter__(self):
        return iter(self._query())


class PocketContextManager(abc.ABC):

    def __init__(self, db_name=None,
                 index_name="documents",
                 schema=DefaultSchema,normalize=None):
        self.pocketsearch = PocketSearch(
            index_name=index_name, db_name=db_name, schema=schema,normalize=normalize)

    def __enter__(self, *args, **kwargs):
        return self.pocketsearch

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.pocketsearch.close()

class QuickPocket(PocketContextManager):
    '''
    In-memory search index
    '''

    def __init__(self,schema=DefaultSchema,normalize=None):
        self.pocketsearch = PocketSearch(schema=schema,normalize=normalize)        

class PocketReader(PocketContextManager):
    '''
    Simple context manager opening a pocket search instance 
    in read-only mode.
    '''


class PocketWriter(PocketContextManager):
    '''
    Simple context manager opening a pocket search instance 
    in read/write mode.
    '''

    def __init__(self, db_name=None,
                 index_name="documents",
                 schema=DefaultSchema,
                 normalize=None):
        self.pocketsearch = PocketSearch(
            index_name=index_name,
            db_name=db_name,
            schema=schema,
            writeable=True,
            normalize=normalize
        )
        self.pocketsearch.execute_sql("begin")

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            if self.pocketsearch.schema._meta.spell_check:
                logger.debug("Building spell checking dictionary")
            self.pocketsearch.execute_sql("commit")
        else:
            logger.exception(exc_traceback)
            logger.debug("Rolling back transaction")
            self.pocketsearch.execute_sql("rollback")
        self.pocketsearch.close()


class SpellChecker:
    '''
    A simplistic implementation of a spellchecker using a PocketSearch 
    instance in the background. 
    '''

    class SpellCheckerSchema(Schema):
        '''
        Schema to store the spelling suggestions
        '''
        token = Text()
        bigrams = Text(index=True)
        bigrams_length = Int(index=True)

    def __init__(self, search_instance):
        self.search_instance = search_instance
        self.spell_checker = PocketSearch(db_name=search_instance.db_name,
                                          index_name="spellcheck_%s" % search_instance.index_name,
                                          writeable=search_instance.writeable,
                                          schema=self.SpellCheckerSchema,
                                          connection=search_instance.connection)

    def _generate_bigrams(self, token, operator=" "):
        bigrams = []
        for i in range(len(token) - 1):
            bigram = token[i:i+2]
            bigrams.append(bigram)
        return operator.join(bigrams)

    def _levenshtein_distance(self, word1, word2):
        m, n = len(word1), len(word2)

        # Create a distance matrix
        distance = [[0] * (n + 1) for _ in range(m + 1)]

        # Initialize the first row and column of the matrix
        for i in range(m + 1):
            distance[i][0] = i
        for j in range(n + 1):
            distance[0][j] = j

        # Calculate the minimum edit distance
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if word1[i - 1] == word2[j - 1]:
                    distance[i][j] = distance[i - 1][j - 1]
                else:
                    distance[i][j] = min(
                        distance[i - 1][j] + 1,  # Deletion
                        distance[i][j - 1] + 1,  # Insertion
                        distance[i - 1][j - 1] + 1  # Substitution
                    )
        return distance[m][n]

    def build(self):
        '''
        Walk through the token of the given search_instance and populate the 
        spell checking index. This methods clear the spelling index and 
        builds it entirely from scratch again. 
        '''
        self.spell_checker.delete_all()
        for token_info in self.search_instance.tokens():
            token = token_info.get("token")
            bigrams = self._generate_bigrams(token)
            self.spell_checker.insert(
                token=token, bigrams=bigrams, bigrams_length=len(bigrams))

    def suggest(self, query):
        '''
        Returns a list of auto corrections for the given query
        '''
        results = {}
        for cleaned_token in set(Unicode61().tokenize(query)):
            if len(cleaned_token) > 1:
                results[cleaned_token] = []
                for result in self.spell_checker.search(bigrams__allow_boolean=self._generate_bigrams(cleaned_token, " OR "))[0:10]:
                    results[cleaned_token].append(
                        (result.token, self._levenshtein_distance(result.token, cleaned_token)))
                results[cleaned_token] = sorted(
                    results[cleaned_token], key=lambda x: x[1])
        return results


class PocketSearch:
    '''
    Main class to interact with the search index.
    '''

    class IndexError(Exception):
        '''
        Thrown if there is a problem with the schema definition itself.
        '''
    class FieldError(Exception):
        '''
        Thrown if arguments provided to the .search method throw an error.
        '''
    class DocumentDoesNotExist(Exception):
        '''
        Thrown, if accessing a document through the .get method that does not exist.
        '''
    class DatabaseError(Exception):
        '''
        Thrown, if the SQL query contains errors.
        '''

    class Argument:
        '''
        Helper class to store fields and its look ups provided through keyword arguments.
        '''

        def __init__(self, field, lookups):
            self.field = field
            self.lookups = lookups

    class Lookup:
        '''
        Helper class to store lookups for a specific field
        '''

        def __init__(self, names, value,normalize=None):
            self.names = names
            if isinstance(value,str) and normalize:
                self.value = normalize(value)
            else:
                self.value = value

    def __init__(self, db_name=None,
                 index_name="documents",
                 schema=DefaultSchema,
                 writeable=False,
                 connection=None,
                 normalize=None):
        self.db_name = db_name
        self.schema = schema(index_name)
        self.db_name = db_name
        self.db_id = uuid.uuid4()
        self.connection = None
        self.normalize = normalize
        if self.normalize is not None and not(isinstance(self.normalize, types.FunctionType)):
            raise ValueError("normalize must be a function.")
        if writeable or db_name is None:
            # If it is an in-memory database, we allow writes by default
            self.writeable = True
        else:
            self.writeable = False
        self.index_name = index_name
        try:
            if connection is None:
                self.connection = self._open()
            else:
                self.connection = connection
                logger.debug(
                    "Re-using existing database connection %s" % connection)
            self.cursor = self.connection.cursor()
            if self.writeable:
                self._create_table(self.schema.name)
            if self.schema._meta.spell_check:
                self._spell_checker = SpellChecker(search_instance=self)
            else:
                self._spell_checker = None
        except:
            # so if setting up the object instance fails, close the connection
            # and re-raise the exception
            self.close()
            raise

    def spell_checker(self):
        '''
        Returns spell checker instance (if available)
        '''
        if self.spell_checker is None:
            raise self.schema.SchemaError(
                "PocketSearch instance is not configured to use spell checking. Check your schema definition.")
        return self._spell_checker

    def _u_name(self):
        if self.db_name is None:
            return "::%s" % self.db_id
        return self.db_name

    def _open(self):
        return connection_pool.get_connection(db_name=self.db_name,
                                              writeable=self.writeable,
                                              conn_id=self.db_id)

    def _close(self):
        if self.connection:
            if self.writeable:
                self.commit()
            logger.debug("Closing connection")
            connection_pool.release_connection(self.db_name,
                                               self.connection,
                                               self.writeable,
                                               conn_id=self.db_id)

    # For backwards compatibility reasons:
    close = _close

    def assure_writeable(self):
        '''
        Tests, if the index is writable.
        '''
        if not self.writeable:
            raise self.IndexError(
                "Index '{schema_name}' has been opened in read-only mode. Cannot write changes to index.".format(schema_name=self.schema.name))

    def execute_sql(self, sql, *args):
        '''
        Executes a raw sql query against the database. sql contains the query, *args the arguments.
        '''
        logger.debug("sql=%s,args=%s" % (f"{sql}", args))
        return self.cursor.execute(f"{sql}", args)

    def _populate_fts(self):
        '''
        Manually populates the FTS5 virtual table with content found in 
        the index_name table.
        '''
        for row in self.cursor.execute('select * from %s' % self.index_name):
            params = {}
            for col in row.keys():
                if col != "id":
                    params[col] = row[col]
            self.insert("%s_fts" % self.index_name, **params)

    def _format_sql(self, index_name, fields, sql):
        '''
        Helper method to create triggers for the virtual FTS5 table.
        '''
        return sql.format(
            index_name=index_name,
            cols=", ".join([field.to_sql(index_table=True)
                           for field in fields if field.fts_enabled()]),
            new_cols=", ".join(["new.%s" % field.to_sql(index_table=True)
                               for field in fields if field.fts_enabled()]),
            old_cols=", ".join(["old.%s" % field.to_sql(index_table=True)
                               for field in fields if field.fts_enabled()]),
        )

    def _create_additional_options(self):
        '''
        Reads the options defined in the meta class of the schema to provide additional information
        for the FTS table creation, specifically the tokenization process.
        '''
        m = self.schema._meta
        return ", " + m.tokenizer.to_sql()

    def _create_prefix_index(self):
        prefix_index = self.schema._meta.prefix_index
        if prefix_index is not None:
            if not isinstance(prefix_index, list):
                raise self.schema.SchemaError(
                    "prefix_index must be list containing positive integer values")
            if not all(isinstance(item, int) and item > 0 for item in prefix_index):
                raise self.schema.SchemaError(
                    "prefix_index list should only contain positive integer values.")
            # eliminate duplicates
            prefix_index = set(prefix_index)
            return ", prefix='{prefix_index}'".format(prefix_index=" ".join(str(item) for item in prefix_index))
        return ""

    def _table_exists(self):
        self.cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (self.index_name,))
        table_exists = self.cursor.fetchone()[0] > 0
        self.cursor.execute(
            "SELECT * from pocket_search_master where name = ?", (self.index_name,))
        managed = self.cursor.fetchone()
        if managed is None:
            mgmt_type = (False, "")
        else:
            mgmt_type = (True, managed["content"])
        return table_exists, mgmt_type

    def _check_fields(self):
        self.cursor.execute("PRAGMA table_info(%s)" % self.index_name)
        table_info = self.cursor.fetchall()
        fields = {}
        mappings = {
            "INT": "INTEGER",
            "FLOAT": "REAL"
        }
        for column in table_info:
            if column[2].upper().startswith("VARCHAR"):
                data_type = "TEXT"
            else:
                data_type = mappings.get(column[2].upper(), column[2])
            fields[column[1]] = data_type
        # check schema
        for field, definition in self.schema.fields.items():
            if field != "rank":
                if field not in fields:
                    raise self.DatabaseError(
                        f"'{field}' is present in the schema but has not been defined in the legacy table.")
                if definition.data_type != fields[field]:
                    legacy_definition = fields[field]
                    raise self.DatabaseError(f"'{field}' has data type '{definition.data_type}' in schema but '{legacy_definition}' was expected.")
        return True

    def _create_table(self, index_name):
        '''
        Private method to create the SQL tables used by the index.
        '''
        fields = []
        index_fields = []
        default_index_fields = []  # non-FTS index fields
        id_field = self.schema.get_id_field() or "id"
        for field in self.schema:
            if not field.hidden:
                if field.index and field.fts_enabled():
                    index_fields.append(field)
                elif field.index and not field.fts_enabled():
                    default_index_fields.append(field)
                fields.append(field)
        if len(index_fields) == 0:
            raise IndexError(
                "Schema does not have a single indexable FTS field.")
        standard_fields = ", ".join([field.to_sql() for field in fields])
        fts_fields = ", ".join([field.to_sql(index_table=True)
                               for field in fields if field.fts_enabled()])
        additional_options = self._create_additional_options()
        prefix_index = self._create_prefix_index()
        # Create meta table holding all pocketsearch created search index names:
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS pocket_search_master (name TEXT unique, content TEXT)")
        # Check if the table is already there and if it is under management of pocketsearch:
        table_exists, mgmt_type = self._table_exists()
        content = self.index_name
        if table_exists:
            # This is a table that has been created outside of pocketsearch.
            # We will create a contentless fts5 virtual table:
            self._check_fields()
            managed, content = mgmt_type
        sql_table = f"CREATE TABLE IF NOT EXISTS {index_name}({standard_fields})"
        sql_virtual_table = f'''
        CREATE VIRTUAL TABLE IF NOT EXISTS {index_name}_fts USING fts5({fts_fields},
            content='{content}', content_rowid='{id_field}' {additional_options} {prefix_index});
        '''
        # aux tables
        sql_aux_table = f'''CREATE VIRTUAL TABLE IF NOT EXISTS {
            index_name}_fts_v USING fts5vocab('{index_name}_fts', 'row');'''
        # Trigger definitions:
        old_cols = ", ".join(["old.%s" % field.to_sql(index_table=True)
                             for field in fields if field.fts_enabled()])
        new_cols = ", ".join(["new.%s" % field.to_sql(index_table=True)
                             for field in fields if field.fts_enabled()])
        sql_trigger_insert = f'''
        CREATE TRIGGER IF NOT EXISTS {index_name}_ai AFTER INSERT ON {index_name} BEGIN
        INSERT INTO {index_name}_fts(rowid, {fts_fields}) VALUES (new.{id_field}, {new_cols});
        END;'''
        sql_trigger_delete = f'''
        CREATE TRIGGER IF NOT EXISTS {index_name}_ad AFTER DELETE ON {index_name} BEGIN
        INSERT INTO {index_name}_fts({index_name}_fts, rowid, {fts_fields}) VALUES('delete', old.{id_field}, {old_cols});
        END;'''
        sql_trigger_update = f'''
        CREATE TRIGGER IF NOT EXISTS {index_name}_au AFTER UPDATE ON {index_name} BEGIN
        INSERT INTO {index_name}_fts({index_name}_fts, rowid, {fts_fields}) VALUES('delete', old.{id_field}, {old_cols});
        INSERT INTO {index_name}_fts(rowid, {fts_fields}) VALUES (new.{id_field}, {new_cols});
        END;
        '''
        self.cursor.execute("begin")
        self.cursor.execute(sql_table)
        self.cursor.execute(sql_aux_table)
        logger.debug(sql_table)
        logger.debug(sql_virtual_table)
        logger.debug(sql_trigger_insert)
        logger.debug(sql_trigger_delete)
        logger.debug(sql_trigger_update)
        self.cursor.execute(sql_virtual_table)
        self.cursor.execute(self._format_sql(
            index_name, fields, sql_trigger_insert))
        self.cursor.execute(self._format_sql(
            index_name, fields, sql_trigger_delete))
        self.cursor.execute(self._format_sql(
            index_name, fields, sql_trigger_update))
        if table_exists:
            if not managed:
                # Index existing data, this will be executed only once
                sql_index_data = f'''INSERT INTO {index_name}_fts (rowid, {fts_fields}) SELECT ROWID, {
                    fts_fields} FROM {index_name}'''
                logger.debug(sql_index_data)
                self.cursor.execute(sql_index_data)
                self.cursor.execute(
                    "insert or ignore into pocket_search_master values (?,?)", (index_name, content))
        else:
            # create standard indices
            self.cursor.execute(
                "insert or ignore into pocket_search_master values (?,?)", (index_name, content))
            for field in default_index_fields:
                self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_std_{index_name}_{field} ON {index_name} ({field});".format(
                    index_name=index_name, field=field.name))
        logger.debug("Commiting transaction")
        self.cursor.execute("commit")

    def tokens(self,top_n=25):
        '''
        Return token statistics on the current index
        '''
        sql = f"""select term as token, doc as num_documents,
        cnt as total_count from {self.index_name}_fts_v order by total_count desc LIMIT {top_n}"""
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        while row is not None:
            yield {"token": row["token"],
                   "num_documents": row["num_documents"],
                   "total_count": row["total_count"]}
            row = self.cursor.fetchone()

    def get_arguments(self, kwargs, for_search=True,normalize=None):
        '''
        Extracts field names and lookups from the keywords arguments and returns
        a dictionary of argument objects.
        '''
        referenced_fields = {}
        id_field = self.schema.get_id_field() or "id"
        for kwarg in kwargs:
            comp = kwarg.split("__")
            if comp[0] not in referenced_fields:
                referenced_fields[comp[0]] = []
            if len(comp) > 1:
                if not for_search:
                    raise self.FieldError(
                        "Lookups are not allowed in the context of inserts and updates")
                referenced_fields[comp[0]].append(
                    self.Lookup(comp[1:], kwargs[kwarg],normalize=normalize))
            else:
                referenced_fields[comp[0]].append(
                    self.Lookup(["eq"], kwargs[kwarg],normalize=normalize))
        for f, lookups in referenced_fields.items():
            if f not in self.schema.fields:
                raise self.FieldError(
                    f"Unknown field '{f}' - it is not defined in the schema.")
            for lookup in lookups:
                for name in lookup.names:
                    if not name in LOOKUPS:
                        raise self.FieldError(f"""Unknown lookup: '{
                                              name}' in field '{f}'""")
        arguments = {}
        for field in self.schema:
            if field.name not in referenced_fields and not (for_search) and field.name not in [id_field, "rank"]:
                raise self.FieldError(
                    f"Missing field '{field.name}' in keyword arguments.")
            if field.name in referenced_fields:
                arguments[field.name] = self.Argument(
                    field, referenced_fields[field.name])
        return arguments

    def build(self, index_reader,verbose=False):
        '''
        Create an index reading a document from an index_builder instance.
        '''
        timer = Timer()
        self.assure_writeable()
        for elem in index_reader.read():
            self.insert_or_update(**elem)
            if verbose:
                timer.snapshot()            

    def insert_or_update(self, **kwargs):
        '''
        Insert or updates a new document if it already exists.
        '''
        self.assure_writeable()
        if self.schema.id_field is None:
            raise self.DatabaseError("""No IDField has been defined in the schema -
                                     cannot perform insert_or_update.""")
        arguments = self.get_arguments(kwargs, for_search=False,normalize=self.normalize)
        joined_fields = ",".join(arguments)
        values = [argument.lookups[0].value for argument in arguments.values()]
        # get rowid:
        unique_id = (kwargs.get(self.schema.id_field),)
        sql = f"select rowid from {self.index_name} where {self.schema.id_field} = ?"
        self.cursor.execute(sql,unique_id)
        row = self.cursor.fetchone()    
        if row is not None:   
            joined_fields = "rowid," + joined_fields
            values = [row["id"]] + values
        placeholder_values = "?" * len(values)
        sql = "replace into %s (%s) values (%s)" % (self.schema.name,
                                                    joined_fields,
                                                    ",".join(placeholder_values))
        try:
            self.cursor.execute(sql, values)
        except Exception as sql_error:
            raise self.DatabaseError(sql_error)

    def commit(self):
        '''
        Commit current changes to database. Commits are only performed 
        when the buffer is full.
        '''
        logger.debug("Committing.")
        self.connection.commit()

    def optimize(self):
        '''
        Runs table optimization that can be run after a huge amount 
        of data has been inserted to the database.
        Technically, this runs a VACUUM ANALYSE command on the 
        database, resulting in potential query speed ups.
        '''
        self.assure_writeable()
        self._close()  # close old connection, so we do not have any conflicts
        connection = self._open()
        connection.cursor().execute("VACUUM")
        connection.close()

    def get(self, rowid):
        '''
        Get a document from the index. rowid is the integer id of the document.
        '''
        sql = "select * from %s  where id=?" % (self.schema.name,)
        fields = self.schema.get_fields()
        logger.debug(sql)
        doc = self.cursor.execute(sql, (rowid,)).fetchone()
        if doc is None:
            raise self.DocumentDoesNotExist()
        document = Document(fields)
        for field in doc.keys():
            setattr(document, field, doc[field])
        return document

    def insert(self, *args, **kwargs):
        '''
        Inserts a new document to the search index.
        '''
        self.assure_writeable()
        if len(args) > 0:
            table_name = args[0]
        else:
            table_name = self.schema.name
        arguments = self.get_arguments(kwargs, for_search=False,normalize=self.normalize)
        joined_fields = ",".join([f for f in arguments])
        values = [argument.lookups[0].value for argument in arguments.values()]
        placeholder_values = "?" * len(values)
        sql = "insert into %s (%s) values (%s)" % (table_name,
                                                   joined_fields,
                                                   ",".join(placeholder_values))
        try:
            logger.debug(sql)
            self.cursor.execute(sql, values)
        except Exception as sql_error:
            raise self.DatabaseError(sql_error)

    def update(self, **kwargs):
        '''
        Updates a document. A rowid keyword argument must be provided. If the
        the rowid is not found, no update is done and no error is thrown.
        '''
        self.assure_writeable()
        id_field = self.schema.get_id_field() or "id"
        docid = kwargs.pop("rowid")
        arguments = self.get_arguments(kwargs, for_search=False,normalize=self.normalize)
        values = [argument.lookups[0].value for argument in arguments.values()] + \
            [docid]
        stmt = []
        for f in arguments:
            stmt.append("%s=?" % f)
        sql = "update %s set %s where %s=?" % (
            self.schema.name, ",".join(stmt), id_field)
        logger.debug(sql)
        self.cursor.execute(sql, values)
        # self.commit()

    def delete(self, rowid):
        '''
        Deletes a document. A rowid keyword argument must be provided. If the
        the rowid is not found, no deletion is done and no error is thrown.
        '''
        self.assure_writeable()
        id_field = self.schema.get_id_field() or "id"
        sql = "delete from %s where %s = ?" % (self.schema.name, id_field)
        logger.debug(sql)
        self.cursor.execute(sql, (rowid,))
        # self.commit()

    def delete_all(self):
        '''
        Delete entire index in database
        '''
        self.assure_writeable()
        sql = "delete from %s" % self.schema.name
        logger.debug(sql)
        self.cursor.execute(sql)
        # self.commit()

    def autocomplete(self, *args, **kwargs):
        '''
        Constructs a query against a given field that performs auto-complete
        (thus, predicting what the rest of a word is a user types in).
        '''
        if len(args) > 0:
            raise Query.QueryError(""".autocomplete expects exactly one keyword argument
            naming the field in the schema you want to search.""")
        if len(kwargs) > 1:
            raise Query.QueryError(
                "Only one field can be searched through autocomplete.")
        if len(kwargs) == 0:
            # return all results
            return Query(search_instance=self, arguments=[], q_arguments=[])
        query = list(kwargs.values())[0]
        if "__" in list(kwargs.keys())[0]:
            raise Query.QueryError(
                "Lookups are not allowed in autocomplete queries.")
        field = list(kwargs.keys())[0]
        query_components = query.split(" ")
        # quote, if necessary
        for idx, component in enumerate(query_components):
            for operator in FTS_OPERATORS+["*", "AND", "OR", "NEAR"]:
                if operator in component:
                    query_components[idx] = '"%s"' % query_components[idx]
        if len(query_components) > 1:
            prefix = ""
        else:
            prefix = "*"
        query_components[0] = "(^{first_word}{prefix} OR {first_word}{prefix})".format(first_word=query_components[0],
                                                                                       prefix=prefix)
        if len(query_components) > 1:
            query_components[len(query_components) -
                             1] = query_components[-1:][0]+"*"
        query = " AND ".join(query_components)
        return self.search(**{f"{field}__allow_boolean__allow_prefix__allow_initial_token" : query})

    def suggest(self, query):
        '''
        Return a list of spelling suggestions for the tokens given in 
        query.
        '''
        if self.schema._meta.spell_check:
            return self.spell_checker().suggest(query)
        raise Query.QueryError("Spell checks are not supported in this index.")

    def _clear_kwargs(self, kwargs):
        cleared_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, str):
                if len(v) > 0:
                    cleared_kwargs[k] = v
                else:
                    cleared_kwargs[k] = '""'
            else:
                if v is not None:
                    cleared_kwargs[k] = v
                else:
                    cleared_kwargs[k] = '""'
        return cleared_kwargs

    def search(self, *args, **kwargs):
        '''
        Initiate search in index
        '''
        if len(args) > 0 and len(kwargs) > 0:
            raise Query.QueryError(
                "Cannot mix Q objects and keyword arguments.")
        # check for empty kwargs
        cleared_kwargs = self._clear_kwargs(kwargs)
        if len(args) > 0:
            for q_expr in args[0]:
                q_expr.arguments = self.get_arguments(
                    self._clear_kwargs(q_expr.kwargs),normalize=self.normalize)
            return Query(search_instance=self, arguments=[], q_arguments=args[0])
        arguments = self.get_arguments(cleared_kwargs,normalize=self.normalize)
        return Query(search_instance=self, arguments=arguments, q_arguments=[])


class IndexReader(abc.ABC):
    '''
    An abstract base class for index readers. Reader classes
    scan through a source (e.g. the file system or some web site)
    and retrieve documents that should be indexed.
    '''

    def read(self):
        '''
        Subclasses need to implement this method.
        It should return a list of dictionaries
        where each dictionary entry represents
        a document in the schema.
        '''
        raise NotImplementedError()


class FileSystemReader(IndexReader):
    '''
    Index files and their contents from a directory.
    The FileSystemReader expects a schema containing
    following fields:

    - filename (TEXT, unique=True)
    - text (TEXT, index=True)

    '''

    encoding = "utf-8"

    class FSSchema(Schema):
        '''
        Schema used by the index reader
        '''

        class Meta:
            '''
            FS Schema meta options
            '''
            spell_check = True

        filename = Text(is_id_field=True)
        text = Text(index=True)

    def __init__(self, base_dir="./", file_extensions=None):
        self.timer = Timer()
        if file_extensions is None:
            self.file_extensions = [".txt"]
        else:
            self.file_extensions = file_extensions
        self.base_dir = base_dir

    def file_to_dict(self, file_path, file):
        '''
        Open the file and transform it to a dictionary.
        '''
        return {"filename": file_path, "text": file.read()}

    def read(self):
        '''
        Traverse directory and yield files found matching 
        the given extensions. This expects
        '''
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                for extension in self.file_extensions:
                    if file.endswith(extension):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding=self.encoding) as file:
                            yield self.file_to_dict(file_path, file)


class ConnectionPool:
    '''
    Managing a connection pool for pocket search instances and 
    assuring that only one thread writes to a pocket search instance 
    at a given time.
    '''

    POOL_MAX_DATABASES = 150
    POOL_CONNECTION_TIMEOUT = 5

    class ConnectionError(Exception):
        '''
        Raised, if no connection could be acquired
        '''

    def __init__(self):
        self.connections = {}
        self.dict_lock = threading.Semaphore(10)

    def _open(self, db_name):
        if db_name is None:
            logger.debug("Opening connection to in-memory db")
            connection = sqlite3.connect(":memory:",
                                         detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        else:
            logger.debug("Opening connection to db %s", db_name)
            connection = sqlite3.connect(
                db_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        connection.row_factory = sqlite3.Row
        return connection

    def get_connection(self, db_name, writeable, conn_id=None):
        '''
        Acquire a new connection and raise an exception if none is available
        '''
        if db_name is not None:
            conn_id = db_name
        if writeable:
            logger.debug("Acquiring dict lock.")
            with self.dict_lock:
                if not conn_id in self.connections:
                    if len(self.connections) > self.POOL_MAX_DATABASES:
                        raise self.ConnectionError(
                            "Too many databases in connection pool.")
                    logger.debug(f"Setting up pool for {conn_id}")
                    self.connections[conn_id] = {
                        "writer": threading.Semaphore(1)}
            logger.debug("Acquiring writer.")
            if not self.connections[conn_id]["writer"].acquire(timeout=self.POOL_CONNECTION_TIMEOUT):
                raise self.ConnectionError(
                    f"Unable to acquire pocketsearch writer (Timed out) for {conn_id}")
        return self._open(db_name)

    def release_connection(self, db_name, connection, writeable, conn_id=None):
        '''
        Release the given connection
        '''
        if db_name is not None:
            conn_id = db_name
        if not self._is_valid_connection(connection):
            connection.close()
        if writeable:
            logger.debug("Writer released")
            self.connections[conn_id]["writer"].release()

    def _is_valid_connection(self, connection):
        try:
            connection.execute("SELECT 1;")
            return True
        except sqlite3.OperationalError:
            return False


connection_pool = ConnectionPool()
