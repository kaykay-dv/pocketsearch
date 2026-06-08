"""
Field types for PocketSearch schemas.

Each field class describes a column in the SQLite index table, including its
data type, FTS indexing behaviour, and SQL constraints. Subclass ``Field`` to
define custom field types with a ``data_type`` attribute.
"""

import abc


class Field(abc.ABC):
    """
    Each schema has a number of fields.

    The field class defines the behavior of a field.
    """

    hidden = False
    data_type = None  # must be set by sub classes

    def __init__(
        self,
        name=None,
        schema=None,
        default=None,
        index=False,
        is_id_field=False,
    ):
        self.schema = schema
        self.name = name
        self.default = default
        self.index = index
        self.is_id_field = is_id_field

    def constraints(self):
        """
        Returns any constraints as string associated with the field.
        """
        if self.is_id_field:
            return " UNIQUE "
        return ""

    def fts_enabled(self):
        """
        Returns, if the field is available for full-text-search.
        """
        return False

    def get_full_qualified_name(self):
        """
        Return the full qualified name including its table for the given field.
        """
        return "%s.%s" % (self.schema.name, self.name)

    def to_sql(self, index_table=False):
        """
        Returns sql representation of field for SQL table generation.
        """
        if self.data_type is None:
            raise self.schema.SchemaError(
                "class %s (field=%s) has no data_type set"
                % (self.__class__.__name__, self.name)
            )
        name = self.schema.reverse_lookup[self]
        if index_table:
            _data_type = ""
        else:
            _data_type = self.data_type
        return "%s %s %s" % (name, _data_type, self.constraints())


class Int(Field):
    """
    Integer field
    """

    data_type = "INTEGER"


class Rank(Field):
    """
    Rank field as returned by FTS5 - it is a hidden field, meaning
    that during index creation it won't be created as actual database
    field.
    """

    hidden = True
    data_type = "REAL"

    def get_full_qualified_name(self):
        return self.name


class IdField(Int):
    """
    Creates a primary key (using autoincrement) integer field in SQLite.
    """

    def constraints(self):
        return "PRIMARY KEY AUTOINCREMENT"


class Text(Field):
    """
    Translates to sqlite3 TEXT field.
    """

    data_type = "TEXT"

    def fts_enabled(self):
        return self.index


class Real(Field):
    """
    Translates to sqlite3 REAL field.
    """

    data_type = "REAL"


class Numeric(Field):
    """
    Translates to sqlite3 NUMERIC field.
    """

    data_type = "NUMERIC"


class Blob(Field):
    """
    Translates to sqlite3 BLOB field.
    """

    data_type = "BLOB"


class Date(Field):
    """
    Translates to sqlite3 DATE field.
    """

    data_type = "Date"


class Datetime(Field):
    """
    Translates to sqlite3 Datetime field.
    """

    data_type = "Datetime"
