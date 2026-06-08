'''
PocketSearch: a pure-Python full-text search library based on SQLite FTS5.

This package exposes the public API. Implementation details live in the
submodules (fields, schema, queries, pocket_search, and others); import
from here as ``from pocketsearch import PocketSearch, Schema, Text``.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE FOR ANY DAMAGES OR OTHER LIABILITY,
WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

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
from .pocket_search import (
    ConnectionPool,
    PocketContextManager,
    PocketReader,
    PocketSearch,
    PocketWriter,
    QuickPocket,
    SpellChecker,
    connection_pool,
)
from .queries import Document, Q, QExpr, Query, SQLQuery, SearchResult
from .readers import FileSystemReader, IndexReader
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
from .utils import Timer, convert_date, convert_timestamp, normalize
