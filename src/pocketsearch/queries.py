import copy
import logging

from .fields import Date
from .sql_query_components import (
    And,
    BooleanFilter,
    Count,
    DateFilter,
    Highlight,
    Join,
    LimitAndOffset,
    MatchFilter,
    Or,
    OrderBy,
    Select,
    Snippet,
    Table,
)

logger = logging.getLogger(__name__)


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
