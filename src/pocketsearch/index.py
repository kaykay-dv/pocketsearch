import os
import time
import re
import sqlite3
import timer

import schema

class SearchResult:

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

class SQLElement:

    class QueryElementError(Exception):pass

    def __init__(self,field,value=None):
        self.field = field
        self.value = value

    def field_to_sql(self):
        raise NotImplementedError()

    def value_to_arg(self):
        if self.value is None:
            return self.value
        return ['%s' % self.value]

    def __repr__(self):
        if self.value is not  None:
            return "<%s:%s=%s>" % (self.__class__.__name__, self.field,self.value)
        else:
            return "<%s:%s>" % (self.__class__.__name__, self.field)

class Filter(SQLElement):

    def escape(self,value):
        for v in [
            "AND",
            "OR",
            "NOT"
        ]:
            # if one of the keywords have been found
            # we can abort and quote the entire value
            if value.find(v) != -1:
                return value.replace(v,'"%s"' % v)
        for ch in ["*","-","^","."]:
            if ch in value:
                return value.replace(value,'"%s"' % value)
        return value

    def field_to_sql(self):
        if "__" in self.field:
            try:
                name , lookup = self.field.split("__")
            except ValueError:
                raise self.QueryElementError("'%s' is not a valid lookup." % self.field)
        else:
            name = self.field
        return "%s match ?" % name

    def value_to_arg(self):
        # Interpret value as given. This 
        # will ignore any AND OR commands:
        return ['%s' % self.escape(self.value)]

class SelectField(SQLElement):

    def field_to_sql(self):
        return self.field

class OrderBy(SQLElement):

    def field_to_sql(self):
        if self.field.startswith("+"):
            d = "ASC"
        elif self.field.startswith("-"):
            d = "DESC"
        else:
            d = "ASC"       
        return "? %s" % d
    
    def value_to_arg(self):
        if self.field.startswith("+") or self.field.startswith("-"):
            return [self.field[1:]]
        return [self.field]

class LimitAndOffset(SQLElement):

    def field_to_sql(self):
        return "LIMIT ? OFFSET ?"
    
    def value_to_arg(self):
        limit , offset = self.value
        return [limit , offset]

class SQLElementList:
    
    def __init__(self):
        self.elements=[]

    def __add__(self,filter):
        self.elements.append(filter)
        return self
    
    def __getitem__(self,idx):
        return self.elements[idx]

    def __len__(self):
        return len(self.elements)

    def fields_to_sql(self):
        o = []
        for f in self.elements:
            o.append(f.field_to_sql())
        return ", ".join(o)
    
    def values_to_sql_arguments(self):
        o = []
        for f in self.elements:
            o.append(f.value_to_arg())
        return o

class WhereClauseElementList(SQLElementList):

    def fields_to_sql(self):
        o = []
        for f in self.elements:
            o.append(f.field_to_sql())
        return " OR ".join(o)    

class Query:

    class QueryError(Exception):pass

    COUNT_EXPR=" count(*) "

    def __init__(self,search_instance,fields,values):
        self.search_instance=search_instance
        self.where_fields = fields
        self.where_values = values
        # Default fields that are returned in search results 
        # if not explicitley set in the .values method:
        self.result_fields = ["rowid"] + self.search_instance.schema.get_fields() + ["rank"]
        self.order_by_fields = ["rank"]
        self.offset = 0
        self.limit  = 20
        self.is_aggregate_query = False

    def count(self):
        self.is_aggregate_query=True
        self.values(self.COUNT_EXPR)
        return self._query()

    def order_by(self,*args):
        self.test_fields_in_schema(args)
        self.order_by_fields.clear()
        for a in args:
            self.order_by_fields.append(a)
        return self

    def test_in_schema(self,field):
        if field not in self.search_instance.schema.get_fields() and field != self.COUNT_EXPR:
            raise self.QueryError("'%s' is not defined in the schema." % field)
        return True

    def test_fields_in_schema(self,fields):
        for f in fields:
            self.test_in_schema(f)

    def values(self,*args):
        self.test_fields_in_schema(args)
        self.result_fields.clear()
        for a in args:
            self.result_fields.append(a)
        return self

    def to_sql_elements(self,fields,clazz,values=None,list_clazz=None):
        if list_clazz is None:
            element_list = SQLElementList()
        else:
            element_list = list_clazz()
        if fields is None:
            return element_list + clazz(field=None,value=values)
        for idx,field in enumerate(fields):
            if values is None:
                element_list=element_list + clazz(field=field)
            else:
                element_list=element_list + clazz(field=field,value=values[idx])
        return element_list

    def _build_results(self,results):
        documents = SearchResult()
        for result in results:
            document=Document(result.keys())
            for field in result.keys():
                setattr(document,field,result[field])
            documents = documents + document
        return documents

    def _query(self):
        sql_arguments = []
        stmt = "" 
        where_list = self.to_sql_elements(self.where_fields,Filter,self.where_values,WhereClauseElementList)
        if len(where_list) == 0:
            from_keyword = "FROM %s" % self.search_instance.index_name 
        else:
            from_keyword = "FROM %s WHERE" % self.search_instance.index_name 
        for keyword, sql_element_list in [ ("SELECT" , self.to_sql_elements(self.result_fields,SelectField)) , 
                                           (from_keyword , where_list) , 
                                           ("ORDER BY", self.to_sql_elements(self.order_by_fields,OrderBy)), 
                                           ("", self.to_sql_elements(None,LimitAndOffset,(self.limit,self.offset))),
                                         ]:
            stmt+=" %s " % keyword
            if len(sql_element_list) > 0:
                stmt+=sql_element_list.fields_to_sql()
                for arg in sql_element_list.values_to_sql_arguments():
                    if arg is not None:
                        sql_arguments = sql_arguments + arg
        print(stmt,sql_arguments)
        if self.is_aggregate_query:
            return self.search_instance.execute_sql(stmt,*sql_arguments).fetchone()[0]
        else:
            return self._build_results(self.search_instance.execute_sql(stmt,*sql_arguments))            


    def __getitem__(self, index):
        if isinstance(index, slice):
            try:
                index_start=int(index.start)
                index_stop=int(index.stop)
            except Exception:
                raise self.QueryError("Slicing arguments must be positive integers and not None.")
            self.offset = index_start
            self.limit = index_stop
            return self._query()
        else:
            try:
                self.offset=int(index)
            except Exception:
                raise self.QueryError("Index arguments must be positive integers and not None.")
            self.limit = 1
        return self._query()[0]

    def __iter__(self):
        return iter(self._query())

class PocketSearch:

    class IndexError(Exception):pass
    class FieldError(Exception):pass
    class DocumentDoesNotExist(Exception):pass

    def __init__(self,db_name=None,
                      index_name="documents",
                      schema=schema.DefaultSchema,
                      writeable=False):
        self.db_name = db_name
        self.index_name = index_name
        self.schema = schema()
        if db_name is None:
            self.connection = sqlite3.connect(":memory:")
        else:
            self.connection = sqlite3.connect(self.db_name) 
        self.connection.row_factory = sqlite3.Row                       
        self.cursor = self.connection.cursor()
        self.db_name = db_name
        self.index_name = index_name
        self.writeable = writeable
        if writeable:
            self._create_table(index_name)

    def assure_writeable(self):
        if not(self.writeable):
            raise self.IndexError("Index '%s' has been opened in read-only mode. Cannot write changes to index." % self.index_name)

    def execute_sql(self,sql,*args):
        return self.cursor.execute(sql,args)

    def _create_table(self,index_name):
        fields=[]
        for field in self.schema:
            fields.append(field.to_sql())
        sql='''
            CREATE VIRTUAL TABLE if not exists %s USING FTS5(
                %s , tokenize = "unicode61 remove_diacritics 0"
            )
            ''' % (index_name , ", ".join(fields))
        self.cursor.execute(sql)       

    def get_arguments(self,kwargs,for_search=True):
        fields=[]
        values=[]
        doc_id = 0
        for kwarg in kwargs:
            if kwarg.split("__")[0] not in self.schema.fields:
                raise self.FieldError("Unknown field '%s' - it is not defined in the schema." % kwarg)
        for idx , field in enumerate(self.schema):
            if not(field.name in kwargs) and not(for_search):
                if field.name in self.schema.fields_with_default:
                    fields.append(field.name)
                    values.append(self.schema.fields_with_default[field.name].default())
                else:
                    raise self.FieldError("Missing field '%s' in keyword arguments." % field.name)
            if field.name in kwargs:
                fields.append(field.name)
                values.append(kwargs[field.name])
        return fields,values


    def insert(self,*args,**kwargs):
        self.assure_writeable()
        fields, values = self.get_arguments(kwargs,for_search=False)
        joined_fields = ",".join(fields)
        placeholder_values = "?" * len(values)
        sql="insert into %s (%s) values (%s)" % (self.index_name,
                                                 joined_fields,
                                                 ",".join(placeholder_values))
        self.cursor.execute(sql,values)
        self.connection.commit()

    def get(self,rowid):
        sql = "select * from %s where rowid=?" % (self.index_name,)
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
        fields, values = self.get_arguments(kwargs,for_search=False)
        stmt=[]
        for idx,f in enumerate(fields):
            stmt.append("%s='%s'" % (f,values[idx]))
        sql="update %s set %s where rowid=?" % (self.index_name,",".join(stmt))
        self.cursor.execute(sql,(docid,))
        self.connection.commit()

    def delete(self,rowid):
        self.assure_writeable()
        sql = "delete from %s where rowid = ?" % (self.index_name)
        self.cursor.execute(sql,(rowid,))
        self.connection.commit()        

    def search(self,**kwargs):
        fields, values = self.get_arguments(kwargs)
        return Query(self,fields,values)


if __name__ == "__main__":
    p = PocketSearch(db_name="eu.db")  
    for item in p.search(content="merkel"):
        print(item.content[0:50])
    '''
    t = timer.Timer() 
    for root, dirs, files in os.walk("/Users/karlkreiner/Desktop/code/git/eu_parliament/DCEP/"):
            for file in files:
                if file.endswith(".txt"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as file:
                        p.insert(content=file.read())
                        t.snapshot()
    '''
                        
