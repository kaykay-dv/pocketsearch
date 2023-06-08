'''
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE 
COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE FOR ANY DAMAGES OR OTHER LIABILITY, 
WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR 
THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sqlite3
import os
import time
import enum

class Timer:
    '''
    A helper class that displays 
    a progress bar in console.
    '''

    def __init__(self,precision=5):
        self.start=time.time()
        self.precision = precision
        self.total_time = 0
        self.laps = []
        self.snapshots = 0 

    def lap(self,name):
        if len(self.laps) > 0:
            self.total_time+=time.time()-self.laps[-1:][0][1]        
        self.laps.append((name,time.time()))

    def snapshot(self,more_info=""):
        stop = time.time()
        self.snapshots=self.snapshots+1
        its = round(1/((stop-self.start)/self.snapshots),self.precision)
        out = "%s iterations %s it/s %s s elapsed %s%s" % (self.snapshots,its,round(stop-self.start,self.precision),more_info," "*15)
        print(out,end="\r",flush=True)

    def done(self):
        print()

    def __str__(self):
        s="----\n"
        longest_string, lap_time = max(self.laps, key=lambda x: len(x[0]))
        for lap_name , lap_time in self.laps:
            lap_name_display = lap_name + (len(longest_string)-len(lap_name)) * " "
            s=s+"%s %s s\n" % (lap_name_display , round(lap_time,self.precision))
        s=s+"Total time: %s\n" % self.total_time
        s=s+"----\n"
        return s  


class Field: 

    hidden = False

    def __init__(self,name=None,schema=None,default=None,index=False):
        self.schema = schema
        self.name = name
        self.default = default
        self.index=index

    def constraints(self):
        return ""

    def fts_enabled(self):
        return False

    def get_full_qualified_name(self):
        if self.index:
            return "%s_fts.%s" % (self.schema.name,self.name)
        else:
            return "%s.%s" % (self.schema.name,self.name)

    def to_sql(self,index_table=False):
        try:
            self.data_type
        except AttributeError:
            raise AttributeError("class %s (field=%s) has not attribute data_type" % (self.__class__.__name__,self.name))
        name = self.schema.reverse_lookup[self]
        if index_table:
            _data_type=""
        else:
            _data_type=self.data_type
        return "%s %s %s" % (name,_data_type,self.constraints())

    #def __repr__(self):
    #    return "<%:%s>" % (self.name,self.self.__class__.__name__)

class Int(Field):

    data_type = "INTEGER"

class Rank(Field): 

    hidden = True

    def get_full_qualified_name(self):
        return self.name

class IdField(Int):
    
    def constraints(self):
        return "PRIMARY KEY AUTOINCREMENT"

class Text(Field):

    data_type = "TEXT"

    def fts_enabled(self):
        return self.index

class Real(Field):

    data_type = "REAL"

class Numeric(Field):

    data_type = "NUMERIC"

class Blob(Field):
    
    data_type = "BLOB"

class Date(Field):

    data_type = "Date"

class Datetime(Field):
    
    data_type = "Datetime"

class Schema: 

    id = IdField()
    rank = Rank()

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
        'WHERE', 'WITH', 'WITHOUT' 
    ]

    class SchemaError(Exception):pass

    def __init__(self,name):
        self.name=name
        self.fields={}
        self.fields_with_default={}
        self.reverse_lookup={}
        for elem in dir(self):
            obj = getattr(self,elem)
            if isinstance(obj,Field):
                if elem.startswith("_") or "__" in elem:
                    raise self.SchemaError("Cannot use '%s' as field name. Field name may not start with an underscore and may not contain double underscores." % elem)                
                if elem.upper() in self.RESERVED_KEYWORDS:
                    raise self.SchemaError("'%s' is a reserved name - Please choose another name." % elem)
                self.fields[elem] = obj
                self.fields[elem].schema = self
                self.fields[elem].name = elem
                self.reverse_lookup[obj]=elem
        for field in self:
            if field.default is not None:
                self.fields_with_default[field.name]=field

    def get_field(self,field_name,raise_exception=False):
        if raise_exception:
            if not field_name in self.fields:
                raise self.SchemaError("'%s' is not defined in this schema '%s'" % (field_name,self.__class__.__name__))
        return self.fields.get(field_name)

    def get_fields(self):
        return list(self.fields.values())

    def __iter__(self):
        return iter(self.fields.values())

class DefaultSchema(Schema):

    text = Text(index=True)

class SearchResult:
    '''
    
    '''

    def __init__(self):
        self.num_results=0
        self.query_time=None
        self.results=[]

    def __getitem__(self,index):
        return self.results[index]
    
    def __len__(self):
        return len(self.results)

    def __add__(self,obj):
        self.results.append(obj)
        return self
    
    def __iter__(self):
        return iter(self.results)

class Document:

    def __init__(self,fields):
        self.fields=fields

    def __repr__(self):
        return "<Document: %s>" % "," .join(["(%s,%s)" % (f,getattr(self,f)) for f in self.fields])

class SQLQueryComponent:

    def __init__(self,sql_query):
        self.sql_query = sql_query

    def to_sql(self):
        raise NotImplementedError()

class Select(SQLQueryComponent):

    def __init__(self,field,sql_query):
        super().__init__(sql_query) 
        self.field = field

    def to_sql(self):
        if type(self.field) is str:
            return self.field
        else:
            if isinstance(self.field,Date):
                return "{full_name} as \"{name} [date]\"".format(full_name=self.field.get_full_qualified_name(),name=self.field.name)
            elif isinstance(self.field,Datetime):
                return "{full_name} as \"{name} [timestamp]\"".format(full_name=self.field.get_full_qualified_name(),name=self.field.name)
        return self.field.get_full_qualified_name()

class Count(SQLQueryComponent):

    def __init__(self,sql_query):
        super().__init__(sql_query) 

    def to_sql(self):
        return "COUNT(*)"

class Table(SQLQueryComponent):

    def __init__(self,table_name,sql_query):
        super().__init__(sql_query) 
        self.table_name = table_name

    def to_sql(self):
        return self.table_name

LU_EQ = "eq"
LU_BOOL = "allow_boolean"
LU_NEG = "allow_negation"
LU_PREFIX = "allow_prefix"
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
    LU_EQ : [], # valid for all field types
    LU_BOOL: [Text],
    LU_NEG: [Text],
    LU_PREFIX: [Text],
    LU_GTE: [Int],
    LU_LTE: [Int],
    LU_GT: [Int],
    LU_LT: [Int],
    LU_YEAR : [Date,Datetime],
    LU_MONTH : [Date,Datetime],
    LU_DAY : [Date,Datetime],
    LU_HOUR : [Datetime],
    LU_MINUTE : [Datetime],

}

class Filter(SQLQueryComponent):

    def __init__(self,field,
                      value,
                      sql_query,
                      lookup):
        super().__init__(sql_query) 
        self.field = field    
        self.value = value
        self.keywords = []
        self.operators = ["-",".","^"]
        if not(LU_BOOL in lookup.names):
            self.keywords = self.keywords + ["AND","OR"]
        if not(LU_NEG in lookup.names):
            self.keywords.append("NOT")
        if not(LU_PREFIX in lookup.names):
            self.operators.append("*")

class MatchFilter(Filter):

    def escape(self,value):
        for v in self.keywords:
            # if one of the keywords have been found
            # we can abort and quote the entire value
            if value.find(v) != -1:
                return value.replace(v,'"%s"' % v)
        for ch in self.operators:
            if ch in value:
                return value.replace(value,'"%s"' % value)
        return value    

    def to_sql(self):
        self.sql_query.add_value(self.escape(self.value))
        return "%s MATCH ?" % self.field.get_full_qualified_name()

class BooleanFilter(SQLQueryComponent):

    def __init__(self,field,
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

    def __init__(self,field,
                      value,
                      sql_query,
                      lookup):
        super().__init__(field,value,sql_query,lookup)
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

    def __init__(self,field,sql_query,sort_dir=None):
        super().__init__(sql_query) 
        self.field = field    
        self.sort_dir = sort_dir

    def to_sql(self):
        if isinstance(self.field,str):
            if self.field.startswith("+"):
                d = "ASC"
            elif self.field.startswith("-"):
                d = "DESC"
            else:
                d = "ASC"     
            #self.sql_query.add_value(self.field[1:])  
            return "%s %s" % (self.field[1:],d)
        if self.sort_dir=="+":
            d = "ASC"
        elif self.sort_dir=="-":
            d = "DESC"
        else:
            d = "ASC"       
        #self.sql_query.add_value(self.field.get_full_qualified_name())
        return "%s %s" % (self.field.get_full_qualified_name(),d)

class LimitAndOffset(SQLQueryComponent):
    
    def __init__(self,limit,offset,sql_query):
        super().__init__(sql_query) 
        self.limit = limit    
        self.offset = offset  

    def to_sql(self):
        #self.sql_query.add_value(self.limit) 
        #self.sql_query.add_value(self.offset)
        return "LIMIT %s OFFSET %s" % (self.limit , self.offset)

class Join(SQLQueryComponent):

    def __init__(self,table_left,
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

class SQLQuery:
    '''
    Helper class that constructs the SQLQuery from 
    individual SQLQueryComponent objects
    '''

    def __init__(self,search_instance):
        self.search_instance = search_instance
        self.v_select = []
        self.v_from_tables = []
        self.v_joins=[]
        self.v_where = []
        self.v_order_by = []
        self.v_limit_and_offset = None
        self.query_args=[]

    def count(self):
        '''
        Add a count(*) expression to the current query
        '''
        self.v_select.clear()
        self.v_select.append(Count(sql_query=self))        

    def select(self,field,clear=False):
        '''
        Adds field to the selected fields clause in the statement. 
        If clear is set to True, any items that have been added 
        prior will be cleared.
        '''        
        if clear: 
            self.v_select.clear()
        self.v_select.append(Select(field=field,sql_query=self))

    def table(self,table_name,clear=False):
        '''
        Adds a reference to the from clause in the SQL statement. 
        If clear is set to True, any items that have been added 
        prior will be cleared.
        '''                
        if clear:
            self.v_from_tables.clear()
        self.v_from_tables.append(Table(table_name=table_name,sql_query=self))

    def join(self,table_left,table_right,left_field,right_field,clear=False):
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

    def where(self,field,lookup,clear=False):        
        if clear: 
            self.v_where.clear()
        if field.fts_enabled():
            filter_clazz = MatchFilter
        else:
            filter_clazz = BooleanFilter
        if field.__class__ is Date:
            filter_clazz = DateFilter
        self.v_where.append(filter_clazz(field=field,value=lookup.value,lookup=lookup, sql_query=self))    

    def order_by(self,field,sort_dir=None,clear=False):
        '''
        Adds an order_by clause to the current statement. sort_dir can either be "+" (ascending)
        or "-" (descending)
        '''        
        if clear: 
            self.v_order_by.clear()                                
        self.v_order_by.append(OrderBy(field=field,sort_dir=sort_dir,sql_query=self))

    def limit_and_offset(self,limit,offset):
        '''
        Set limit and offset of query
        '''
        self.v_limit_and_offset = LimitAndOffset(limit=limit,offset=offset,sql_query=self)
            
    def add_value(self,value):
        '''
        Adds a value to the SQL string. This value will be later added to 
        the arguments list of the execute_sql method.
        '''
        self.query_args.append(value)

    def to_sql(self):
        '''
        Render statement as SQL string
        '''
        self.query_args=[]
        stmt=["SELECT"]
        stmt.append(",".join([s.to_sql() for s in self.v_select]))
        stmt.append("FROM")
        stmt.append(",".join([t.to_sql() for t in self.v_from_tables]))
        if self.v_joins or self.v_where:
            stmt.append("WHERE")
            stmt.append(" AND ".join([j.to_sql() for j in self.v_joins]))
            if self.v_where:
                stmt.append("AND")
                stmt.append(" AND ".join([w.to_sql() for w in self.v_where]))
        stmt.append("ORDER BY")
        stmt.append(",".join([o.to_sql() for o in self.v_order_by]))
        stmt.append(self.v_limit_and_offset.to_sql())
        return " ".join(stmt) , self.query_args

class Query:

    class QueryError(Exception):
        '''
        Raised if the query could not be correctly interpreted.
        '''
        pass

    def __init__(self,search_instance,arguments):
        self.search_instance=search_instance
        self.arguments=arguments
        self.sql_query = SQLQuery(search_instance=search_instance)
        for field in self.search_instance.schema.get_fields():
            self.sql_query.select(field=field)
        for field_name , argument in arguments.items():
            #self.sql_query.select(field=argument.field)
            for lookup in argument.lookups:
                self.sql_query.where(field=argument.field,lookup=lookup) 
        self.sql_query.select("rank")
        self.sql_query.table(table_name=self.search_instance.schema.name) 
        self.sql_query.table(table_name="%s_fts" % self.search_instance.schema.name) 
        self.sql_query.join(self.sql_query.v_from_tables[0],self.sql_query.v_from_tables[1],"id","rowid")
        self.sql_query.order_by("+rank")
        self.sql_query.limit_and_offset(limit=10,offset=0)
        self.is_aggregate_query = False

    def count(self):
        self.is_aggregate_query=True
        self.sql_query.count()
        return self._query()

    def order_by(self,*args):
        for a in args:
            if a.startswith("+") or a.startswith("-"):
                field = self.search_instance.schema.get_field(a[1:],raise_exception=True)
                sort_dir = a[0]
            else:
                field = self.search_instance.schema.get_field(a,raise_exception=True)
                sort_dir = "+"
            self.sql_query.order_by(field,sort_dir,clear=True)
        return self

    def values(self,*args):
        self.sql_query.v_select.clear()
        for a in args:
            field = self.search_instance.schema.get_field(a,raise_exception=True)            
            self.sql_query.select(field)
        return self

    def _build_results(self,results):
        documents = SearchResult()
        for result in results:
            document=Document(result.keys())
            for field in result.keys():
                setattr(document,field,result[field])
            documents = documents + document
        return documents

    def _query(self):
        stmt , query_args = self.sql_query.to_sql()
        print(stmt,query_args)
        if self.is_aggregate_query:
            return self.search_instance.execute_sql(stmt,*query_args).fetchone()[0]
        else:
            return self._build_results(self.search_instance.execute_sql(stmt,*query_args))            


    def __getitem__(self, index):
        if isinstance(index, slice):
            try:
                index_start=int(index.start)
                index_stop=int(index.stop)
            except Exception:
                raise self.QueryError("Slicing arguments must be positive integers and not None.")
            self.sql_query.limit_and_offset(limit=index_stop,offset=index_start)
            return self._query()
        else:
            try:
                self.sql_query.limit_and_offset(limit=1,offset=int(index))
            except Exception:
                raise self.QueryError("Index arguments must be positive integers and not None.")
        return self._query()[0]

    def __iter__(self):
        return iter(self._query())

class PocketSearch:

    class IndexError(Exception):pass
    class FieldError(Exception):pass
    class DocumentDoesNotExist(Exception):pass

    class Argument:

        def __init__(self,field,lookups):
            self.field = field
            self.lookups = lookups

    class Lookup:

        def __init__(self,names,value):
            self.names = names
            self.value = value

    def __init__(self,db_name=None,
                      index_name="documents",
                      schema=DefaultSchema,
                      writeable=False):
        self.db_name = db_name
        self.schema = schema(index_name)
        if db_name is None:
            self.connection = sqlite3.connect(":memory:",detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        else:
            self.connection = sqlite3.connect(self.db_name,detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) 
        self.connection.row_factory = sqlite3.Row                       
        self.cursor = self.connection.cursor()
        self.db_name = db_name
        self.writeable = writeable
        if writeable or db_name is None:
            # If it is an in-memory database, we allow writes by default
            self.writeable=True
            self._create_table(self.schema.name)

    def assure_writeable(self):
        if not(self.writeable):
            raise self.IndexError("Index '%s' has been opened in read-only mode. Cannot write changes to index." % self.schema.name)

    def execute_sql(self,sql,*args):
        return self.cursor.execute(sql,args)

    def _format_sql(self,index_name,fields,sql):
        return sql.format(
            index_name=index_name,
            cols=", ".join([field.to_sql(index_table=True) for field in fields if field.name!="id"]),
            new_cols=", ".join(["new.%s" % field.to_sql(index_table=True) for field in fields if field.name!="id"]),
            old_cols=", ".join(["old.%s" % field.to_sql(index_table=True) for field in fields if field.name!="id"]),
        )          

    def _create_table(self,index_name):
        fields=[]
        index_fields=[]
        for field in self.schema:
            if (not(field.hidden)):
                if field.index:
                    index_fields.append(field)
                fields.append(field)
        if len(index_fields)==0:
            raise IndexError("Schema does not have a single indexable field.")
        sql_table = '''
        CREATE TABLE %s(%s)
        ''' % (index_name,", ".join([field.to_sql() for field in fields]))
        sql_virtual_table='''
        CREATE VIRTUAL TABLE %s_fts USING fts5(%s, content='%s', content_rowid='id');
        ''' % (index_name,", ".join([field.to_sql(index_table=True) for field in fields if field.name!="id"]),index_name)
        # Trigger definitions:
        sql_trigger_insert='''
        CREATE TRIGGER {index_name}_ai AFTER INSERT ON {index_name} BEGIN
        INSERT INTO {index_name}_fts(rowid, {cols}) VALUES (new.id, {new_cols});
        END;'''
        sql_trigger_delete='''
        CREATE TRIGGER {index_name}_ad AFTER DELETE ON {index_name} BEGIN
        INSERT INTO {index_name}_fts({index_name}_fts, rowid, {cols}) VALUES('delete', old.id, {old_cols});
        END;'''
        sql_trigger_update='''
        CREATE TRIGGER {index_name}_au AFTER UPDATE ON {index_name} BEGIN
        INSERT INTO {index_name}_fts({index_name}_fts, rowid, {cols}) VALUES('delete', old.id, {old_cols});
        INSERT INTO {index_name}_fts(rowid, {cols}) VALUES (new.id, {new_cols});
        END;
        '''
        self.cursor.execute(sql_table)
        self.cursor.execute(sql_virtual_table)
        self.cursor.execute(self._format_sql(index_name,fields,sql_trigger_insert))
        self.cursor.execute(self._format_sql(index_name,fields,sql_trigger_delete))
        self.cursor.execute(self._format_sql(index_name,fields,sql_trigger_update))

    def get_arguments(self,kwargs,for_search=True):
        '''
        Extracts field names and lookups from the keywords arguments and returns 
        a dictionary of argument objects.
        '''
        referenced_fields = {} 
        for kwarg in kwargs:
            comp = kwarg.split("__")
            if comp[0] not in referenced_fields:
                referenced_fields[comp[0]] = []
            if len(comp) > 1:
                if not(for_search):
                    raise self.FieldError("Lookups are not allowed in the context of inserts and updates")  
                referenced_fields[comp[0]].append(self.Lookup(comp[1:],kwargs[kwarg]))
            else:
                referenced_fields[comp[0]].append(self.Lookup(["eq"],kwargs[kwarg]))
        for f , lookups in referenced_fields.items():
            if f not in self.schema.fields:
                raise self.FieldError("Unknown field '%s' - it is not defined in the schema." % f)            
            for lookup in lookups:
                for name in lookup.names:
                    if not(name) in LOOKUPS:
                        raise self.FieldError("Unknown lookup: '%s' in %s" % (lookup,f))
        arguments={}
        for field in self.schema:
            if field.name not in referenced_fields and not(for_search) and field.name not in ["id","rank"]:
                raise self.FieldError("Missing field '%s' in keyword arguments." % field.name)
            if field.name in referenced_fields:
                arguments[field.name]=self.Argument(field,referenced_fields[field.name])
        return arguments


    def insert(self,*args,**kwargs):
        self.assure_writeable()
        arguments = self.get_arguments(kwargs,for_search=False)
        joined_fields = ",".join([f for f in arguments])
        values = [argument.lookups[0].value for argument in arguments.values()]
        placeholder_values = "?" * len(values)
        sql="insert into %s (%s) values (%s)" % (self.schema.name,
                                                 joined_fields,
                                                 ",".join(placeholder_values))
        self.cursor.execute(sql,values)
        self.connection.commit()

    def get(self,rowid):
        sql = "select * from %s  where id=?" % (self.schema.name,)
        fields = self.schema.get_fields()
        doc = self.cursor.execute(sql,(rowid,)).fetchone()
        if doc is None:
            raise self.DocumentDoesNotExist()
        document=Document(fields)
        for field in doc.keys():
            setattr(document,field,doc[field])        
        return document

    def update(self,**kwargs):
        self.assure_writeable()
        docid = kwargs.pop("rowid")
        arguments = self.get_arguments(kwargs,for_search=False)
        values = [argument.lookups[0].value for argument in arguments.values()] + [docid]
        stmt=[]
        for f in arguments:
            stmt.append("%s=?" % f)
        sql="update %s set %s where id=?" % (self.schema.name,",".join(stmt))
        self.cursor.execute(sql,values)
        self.connection.commit()

    def delete(self,rowid):
        self.assure_writeable()
        sql = "delete from %s where id = ?" % (self.schema.name)
        self.cursor.execute(sql,(rowid,))
        self.connection.commit()        

    def search(self,**kwargs):
        arguments = self.get_arguments(kwargs)
        return Query(self,arguments)


if __name__ == "__main__":
    p = PocketSearch(db_name="eu.db")  
    for item in p.search(text="merkel"):
        print(item.text[0:50])

    #t = Timer() 
    #for root, dirs, files in os.walk("/Users/karlkreiner/Desktop/code/git/eu_parliament/DCEP/"):
    #        for file in files:
    #            if file.endswith(".txt"):
    #                file_path = os.path.join(root, file)
    #                with open(file_path, 'r') as file:
    #                    p.insert(text=file.read())
    #                    t.snapshot()
    #t.done()
                        
