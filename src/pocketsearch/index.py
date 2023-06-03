import os
import time
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

class Query:

    def __init__(self,search_instance,fields,values):
        self.search_instance=search_instance
        self.fields = fields
        self.values = values
        self.offset = 0
        self.limit  = 20
        self._order_by = [] 

    def order_by(self,*args):
        for o in args:
            if o.startswith("+"):
                direction = "asc"
            elif o.startswith("-"):
                direction = "desc"
            else:
                direction = "asc"
            self._order_by.append(" %s %s " % (o,direction))
        return self

    def _where_clause(self):
        clause=[]
        for idx, f in enumerate(self.fields):
            clause.append(" %s match '\"%s\"' " % (f , self.values[idx]))
        if len(clause) > 0:
            return " where " + " and ".join(clause)
        return ""

    def _query(self):
        search_fields = ["rowid"] + self.fields + ["rank"]
        #["highlight(%s,0,'[',']')" % f for f in self.fields]
        #["highlight(%s,0,'[',']')" % f for f in self.search_instance.schema.get_fields()]
        result_fields = ["rowid"] + self.search_instance.schema.get_fields() + ["rank"]
        # FIXME: do proper quoting here, queries like "'x'" will fail.
        sql = '''
           select %s from %s %s 
        ''' % (", ".join(result_fields),
               self.search_instance.index_name,               
               self._where_clause())
        if len(self._order_by)==0:
            sql+=" order by rank "
        else:
            sql+=" order by %s" % "," .join(self._order_by)        
        sql+=" limit %s offset %s " % (self.limit,self.offset)
        results = SearchResult()
        for result in self.search_instance.execute_sql(sql):
            item=Document(result_fields)
            for field in result_fields:
                setattr(item,field,result[field])
            results = results + item
        return results

    def __getitem__(self, index):
        self.offset = index
        self.limit = 1
        if isinstance(index, slice):
            self.offset = index.start
            self.limit = index.stop
            return self._query()
        return self._query()[0]

    def count(self):
        sql = '''
           select count(*) from %s %s 
        ''' % (self.search_instance.index_name,self._where_clause())        
        return self.search_instance.execute_sql(sql).fetchone()[0]

    def __iter__(self):
        return iter(self._query())

class PocketSearch:

    class FieldError(Exception):pass
    class DocumentDoesNotExist(Exception):pass

    def __init__(self,db_name=None,
                      index_name="documents",
                      schema=schema.DefaultSchema,
                      create_index=True):
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
        if create_index:
            self._create_table(index_name)

    def execute_sql(self,sql,commit=False):
        return self.cursor.execute(sql)

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
            if kwarg not in self.schema.fields:
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
        fields, values = self.get_arguments(kwargs,for_search=False)
        joined_fields = ",".join(fields)
        placeholder_values = "?" * len(values)
        sql="insert into %s (%s) values (%s)" % (self.index_name,
                                                 joined_fields,
                                                 ",".join(placeholder_values))
        self.cursor.execute(sql,values)
        self.connection.commit()

    def get(self,rowid):
        sql = "select * from %s where rowid=%s" % (self.index_name,rowid)
        fields = self.schema.get_fields()
        doc = self.cursor.execute(sql).fetchone()
        if doc is None:
            raise self.DocumentDoesNotExist()
        document=Document(fields)
        for field in doc.keys():
            setattr(document,field,doc[field])        
        return document

    def update(self,**kwargs):
        docid = kwargs.pop("rowid")
        fields, values = self.get_arguments(kwargs,for_search=False)
        stmt=[]
        for idx,f in enumerate(fields):
            stmt.append("%s='%s'" % (f,values[idx]))
        sql="update %s set %s where rowid=%s" % (self.index_name,",".join(stmt),docid)
        self.cursor.execute(sql)
        self.connection.commit()

    def delete(self,rowid):
        sql = "delete from %s where rowid = %s" % (self.index_name,rowid)
        self.cursor.execute(sql)
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
                        
