'''
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE FOR ANY DAMAGES OR OTHER LIABILITY,
WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import threading
import datetime
import sqlite3
import collections
import unicodedata
import os
import time
import abc
import copy
import uuid
import logging

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


class Tokenizer(abc.ABC):
    '''
    Base class for tokenizers
    '''

    class TokenizerError(Exception):
        '''
        Thrown if the initialization of the tokenizer fails
        '''

    def __init__(self, name):
        self.name = name
        self.properties = {}

    def add_property(self, name, value):
        '''
        Add a property to the tokenizer
        '''
        if value is not None:
            self.properties[name] = self.Property(name, value)

    class Property:
        '''
        Property associated with tokenizer
        '''

        def __init__(self, name, value):
            self.name = name
            self.value = value

    def to_sql(self):
        properties = " ".join(["%s '%s'" % (p.name, p.value)
                              for p in self.properties.values()])
        return "tokenize=\"{name} {properties}\"".format(name=self.name, properties=properties)


class Unicode61(Tokenizer):
    '''
    Unicode61 tokenizer (see https://www.sqlite.org/fts5.html for more details)
    '''

    VALID_DIACRITICS = ["0", "1", "2"]

    def __init__(self, remove_diacritics="2", categories=None, tokenchars=None, separators=""):
        super().__init__("unicode61")
        if remove_diacritics not in self.VALID_DIACRITICS and remove_diacritics is not None:
            raise self.TokenizerError(
                "Invalid valid for remove_diacritics. Valid options are %s" % self.VALID_DIACRITICS)
        self.add_property("remove_diacritics", remove_diacritics)
        if categories is None:
            categories = "L* N* Co"
        self.add_property("categories", categories)
        self.add_property("tokenchars", tokenchars)
        self.add_property("separators", separators)

    def is_tokenchar(self, character):
        '''
        Test if the given character is a token character (True) or 
        separator (False)
        '''
        categories = self.properties.get("categories").value.split()
        if "tokenchars" in self.properties:
            tokenchars = self.properties["tokenchars"].value.split()
        else:
            tokenchars = []
        additional_separators = self.properties.get("separators")
        if additional_separators is not None:
            if character in additional_separators.value:
                return False
        if character in tokenchars:
            return True
        ch_category = unicodedata.category(character)
        return ch_category in categories or ch_category[0]+"*" in categories

    def tokenize(self, input_str, keep=[]):
        '''
        Based on the settings of unicode61 tokenizer given, split the 
        input_str into individual tokens and return them as a list of 
        tokens.
        You can provide additional characters to be considered as tokens 
        in the keep arguments. 
        When quote is set to True, tokens containing punctuation will be 
        automatically quoted.
        '''
        output_str = ""
        for character in input_str:
            if character in keep:
                output_str += character
                continue
            if self.is_tokenchar(character):
                output_str += character
            else:
                output_str += " "
        return [ch for ch in output_str.split(" ") if len(ch) > 0]


class Field(abc.ABC):
    '''
    Each schema has a number of fields. The field class defines the behavior of a field
    '''

    hidden = False
    data_type = None  # must be set by sub classes

    def __init__(self, name=None, schema=None, default=None, index=False, is_id_field=False):
        self.schema = schema
        self.name = name
        self.default = default
        self.index = index
        self.is_id_field = is_id_field

    def constraints(self):
        '''
        Returns any constraints as string associated with the field.
        '''
        if self.is_id_field:
            return " UNIQUE "
        return ""

    def fts_enabled(self):
        '''
        Returns, if the field is available for full-text-search.
        '''
        return False

    def get_full_qualified_name(self):
        '''
        Return the full qualified name including its table for the given field.
        '''
        return "%s.%s" % (self.schema.name, self.name)

    def to_sql(self, index_table=False):
        '''
        Returns sql representation of field for SQL table generation.
        '''
        if self.data_type is None:
            raise self.schema.SchemaError("class %s (field=%s) has no data_type set" % (
                self.__class__.__name__, self.name))
        name = self.schema.reverse_lookup[self]
        if index_table:
            _data_type = ""
        else:
            _data_type = self.data_type
        return "%s %s %s" % (name, _data_type, self.constraints())


class Int(Field):
    '''
    Integer field
    '''

    data_type = "INTEGER"


class Rank(Field):
    '''
    Rank field as returned by FTS5 - it is a hidden field, meaning
    that during index creation it won't be created as actual database
    field.
    '''

    hidden = True
    data_type = "REAL"

    def get_full_qualified_name(self):
        return self.name


class IdField(Int):
    '''
    Creates a primary key (using autoincrement) integer field in the SQLITE database.
    '''

    def constraints(self):
        return "PRIMARY KEY AUTOINCREMENT"


class Text(Field):
    '''
    Translates to sqlite3 TEXT field.
    '''

    data_type = "TEXT"

    def fts_enabled(self):
        return self.index


class Real(Field):
    '''
    Translates to sqlite3 REAL field.
    '''

    data_type = "REAL"


class Numeric(Field):
    '''
    Translates to sqlite3 NUMERIC field.
    '''

    data_type = "NUMERIC"


class Blob(Field):

    '''
    Translates to sqlite3 BLOB field.
    '''
    data_type = "BLOB"


class Date(Field):
    '''
    Translates to sqlite3 DATE field.
    '''

    data_type = "Date"


class Datetime(Field):
    '''
    Translates to sqlite3 Datetime field.
    '''
    data_type = "Datetime"


class Schema:
    '''
    A schema defines what fields can be searched in the search index.
    '''

    # id = IdField()
    rank = Rank()

    class Meta:
        tokenizer = Unicode61()
        spell_check = False
        prefix_index = None

    RESERVED_KEYWORDS = [
        'ABORT', 'ACTION', 'ADD', 'AFTER', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC', 'ATTACH', 'AUTOINCREMENT',
        'BEFORE', 'BEGIN', 'BETWEEN', 'BY', 'CASCADE', 'CASE', 'CAST', 'CHECK', 'COLLATE', 'COLUMN', 'COMMIT',
        'CONFLICT', 'CONSTRAINT', 'CREATE', 'CROSS', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'DATABASE',
        'DEFAULT', 'DEFERRABLE', 'DEFERRED', 'DELETE', 'DESC', 'DETACH', 'DISTINCT', 'DROP', 'EACH', 'ELSE', 'END',
        'CONTENT', 'ESCAPE', 'EXCEPT', 'EXCLUSIVE', 'EXISTS', 'EXPLAIN', 'FAIL', 'FOR', 'FOREIGN', 'FROM', 'FULL', 'GLOB',
        'GROUP', 'HAVING', 'IF', 'IGNORE', 'IMMEDIATE', 'IN', 'INDEX', 'INDEXED', 'INITIALLY', 'INNER', 'INSERT',
        'INSTEAD', 'INTERSECT', 'INTO', 'IS', 'ISNULL', 'JOIN', 'KEY', 'LEFT', 'LIKE', 'LIMIT', 'MATCH', 'NATURAL',
        'NO', 'NOT', 'NOTNULL', 'NULL', 'OF', 'OFFSET', 'ON', 'OR', 'ORDER', 'OUTER', 'PLAN', 'PRAGMA', 'PRIMARY',
        'QUERY', 'RAISE', 'RECURSIVE', 'REFERENCES', 'REGEXP', 'REINDEX', 'RELEASE', 'RENAME', 'REPLACE', 'RESTRICT',
        'RIGHT', 'ROLLBACK', 'ROW', 'SAVEPOINT', 'SELECT', 'SET', 'TABLE', 'TEMP', 'TEMPORARY', 'THEN', 'TO',
        'TRANSACTION', 'TRIGGER', 'UNION', 'UNIQUE', 'UPDATE', 'USING', 'VACUUM', 'VALUES', 'VIEW', 'VIRTUAL', 'WHEN',
        'WHERE', 'WITH', 'WITHOUT', 'NAME', 'FIELDS', 'FIELDS_INDEX', 'FIELDS_WITH_DEFAULT',
        'REVERSE_LOOKUP', 'ID_FIELD'
    ]

    class SchemaError(Exception):
        '''
        Thrown, if the schema cannot be generated.
        '''

    def _set_meta_defaults(self):
        try:
            self._meta.prefix_index
        except AttributeError:
            self._meta.prefix_index = None
        try:
            self._meta.tokenizer
        except AttributeError:
            # FIXME: might have undesired
            # side effects / using another
            # exception here?
            self._meta.tokenizer = Unicode61()
        try:
            self._meta.spell_check
        except AttributeError:
            self._meta.spell_check = False

    def __init__(self, name):
        self._meta = self.Meta()
        self._set_meta_defaults()
        self.name = name
        self.fields = collections.OrderedDict()
        self.field_index = {}  # required by some SQL functions, e.g. highlight
        self.fields_with_default = {}
        self.reverse_lookup = {}
        self.id_field = None
        field_index = 0
        for elem in dir(self):
            # Create and store a (shallow) copy of the class variable
            # in order to avoid any side effects. All schema classes
            # share the IDField and the RankField and both have
            # instance variable. If we would not have a copy of these
            # class-wide objects we run into scenarios (e.g. changing index)
            # that would affect all schemas an application uses
            obj = copy.copy(getattr(self, elem))
            if isinstance(obj, Field):
                if obj.data_type is None:
                    raise self.SchemaError("class %s (field=%s) has no data_type set" % (
                        obj.__class__.__name__, elem))
                if elem.startswith("_") or "__" in elem:
                    raise self.SchemaError(
                        "Cannot use '%s' as field name. Field name may not start with an underscore and may not contain double underscores." %
                        elem)
                if elem.upper() in self.RESERVED_KEYWORDS:
                    raise self.SchemaError(
                        "'%s' is a reserved name - Please choose another name." % elem)
                self.fields[elem] = obj
                self.fields[elem].schema = self
                self.fields[elem].name = elem
                self.reverse_lookup[obj] = elem
                if obj.is_id_field:
                    if self.id_field is not None:
                        raise self.SchemaError(
                            "You can only provide one IDField per schema. The current IDField is: %s" % self.id_field)
                    self.id_field = obj.name
                if obj.fts_enabled():
                    self.field_index[obj.name] = field_index
                    field_index += 1
        if not self.get_id_field():
            obj = IdField()
            obj.name = "id"
            self.fields["id"] = obj
            self.fields["id"].schema = self
            self.reverse_lookup[obj] = "id"

        for field in self:
            if field.default is not None:
                self.fields_with_default[field.name] = field

    def get_id_field(self):
        '''
        Returns True if the current schema has explicitly 
        defined an IdField
        '''
        for elem in dir(self):
            obj = getattr(self, elem)
            if isinstance(obj, IdField):
                return elem
        return None

    def get_field(self, field_name, raise_exception=False):
        '''
        Returns field object for the given field name. If raise_exception is set to True,
        an exception is raised if the field is not defined in the index.
        '''
        if raise_exception:
            if not field_name in self.fields:
                raise self.SchemaError("'%s' is not defined in this schema '%s'" % (
                    field_name, self.__class__.__name__))
        return self.fields.get(field_name)

    def get_fields(self):
        '''
        Returns all field objects defined in the schema.
        '''
        return list(self.fields.values())

    def __iter__(self):
        return iter(self.fields.values())


class DefaultSchema(Schema):
    '''
    Default schema, if none is explicitly provided in the PocketSearch constructor.
    '''

    text = Text(index=True)


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


class SQLQueryComponent(abc.ABC):
    '''
    Used by the SQLQuery class. Each component represents a part of
    the overall SQL statment, e.g. the values selected or the order by
    clause.
    '''

    def __init__(self, sql_query):
        self.sql_query = sql_query

    def to_sql(self):
        '''
        This class must be implemented by any class subclassing SQLQueryComponent.
        It should return a string containing valid SQL.
        '''
        raise NotImplementedError()


class Function:
    '''
    SQL function applied to fields in the select part 
    of the query
    '''


class Highlight(Function):
    '''
    Highlight SQL function
    '''

    def __init__(self, marker_start, marker_end):
        self.marker_start = marker_start
        self.marker_end = marker_end

    def to_sql(self, field):
        return "highlight({table}_fts, {index}, '{m_start}', '{m_end}') as {field}".format(field=field.name,
                                                                                           table=field.schema.name,
                                                                                           index=field.schema.field_index[
                                                                                               field.name],
                                                                                           m_start=self.marker_start,
                                                                                           m_end=self.marker_end)


class Snippet(Function):
    '''
    Snippet SQL function
    '''

    def __init__(self, text_before, text_after, snippet_length=16):
        self.text_before = text_before
        self.text_after = text_after
        self.snippet_length = snippet_length

    def to_sql(self, field):
        return "snippet({table}_fts, {index}, '{t_before}', '{t_after}','...',{l}) as {field}".format(field=field.name,
                                                                                                      table=field.schema.name,
                                                                                                      index=field.schema.field_index[
                                                                                                          field.name],
                                                                                                      t_before=self.text_before,
                                                                                                      l=self.snippet_length,
                                                                                                      t_after=self.text_after)


class Select(SQLQueryComponent):
    '''
    A single field selected in the query.
    '''

    def __init__(self, field, sql_query, function=None):
        super().__init__(sql_query)
        self.field = field
        self.function = function

    def to_sql(self):
        if isinstance(self.field,str):
            return self.field
        if isinstance(self.field, Date):
            return "{full_name} as \"{name} [date]\"".format(full_name=self.field.get_full_qualified_name(), name=self.field.name)
        elif isinstance(self.field, Datetime):
            return "{full_name} as \"{name} [timestamp]\"".format(full_name=self.field.get_full_qualified_name(), name=self.field.name)
        if self.function is None:
            return self.field.get_full_qualified_name()
        return self.function.to_sql(self.field)


class Count(SQLQueryComponent):
    '''
    Count statement in the select part
    '''

    def to_sql(self):
        return "COUNT(*)"


class Table(SQLQueryComponent):
    '''
    Table referenced in the FROM clause
    '''

    def __init__(self, table_name, sql_query):
        super().__init__(sql_query)
        self.table_name = table_name

    def to_sql(self):
        return self.table_name


LU_EQ = "eq"
LU_BOOL = "allow_boolean"
LU_NEG = "allow_negation"
LU_PREFIX = "allow_prefix"
LU_INITIAL_TOKEN = "allow_initial_token"
LU_GTE = "gte"
LU_LTE = "lte"
LU_GT = "gt"
LU_LT = "lt"
LU_YEAR = "year"
LU_MONTH = "month"
LU_DAY = "day"
LU_HOUR = "hour"
LU_MINUTE = "minute"

LOOKUPS = {
    LU_EQ: [],  # valid for all field types
    LU_BOOL: [Text],
    LU_NEG: [Text],
    LU_PREFIX: [Text],
    LU_INITIAL_TOKEN: [Text],
    LU_GTE: [Int],
    LU_LTE: [Int],
    LU_GT: [Int],
    LU_LT: [Int],
    LU_YEAR: [Date, Datetime],
    LU_MONTH: [Date, Datetime],
    LU_DAY: [Date, Datetime],
    LU_HOUR: [Datetime],
    LU_MINUTE: [Datetime],

}

FTS_OPERATORS = ["-", ".", "#", "NEAR", "@"]


class Filter(SQLQueryComponent):
    '''
    Abstract base class for fields referenced in
    the WHERE part of the SQL statement
    '''

    def __init__(self, field,
                 value,
                 sql_query,
                 lookup):
        super().__init__(sql_query)
        self.field = field
        self.value = value
        self.keywords = []
        self.operators = ['"']
        if LU_PREFIX in lookup.names:
            self.operators.append("*")
        if LU_INITIAL_TOKEN in lookup.names:
            self.operators.append("^")
        if LU_BOOL in lookup.names:
            self.keywords = self.keywords + ["AND", "OR"]
            self.operators.append("(")
            self.operators.append(")")
        if LU_NEG in lookup.names:
            self.keywords.append("NOT")


class MatchFilter(Filter):
    '''
    Full text match filter in where clause
    '''

    def _escape(self, value):
        tokens_1 = self.sql_query.search_instance.schema._meta.tokenizer.tokenize(value,
                                                                                  keep=self.operators)
        tokens = []
        multiple_token_quote = False
        for token in tokens_1:
            quote = True
            if token.startswith('"'):
                multiple_token_quote = True
            if token.endswith('"'):
                multiple_token_quote = False
            if token in self.keywords:
                quote = False
            for operator in self.operators:
                if operator in token:
                    quote = False
            if quote and not multiple_token_quote:
                tokens.append(f'"{token}"')
            else:
                tokens.append(token)
        if len(tokens) == 0:
            return '""'
        return " ".join(tokens)

    def to_sql(self):
        v = "%s:%s" % (self.field.name, self._escape(self.value))
        return v


class BooleanFilter(SQLQueryComponent):
    '''
    Referenced field in WHERE clause that
    is not part of the FTS5 index.
    '''

    def __init__(self, field,
                 value,
                 sql_query,
                 lookup):
        super().__init__(sql_query)
        if LU_GTE in lookup.names:
            self.op = ">="
        elif LU_GT in lookup.names:
            self.op = ">"
        elif LU_LTE in lookup.names:
            self.op = "<="
        elif LU_LT in lookup.names:
            self.op = "<"
        else:
            self.op = "="
        self.field = field
        self.value = value

    def to_sql(self):
        self.sql_query.add_value(self.value)
        return "%s %s ?" % (self.field.get_full_qualified_name(), self.op)


class DateFilter(BooleanFilter):
    '''
    Referenced field in WHERE clause filtering
    dates.
    '''

    def __init__(self, field,
                 value,
                 sql_query,
                 lookup):
        super().__init__(field, value, sql_query, lookup)
        if LU_YEAR in lookup.names:
            self.date_selector = "%Y"
        elif LU_MONTH in lookup.names:
            self.date_selector = "%m"
        elif LU_DAY in lookup.names:
            self.date_selector = "%d"
        else:
            self.date_selector = None

    def to_sql(self):
        if self.date_selector is None:
            return super().to_sql()
        self.sql_query.add_value("%s" % self.value)
        return "CAST(strftime('%s',%s) AS INTEGER) %s ?" % (self.date_selector,
                                                            self.field.get_full_qualified_name(),
                                                            self.op)


class OrderBy(SQLQueryComponent):
    '''
    Referenced field in order by clause.
    '''

    def __init__(self, field, sql_query, sort_dir=None):
        super().__init__(sql_query)
        self.field = field
        self.sort_dir = sort_dir

    def to_sql(self):
        if isinstance(self.field, str):
            if self.field.startswith("+"):
                d = "ASC"
            elif self.field.startswith("-"):
                d = "DESC"
            else:
                d = "ASC"
            # self.sql_query.add_value(self.field[1:])
            return "%s %s" % (self.field[1:], d)
        if self.sort_dir == "+":
            d = "ASC"
        elif self.sort_dir == "-":
            d = "DESC"
        else:
            d = "ASC"
        # self.sql_query.add_value(self.field.get_full_qualified_name())
        return "%s %s" % (self.field.get_full_qualified_name(), d)


class LimitAndOffset(SQLQueryComponent):
    '''
    LIMIT and OFFSET in SQL query
    '''

    def __init__(self, limit, offset, sql_query):
        super().__init__(sql_query)
        self.limit = limit
        self.offset = offset

    def to_sql(self):
        # self.sql_query.add_value(self.limit)
        # self.sql_query.add_value(self.offset)
        return "LIMIT %s OFFSET %s" % (self.limit, self.offset)


class Join(SQLQueryComponent):
    '''
    Join on tables in SQL query
    '''

    def __init__(self, table_left,
                 table_right,
                 left_field,
                 right_field,
                 sql_query):
        super().__init__(sql_query)
        self.table_left = table_left
        self.table_right = table_right
        self.left_field = left_field
        self.right_field = right_field

    def to_sql(self):
        return "{table_left}.{left_field}={table_right}.{right_field}".format(table_left=self.table_left.to_sql(),
                                                                              table_right=self.table_right.to_sql(),
                                                                              left_field=self.left_field,
                                                                              right_field=self.right_field)


class And(SQLQueryComponent):
    '''
    AND keyword in sql query
    '''

    def to_sql(self):
        return "AND"


class Or(SQLQueryComponent):
    '''
    OR keyword in sql query
    '''

    def to_sql(self):
        return "OR"


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
                 schema=DefaultSchema):
        self.pocketsearch = PocketSearch(
            index_name=index_name, db_name=db_name, schema=schema)

    def __enter__(self, *args, **kwargs):
        return self.pocketsearch

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.pocketsearch.close()


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
                 schema=DefaultSchema):
        self.pocketsearch = PocketSearch(
            index_name=index_name,
            db_name=db_name,
            schema=schema,
            writeable=True
        )
        self.pocketsearch.execute_sql("begin")

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            if self.pocketsearch.schema._meta.spell_check:
                logger.debug("Building spell checking dictionary")
                # self.pocketsearch._get_or_create_spellchecker_instance().build()
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

        def __init__(self, names, value):
            self.names = names
            self.value = value

    def __init__(self, db_name=None,
                 index_name="documents",
                 schema=DefaultSchema,
                 writeable=False,
                 connection=None):
        self.db_name = db_name
        self.schema = schema(index_name)
        self.db_name = db_name
        self.db_id = uuid.uuid4()
        self.connection = None
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

    def tokens(self):
        '''
        Return token statistics on the current index
        '''
        sql = f"""select term as token, doc as num_documents,
        cnt as total_count from {self.index_name}_fts_v order by total_count desc"""
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        while row is not None:
            yield {"token": row["token"],
                   "num_documents": row["num_documents"],
                   "total_count": row["total_count"]}
            row = self.cursor.fetchone()

    def get_arguments(self, kwargs, for_search=True):
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
                    self.Lookup(comp[1:], kwargs[kwarg]))
            else:
                referenced_fields[comp[0]].append(
                    self.Lookup(["eq"], kwargs[kwarg]))
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

    def build(self, index_reader):
        '''
        Create an index reading a document from an index_builder instance.
        '''
        self.assure_writeable()
        for elem in index_reader.read():
            self.insert_or_update(**elem)

    def insert_or_update(self, **kwargs):
        '''
        Insert or updates a new document if it already exists.
        '''
        self.assure_writeable()
        if self.schema.id_field is None:
            raise self.DatabaseError("""No IDFIeld has been defined in the schema -
                                     cannot perform insert_or_update.""")
        arguments = self.get_arguments(kwargs, for_search=False)
        joined_fields = ",".join(arguments)
        values = [argument.lookups[0].value for argument in arguments.values()]
        placeholder_values = "?" * len(values)
        sql = "insert or replace into %s (%s) values (%s)" % (self.schema.name,
                                                              joined_fields,
                                                              ",".join(placeholder_values))
        try:
            self.cursor.execute(sql, values)
        except Exception as sql_error:
            raise self.DatabaseError(sql_error)
        # self.connection.commit()

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
        arguments = self.get_arguments(kwargs, for_search=False)
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
        # self.commit()

    def update(self, **kwargs):
        '''
        Updates a document. A rowid keyword argument must be provided. If the
        the rowid is not found, no update is done and no error is thrown.
        '''
        self.assure_writeable()
        id_field = self.schema.get_id_field() or "id"
        docid = kwargs.pop("rowid")
        arguments = self.get_arguments(kwargs, for_search=False)
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
                    self._clear_kwargs(q_expr.kwargs))
            return Query(search_instance=self, arguments=[], q_arguments=args[0])
        arguments = self.get_arguments(cleared_kwargs)
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
