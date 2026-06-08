"""
Low-level SQL query components for PocketSearch.

Each ``SQLQueryComponent`` subclass renders one part of a SELECT statement
(WHERE, ORDER BY, JOIN, and so on). Lookup constants (``LU_*``, ``LOOKUPS``)
define which field lookups are valid for each field type.
"""

import abc

from .fields import Date, Datetime, Int, Text


class SQLQueryComponent(abc.ABC):
    """
    Used by the SQLQuery class. Each component represents a part of
    the overall SQL statment, e.g. the values selected or the order by
    clause.
    """

    def __init__(self, sql_query):
        self.sql_query = sql_query

    def to_sql(self):
        """
        Subclasses must return a string containing valid SQL.
        """
        raise NotImplementedError()


class Function:
    """
    SQL function applied to fields in the select part
    of the query
    """


class Highlight(Function):
    """
    Highlight SQL function
    """

    def __init__(self, marker_start, marker_end):
        self.marker_start = marker_start
        self.marker_end = marker_end

    def to_sql(self, field):
        return "highlight({table}_fts, {index}, '{m_start}', '{m_end}') as {field}".format(
            field=field.name,
            table=field.schema.name,
            index=field.schema.field_index[field.name],
            m_start=self.marker_start,
            m_end=self.marker_end,
        )


class Snippet(Function):
    """
    Snippet SQL function
    """

    def __init__(self, text_before, text_after, snippet_length=16):
        self.text_before = text_before
        self.text_after = text_after
        self.snippet_length = snippet_length

    def to_sql(self, field):
        return (
            "snippet({table}_fts, {index}, '{t_before}', "
            "'{t_after}','...',{l}) as {field}"
        ).format(
            field=field.name,
            table=field.schema.name,
            index=field.schema.field_index[field.name],
            t_before=self.text_before,
            l=self.snippet_length,
            t_after=self.text_after,
        )


class Select(SQLQueryComponent):
    """
    A single field selected in the query.
    """

    def __init__(self, field, sql_query, function=None):
        super().__init__(sql_query)
        self.field = field
        self.function = function

    def to_sql(self):
        if isinstance(self.field, str):
            return self.field
        if isinstance(self.field, Date):
            return '{full_name} as "{name} [date]"'.format(
                full_name=self.field.get_full_qualified_name(),
                name=self.field.name,
            )
        elif isinstance(self.field, Datetime):
            return '{full_name} as "{name} [timestamp]"'.format(
                full_name=self.field.get_full_qualified_name(),
                name=self.field.name,
            )
        if self.function is None:
            return self.field.get_full_qualified_name()
        return self.function.to_sql(self.field)


class Count(SQLQueryComponent):
    """
    Count statement in the select part
    """

    def to_sql(self):
        return "COUNT(*)"


class Table(SQLQueryComponent):
    """
    Table referenced in the FROM clause
    """

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


class Filter(SQLQueryComponent):
    """
    Abstract base class for fields referenced in
    the WHERE part of the SQL statement
    """

    def __init__(self, field, value, sql_query, lookup):
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
    """
    Full text match filter in where clause
    """

    def _escape(self, value):
        tokens_1 = (
            self.sql_query.search_instance.schema._meta.tokenizer.tokenize(
                value, keep=self.operators
            )
        )
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
    """
    Referenced field in WHERE clause that
    is not part of the FTS5 index.
    """

    def __init__(self, field, value, sql_query, lookup):
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
    """
    Referenced field in WHERE clause filtering
    dates.
    """

    def __init__(self, field, value, sql_query, lookup):
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
        return "CAST(strftime('%s',%s) AS INTEGER) %s ?" % (
            self.date_selector,
            self.field.get_full_qualified_name(),
            self.op,
        )


class OrderBy(SQLQueryComponent):
    """
    Referenced field in order by clause.
    """

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
    """
    LIMIT and OFFSET in SQL query
    """

    def __init__(self, limit, offset, sql_query):
        super().__init__(sql_query)
        self.limit = limit
        self.offset = offset

    def to_sql(self):
        # self.sql_query.add_value(self.limit)
        # self.sql_query.add_value(self.offset)
        return "LIMIT %s OFFSET %s" % (self.limit, self.offset)


class Join(SQLQueryComponent):
    """
    Join on tables in SQL query
    """

    def __init__(
        self, table_left, table_right, left_field, right_field, sql_query
    ):
        super().__init__(sql_query)
        self.table_left = table_left
        self.table_right = table_right
        self.left_field = left_field
        self.right_field = right_field

    def to_sql(self):
        return "{table_left}.{left_field}={table_right}.{right_field}".format(
            table_left=self.table_left.to_sql(),
            table_right=self.table_right.to_sql(),
            left_field=self.left_field,
            right_field=self.right_field,
        )


class And(SQLQueryComponent):
    """
    AND keyword in sql query
    """

    def to_sql(self):
        return "AND"


class Or(SQLQueryComponent):
    """
    OR keyword in sql query
    """

    def to_sql(self):
        return "OR"
