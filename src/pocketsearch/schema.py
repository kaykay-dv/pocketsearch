import uuid

class Field: 

    def __init__(self,name=None,schema=None,default=None):
        self.schema = schema
        self.name = name
        self.default = default

    def to_sql(self):
        return self.schema.reverse_lookup[self]
    
def get_default_id():
    return str(uuid.uuid4())

class Schema: 

    RESERVED_KEYWORDS = [
        'ABORT', 'ACTION', 'ADD', 'AFTER', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC', 'ATTACH', 'AUTOINCREMENT',
        'BEFORE', 'BEGIN', 'BETWEEN', 'BY', 'CASCADE', 'CASE', 'CAST', 'CHECK', 'COLLATE', 'COLUMN', 'COMMIT',
        'CONFLICT', 'CONSTRAINT', 'CREATE', 'CROSS', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'DATABASE',
        'DEFAULT', 'DEFERRABLE', 'DEFERRED', 'DELETE', 'DESC', 'DETACH', 'DISTINCT', 'DROP', 'EACH', 'ELSE', 'END',
        'ESCAPE', 'EXCEPT', 'EXCLUSIVE', 'EXISTS', 'EXPLAIN', 'FAIL', 'FOR', 'FOREIGN', 'FROM', 'FULL', 'GLOB',
        'GROUP', 'HAVING', 'IF', 'IGNORE', 'IMMEDIATE', 'IN', 'INDEX', 'INDEXED', 'INITIALLY', 'INNER', 'INSERT',
        'INSTEAD', 'INTERSECT', 'INTO', 'IS', 'ISNULL', 'JOIN', 'KEY', 'LEFT', 'LIKE', 'LIMIT', 'MATCH', 'NATURAL',
        'NO', 'NOT', 'NOTNULL', 'NULL', 'OF', 'OFFSET', 'ON', 'OR', 'ORDER', 'OUTER', 'PLAN', 'PRAGMA', 'PRIMARY',
        'QUERY', 'RAISE', 'RECURSIVE', 'REFERENCES', 'REGEXP', 'REINDEX', 'RELEASE', 'RENAME', 'REPLACE', 'RESTRICT',
        'RIGHT', 'ROLLBACK', 'ROW', 'SAVEPOINT', 'SELECT', 'SET', 'TABLE', 'TEMP', 'TEMPORARY', 'THEN', 'TO',
        'TRANSACTION', 'TRIGGER', 'UNION', 'UNIQUE', 'UPDATE', 'USING', 'VACUUM', 'VALUES', 'VIEW', 'VIRTUAL', 'WHEN',
        'WHERE', 'WITH', 'WITHOUT' , 'RANK'
    ]

    class SchemaError(Exception):pass

    def __init__(self):
        self.fields={}
        self.fields_with_default={}
        self.reverse_lookup={}
        for elem in dir(self):
            obj = getattr(self,elem)
            if isinstance(obj,Field):
                if elem.upper() in self.RESERVED_KEYWORDS:
                    raise self.SchemaError("'%s' is a reserved name - Please choose another name." % elem)
                self.fields[elem] = obj
                self.fields[elem].schema = self
                self.fields[elem].name = elem
                self.reverse_lookup[obj]=elem
        for field in self:
            if field.default is not None:
                self.fields_with_default[field.name]=field

    def get_fields(self):
        return list(self.fields.keys())

    def __iter__(self):
        return iter(self.fields.values())

class DefaultSchema(Schema):

    content = Field()



