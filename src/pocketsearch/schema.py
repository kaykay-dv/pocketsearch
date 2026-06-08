import collections
import copy

from .fields import Field, IdField, Rank, Text
from .tokenizers import Unicode61


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
