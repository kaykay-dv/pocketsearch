'''
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE FOR ANY DAMAGES OR OTHER LIABILITY,
WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sys
import sqlite3
import os.path
import unittest
import threading
import tempfile
import datetime
import logging

from pocketsearch import PocketSearch, PocketReader, PocketWriter, Schema, ConnectionPool, connection_pool
from pocketsearch import Text, Int, Real, Blob, Field, Datetime, Date, IdField
from pocketsearch import Unicode61
from pocketsearch import Query, Q
from pocketsearch import FileSystemReader

logging.basicConfig(level=logging.DEBUG)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


class Movie(Schema):
    '''
    A simple movie schema we use for tests.
    '''

    title = Text(index=True)
    text = Text(index=True)


class CustomField(Field):
    '''
    Field with no data type provided
    '''


class Page(Schema):
    '''
    Page schema to use multi-field searches
    '''

    title = Text(index=True)
    category = Text(index=True)
    text = Text(index=True)


class BrokenSchema(Schema):
    '''
    Broken schema definition - select is a reserved keyword.
    '''

    select = Field()


class BrokenSchemaUnderscores(Schema):
    '''
    Broken schema definition - Underscores are not allowed
    '''

    test__123 = Field()


class SchemaCustomField(Schema):
    '''
    Schema using a custom field with no data type
    '''

    custom_field = CustomField()


class SchemaTest(unittest.TestCase):
    '''
    Tests for schema generation
    '''

    def test_create_schema(self):
        '''
        Schema creation test
        '''
        schema = Movie(name="movie")
        for field in ["title", "text"]:
            self.assertEqual(field in schema.fields, True)

    def test_use_underscores_in_fields(self):
        '''
        Schema creation test with field containing underscores
        '''
        with self.assertRaises(Schema.SchemaError):
            schema = BrokenSchemaUnderscores(name="broken")

    def test_use_reserved_keywords(self):
        '''
        Schema creation test with field containing keywords
        '''
        with self.assertRaises(Schema.SchemaError):
            BrokenSchema(name="broken")

    def test_field_no_data_type(self):
        '''
        Schema creation test with field having no data type
        '''
        with self.assertRaises(Schema.SchemaError):
            schema = SchemaCustomField(name="broken")


class BaseTest(unittest.TestCase):
    '''
    Base test class that creates some test data
    '''

    def setUp(self):
        self.data = [
            "The fox jumped over the fence. Now he is beyond the fence.",
            "England is in Europe.",
            "Paris is the captial of france.",
        ]
        self.pocket_search = PocketSearch(
            index_name="text_data", writeable=True)
        for elem in self.data:
            self.pocket_search.insert(text=elem)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()


class SQLFunctionTests(BaseTest):

    def test_highlight(self):
        self.assertEqual(
            "*fox*" in self.pocket_search.search(text="fox").highlight("text")[0].text, True)

    def test_highlight_alternative_marker(self):
        self.assertEqual("<b>fox</b>" in self.pocket_search.search(text="fox").highlight(
            "text", marker_start="<b>", marker_end="</b>")[0].text, True)

    def test_snippet(self):
        text = '''
        In computer science, an inverted index (also referred to as a postings list, postings file, or inverted file) is a 
        database index storing a mapping from content, such as words or numbers, to its locations in a table, or in a 
        document or a set of documents (named in contrast to a forward index, which maps from documents to content).
        The purpose of an inverted index is to allow fast full-text searches, at a cost of increased processing when a 
        document is added to the database.[2] The inverted file may be the database file itself, rather than its index. 
        It is the most popular data structure used in document retrieval systems,[3] used on a large scale for example in search engines.
        '''
        self.pocket_search.insert(text=text)
        result = self.pocket_search.search(
            text="forward index").snippet("text")[0].text
        eq = self.assertEqual
        eq("*forward*" in result, True)
        eq("*index*" in result, True)
        # Test alternative before/after text
        result = self.pocket_search.search(text="forward index").snippet(
            "text", text_before="<b>", text_after="</b>")[0].text
        eq("<b>forward</b>" in result, True)
        eq("<b>index</b>" in result, True)

    def test_snippet_length_too_big(self):
        '''
        Snippets may not exceed 64 tokens
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="forward index").snippet(
                "text", snippet_length=128)

    def test_snippet_length_too_small(self):
        '''
        Snippets must have at least 1 token
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="forward index").snippet(
                "text", snippet_length=0)


class TokenInfoTest(BaseTest):
    '''
    Test accessing meta data of the index
    '''

    def test_get_tokens(self):
        '''
        Try to access the list of tokens
        '''
        tokens = list(self.pocket_search.tokens())
        # Check number of entries, should be 16
        self.assertEqual(len(tokens), 16)
        # Check, if the first entry is the most frequent token
        self.assertEqual(tokens[0]["token"], "the")
        self.assertEqual(tokens[0]["num_documents"], 2)
        self.assertEqual(tokens[0]["total_count"], 4)

    def test_delete_tokens(self):
        '''
        Test, if deletes are propagated to the token statistics
        '''
        rowid = self.pocket_search.search(text="fox")[0].id
        tokens = list(self.pocket_search.tokens())
        self.assertEqual(len(tokens), 16)
        self.pocket_search.delete(rowid=rowid)
        self.assertEqual(self.pocket_search.search(text="fox").count(), 0)
        # Number of tokens should now be reduced:
        tokens = list(self.pocket_search.tokens())
        self.assertEqual(len(tokens), 9)

    def test_empty_pocket(self):
        '''
        Empty index should lead to an empty list
        '''
        p = PocketSearch()
        self.assertEqual(len(list(p.tokens())), 0)


class OperatorSearch(BaseTest):
    '''
    Tests covering the usage of boolean operators and prefix search
    '''

    def test_search_len_func(self):
        # test application of len function to search result
        self.assertEqual(len(self.pocket_search.search(text="france")[0:1]), 1)

    def test_search_empty(self):
        # by definition, an empty search returns all objects
        self.assertEqual(self.pocket_search.search(text="").count(), 0)

    def test_search_none(self):
        # by definition, an empty search returns all objects
        self.assertEqual(self.pocket_search.search(text=None).count(), 0)

    def test_search_prefix(self):
        # by default, prefix search is not supported:
        self.assertEqual(self.pocket_search.search(text="fran*").count(), 0)

    def test_search_prefix_explicit(self):
        # by default, prefix search is not supported:
        self.assertEqual(self.pocket_search.search(
            text__allow_prefix="fran*").count(), 1)

    def test_initial_token_queries_implicit(self):
        self.pocket_search.insert(text="Paris is not the capital of england.")
        # in this case, the ^ operator will be ignored and 2 matches found:
        self.assertEqual(self.pocket_search.search(text="^england").count(), 2)

    def test_initial_token_queries_explicit(self):
        self.pocket_search.insert(text="Paris is not the capital of england.")
        # search for results where england can be found at the begining:
        self.assertEqual(self.pocket_search.search(
            text__allow_initial_token="^england").count(), 1)
        self.assertEqual(self.pocket_search.search(
            text__allow_initial_token__allow_prefix="^engl*").count(), 1)

    def test_search_and_or_query_default(self):
        # by default, AND/OR queries are not supported:
        self.assertEqual(self.pocket_search.search(
            text='france AND paris').count(), 0)
        self.assertEqual(self.pocket_search.search(
            text='france OR paris').count(), 0)

    def test_near_query(self):
        # NEAR queries are not supported at the moment
        self.assertEqual(self.pocket_search.search(
            text='NEAR(one, two)').count(), 0)

    def test_combined_lookups(self):
        self.assertEqual(self.pocket_search.search(
            text__allow_boolean__allow_prefix='france OR engl*').count(), 2)

    def test_search_and_or_query_explicit(self):
        # Allow AND + OR
        self.assertEqual(self.pocket_search.search(
            text__allow_boolean='france AND paris').count(), 1)
        self.assertEqual(self.pocket_search.search(
            text__allow_boolean='france OR paris').count(), 1)
        self.assertEqual(self.pocket_search.search(
            text__allow_boolean='france OR england OR fence').count(), 3)

    def test_negation_default(self):
        # By default, negation is not supported
        self.assertEqual(self.pocket_search.search(
            text="NOT france").count(), 0)


class PrefixIndexTest(unittest.TestCase):
    '''
    Test creation of prefix indices
    '''

    class PrefixIndex1(Schema):
        '''
        Simple schema that sets a prefix index for 
        2,3 and 4 characters
        '''
        class Meta:
            prefix_index = [2, 3, 4]
        body = Text(index=True)

    class PrefixIndex2(Schema):
        '''
        Prefix index definition with negative numbers
        '''
        class Meta:
            prefix_index = [2, -3, 4]
        body = Text(index=True)

    class PrefixIndex3(Schema):
        '''
        Prefix index definition, wrong data type
        '''
        class Meta:
            prefix_index = "2,3,4"

        body = Text(index=True)

    class PrefixIndex4(Schema):
        '''
        Prefix index definition with duplicate values
        '''
        class Meta:
            prefix_index = [2, 2, 4]
        body = Text(index=True)

    class PrefixIndex5(Schema):
        '''
        Prefix index definition with duplicate values
        '''
        class Meta:
            prefix_index = [0, 1]
        body = Text(index=True)

    class PrefixIndex6(Schema):
        '''
        Prefix index definition with non-integer values
        '''
        class Meta:
            prefix_index = ["0", 1]
        body = Text(index=True)

    def test_create_prefix_index(self):
        '''
        Test creation of prefix index
        '''
        p = PocketSearch(schema=self.PrefixIndex1)
        p.close()
        with self.assertRaises(Schema.SchemaError):
            PocketSearch(schema=self.PrefixIndex2)
        with self.assertRaises(Schema.SchemaError):
            PocketSearch(schema=self.PrefixIndex3)
        p = PocketSearch(schema=self.PrefixIndex4)
        p.close()
        with self.assertRaises(Schema.SchemaError):
            PocketSearch(schema=self.PrefixIndex6)


class PhraseSearch(unittest.TestCase):

    def test_search_phrase(self):
        pocket_search = PocketSearch(writeable=True)
        pocket_search.insert(text="This is a phrase")
        pocket_search.insert(text="a phrase this is")
        self.assertEqual(pocket_search.search(
            text="This is a phrase").count(), 2)
        self.assertEqual(pocket_search.search(
            text="this phrase a is").count(), 2)
        self.assertEqual(pocket_search.search(
            text='"this is a phrase"').count(), 1)
        pocket_search.close()

    def test_multiple_phrases(self):
        pocket_search = PocketSearch(writeable=True)
        pocket_search.insert(text="This is a phrase")
        self.assertEqual(pocket_search.search(
            text='"this is" "a phrase"').count(), 1)
        self.assertEqual(pocket_search.search(
            text='"this is" "phrase a"').count(), 0)
        pocket_search.close()


class PermanentDatabaseTest(unittest.TestCase):

    def test_create_permanent_db(self):
        '''
        Test writing to a database on disk and reading 
        afterwards from it:
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            # set write buffer size to 100, so we can test
            # if the context manager does the final commit right:
            with PocketWriter(db_name=db_name) as pocket_writer:
                pocket_writer.insert(text="Hello world.")
            # read out again and do a count
            with PocketReader(db_name=db_name) as pocket_reader:
                num_docs = pocket_reader.search(text="world").count()
                self.assertEqual(num_docs, 1)


class ContextManagerTest(unittest.TestCase):

    def test_context_manager(self):
        '''
        Tests for in-memory context managers
        '''
        # Create in-memory database:
        with PocketWriter() as pocketsearch:
            pocketsearch.insert(text="Hello world.")
            self.assertEqual(pocketsearch.search().count(), 1)
        # Create reader - this should return 0 results
        # as the PocketReader creates a new database:
        with PocketReader() as pocketsearch:
            self.assertEqual(pocketsearch.search(
                text="Hello world.").count(), 0)


class TransactionTests(unittest.TestCase):
    '''
    Tests that ensure that error handling (and transaction rollbacks more specifically)
    are handled as expected.
    '''

    def test_delete(self):
        '''
        Test if delete operations are rolled back if an exception occurs.
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            with PocketWriter(db_name=db_name) as writer:
                writer.insert(text="Text #1")
                writer.insert(text="Text #2")
            try:
                with PocketWriter(db_name=db_name) as writer:
                    writer.delete(rowid=1)
                    0 / 0
            except ZeroDivisionError:
                with PocketReader(db_name=db_name) as reader:
                    self.assertEqual(reader.search().count(), 2)

    def test_update(self):
        '''
        Test if update operations are rolled back if an exception occurs.
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            with PocketWriter(db_name=db_name) as writer:
                writer.insert(text="Text #1")
            try:
                with PocketWriter(db_name=db_name) as writer:
                    writer.update(rowid=1, text="updated")
                    0 / 0
            except ZeroDivisionError:
                with PocketReader(db_name=db_name) as reader:
                    self.assertEqual(reader.search(text="updated").count(), 0)

    def test_delete_all(self):
        '''
        Test if delete_all operations are rolled back if an exception occurs.
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            with PocketWriter(db_name=db_name) as writer:
                writer.insert(text="Text #1")
            try:
                with PocketWriter(db_name=db_name) as writer:
                    writer.delete_all()
                    0 / 0
            except ZeroDivisionError:
                with PocketReader(db_name=db_name) as reader:
                    self.assertEqual(reader.search().count(), 1)

    def test_insert(self):
        '''
        Tests, if insert operations are rolled back correctly
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            with PocketWriter(db_name=db_name) as writer:
                writer.insert(text="Text #1")
            try:
                with PocketWriter(db_name=db_name) as writer:
                    writer.insert(text="Text #2")
                    writer.insert(text="Text #3")
                    # now cause an exception - this should lead to a rollback
                    # in the database
                    0 / 0
            except ZeroDivisionError:
                with PocketReader(db_name=db_name) as reader:
                    self.assertEqual(reader.search(text="text").count(), 1)


class IndexTest(BaseTest):

    def test_write_to_read_only_index(self):
        pocket_search = PocketSearch(writeable=False)
        # in.memory dbs are writeable by default so we set the flag manually
        pocket_search.writeable = False
        with self.assertRaises(pocket_search.IndexError):
            pocket_search.insert(text="21")
        pocket_search.close()

    def test_optimize_within_transcation(self):
        pocket_search = PocketSearch()
        pocket_search.insert(text="123")
        pocket_search.commit()
        # with self.assertRaises(Exception):
        # this should not work, as vacuum is not allowed at this stage
        pocket_search.optimize()
        pocket_search.close()

    def test_use_insert_update_with_lookups(self):
        pocket_search = PocketSearch()
        with self.assertRaises(pocket_search.FieldError):
            pocket_search.insert(text__allow_boolean="123")
        pocket_search.insert(text="123")
        with self.assertRaises(pocket_search.FieldError):
            pocket_search.update(
                rowid=1, text__allow_boolean="The DOG jumped over the fence. Now he is beyond the fence.")
        pocket_search.close()

    def test_unknown_field(self):
        try:
            self.pocket_search.insert(non_existing_field_in_schema="21")
        except self.pocket_search.FieldError:
            pass

    def test_count(self):
        self.assertEqual(self.pocket_search.search(text="is").count(), 3)
        self.assertEqual(self.pocket_search.search(
            text="notinindex").count(), 0)

    def test_indexing(self):
        self.assertEqual(self.pocket_search.search(
            text="fence")[0].text, self.data[0])
        self.assertEqual(self.pocket_search.search(
            text="is")[0].text, self.data[1])

    def test_get_all(self):
        self.assertEqual(self.pocket_search.search().count(), 3)

    def test_get_rowid(self):
        self.pocket_search.search()[0].id

    def test_slicing_open(self):
        with self.assertRaises(Query.QueryError):
            results = self.pocket_search.search(text="is")[0:]

    def test_negative_slicing_start(self):
        with self.assertRaises(Query.QueryError):
            results = self.pocket_search.search(text="is")[-1:]

    def test_negative_slicing_end(self):
        with self.assertRaises(Query.QueryError):
            results = self.pocket_search.search(text="is")[:-4]

    def test_start_stop_none(self):
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="is")[:]

    def test_non_numeric_index(self):
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="is")["a"]

    def test_slicing(self):
        results = self.pocket_search.search(text="is")[0:2]
        self.assertEqual(results[0].text, self.data[1])
        self.assertEqual(results[1].text, self.data[2])

    def test_setitem_results(self):
        results = self.pocket_search.search(text="is")[0:2]
        results[0]

    def test_iteration(self):
        for idx, item in enumerate(self.pocket_search.search(text="is")):
            item.text  # just check, if it possible to call the attribute

    def test_order_by_override_default_order_by(self):
        # This should override the default rank sorting by the text sorting
        r = self.pocket_search.search(text="is").values(
            "id", "rank", "text").order_by("-text")
        self.assertEqual(r[0].text, self.data[0])
        self.assertEqual(r[1].text, self.data[2])
        self.assertEqual(r[2].text, self.data[1])


class QTests(unittest.TestCase):
    '''
    Tests the behavior of the Q operator
    '''

    class Product(Schema):
        '''
        Schema with Two-field FTS index
        '''
        code = Text(index=True)
        product = Text(index=True)
        price = Int()

    def setUp(self):
        self.pocketsearch = PocketSearch(schema=self.Product)
        for code, name, price in [
            ("A01", "Apple", 4),
            ("A02", "Peach", 7),
            ("A03", "Orange", 8),
            ("B01", "Grapefruit", 5),
            ("B02", "Banana", 9),
            ("C01", "Apple and Orange", 3),
        ]:
            self.pocketsearch.insert(code=code, product=name, price=price)

    def tearDown(self):
        self.pocketsearch.close()
        return super().tearDown()

    def test_deprecated_union_search(self):
        # FIXME: test if log message is actually written
        self.pocketsearch.search(
            product="apple") | self.pocketsearch.search(product="peach")

    def test_or_empty(self):
        q = self.pocketsearch.search(Q(product=''))
        self.assertEqual(q.count(), 0)

    def test_or_none(self):
        q = self.pocketsearch.search(Q(product=None))
        self.assertEqual(q.count(), 0)

    def test_or_same_keyword(self):
        q = self.pocketsearch.search(Q(product='apple') | Q(product='Peach'))
        self.assertEqual(q.count(), 3)

    def test_phrase_query(self):
        q = self.pocketsearch.search(Q(product='"apple and orange"'))
        self.assertEqual(q.count(), 1)
        q = self.pocketsearch.search(Q(product='orange and apple'))
        self.assertEqual(q.count(), 1)

    def test_initial_token_query(self):
        # This should only bring one result back:
        q = self.pocketsearch.search(Q(price__gte=3) & Q(
            product__allow_initial_token="^Orange"))
        self.assertEqual(q.count(), 1)

    def test_and(self):
        q = self.pocketsearch.search(Q(product="Apple") & Q(
            code__allow_prefix="A*") & Q(price__gte=2))
        self.assertEqual(q.count(), 1)
        # Test the other way around:
        q = self.pocketsearch.search(Q(price__gte=2) & Q(
            product="Apple") & Q(code__allow_prefix="A*"))
        self.assertEqual(q.count(), 1)
        # Mixed
        q = self.pocketsearch.search(
            Q(code__allow_prefix="A*") & Q(price__gte=2) & Q(product="Apple"))
        self.assertEqual(q.count(), 1)

    def test_or(self):
        q = self.pocketsearch.search(Q(price__gte=9) | Q(price__lte=3))
        self.assertEqual(q.count(), 2)

    def test_combined_and_or(self):
        q = self.pocketsearch.search(Q(price__gte=1) & Q(
            price__lte=5) & Q(product="Apple") | Q(product="Orange"))
        self.assertEqual(q.count(), 2)

    def test_mixed_q_query(self):
        with self.assertRaises(Query.QueryError):
            self.pocketsearch.search(
                Q(price__gte=1) & Q(price__lte=5), product="apple")

    def test_q_objects_multiple_kw_arguments(self):
        with self.assertRaises(Query.QueryError):
            self.pocketsearch.search(Q(price__gte=1, price__lte=5))


class IDFieldTest(unittest.TestCase):

    class IdSchema(Schema):

        text = Text(index=True)
        file_name = Text(is_id_field=True)

    class IdSchema2IdFields(Schema):

        text = Text(index=True, is_id_field=True)
        file_name = Text(is_id_field=True)

    def test_add_id_field(self):
        pocket_search = PocketSearch(schema=self.IdSchema)
        self.assertEqual(pocket_search.schema.id_field, "file_name")
        pocket_search.close()

    def test_add_data(self):
        pocket_search = PocketSearch(schema=self.IdSchema)
        pocket_search.insert(text="A", file_name="a.txt")
        with self.assertRaises(pocket_search.DatabaseError):
            pocket_search.insert(text="B", file_name="a.txt")

    def test_insert_or_update_no_id_field(self):
        pocket_search = PocketSearch()
        with self.assertRaises(pocket_search.DatabaseError):
            pocket_search.insert_or_update(text="123")

    def test_insert_or_update(self):
        pocket_search = PocketSearch(schema=self.IdSchema)
        pocket_search.insert(text="A", file_name="a.txt")
        pocket_search.insert_or_update(text="B", file_name="a.txt")
        self.assertEqual(pocket_search.search(text="B").count(), 1)

    def test_add_2_id_fields(self):
        with self.assertRaises(Schema.SchemaError):
            PocketSearch(schema=self.IdSchema2IdFields)


class IndexUpdateTests(BaseTest):
    '''
    Test updates on schemas
    '''

    class Example(Schema):
        '''
        Multi-field schema to test updates to 
        multiple fields in one .update call
        '''

        f1 = Text(index=True)
        f2 = Text(index=True)

    def test_get_entry(self):
        '''
        Test get document by id
        '''
        document = self.pocket_search.get(rowid=1)
        self.assertEqual(document.id, 1)

    def test_get_non_existing_entry(self):
        '''
        Getting a document with a non-existing id, should result in an 
        exception
        '''
        with self.assertRaises(self.pocket_search.DocumentDoesNotExist):
            self.pocket_search.get(rowid=1000)

    def test_delete_entry(self):
        '''
        Entry if "fox" should have disappeared:
        '''
        self.pocket_search.delete(rowid=1)
        self.assertEqual(self.pocket_search.search(text="fox").count(), 0)

    def test_delete_all(self):
        '''
        Should result in an empty database
        '''
        self.pocket_search.delete_all()
        self.assertEqual(self.pocket_search.search().count(), 0)
        # try to apply the delete again:
        self.pocket_search.delete_all()

    def test_update_entry(self):
        '''
        Test updating an entry
        '''
        self.pocket_search.update(
            rowid=1, text="The DOG jumped over the fence. Now he is beyond the fence.")
        self.assertEqual(self.pocket_search.search(text="fox").count(), 0)
        self.assertEqual(self.pocket_search.search(text="dog").count(), 1)
        self.assertEqual(self.pocket_search.search().count(), 3)

    def test_update_multiple_fields(self):
        '''
        Test updating multiple fields
        '''
        p = PocketSearch(schema=self.Example)
        p.insert(f1="a", f2="b")
        rowid = p.search(f1="a", f2="b")[0].id
        p.update(rowid=rowid, f1="c", f2="d")
        self.assertEqual(p.search(f1="a", f2="b").count(), 0)
        self.assertEqual(p.search(f1="c", f2="d").count(), 1)
        p.close()

    # def test_buffered_writes(self):
    #    '''
    #    Test buffered writing
    #    '''
    #    pocket_search = PocketSearch(write_buffer_size=3,writeable=True)
    #    pocket_search.insert(text="A")
    #    # inserted row is immediately visible:
    #    self.assertEqual(pocket_search.search().count(),1)
    #    self.assertEqual(pocket_search.write_buffer,1)
    #    pocket_search.insert(text="B")
    #    self.assertEqual(pocket_search.search().count(),2)
    #    self.assertEqual(pocket_search.write_buffer,2)
    #    pocket_search.insert(text="C")
    #    self.assertEqual(pocket_search.search().count(),3)
    #    # now the write buffer should be set back to 0
    #    self.assertEqual(pocket_search.write_buffer,0)


class EscapeTests(unittest.TestCase):

    def test_escape_characters(self):
        '''
        Test the proper handling of punctuation in queries. 
        '''
        pocket_search = PocketSearch(writeable=True)
        pocket_search.insert(text="Hello")
        pocket_search.insert(text="World")
        pocket_search.insert(text="Hello World!")
        pocket_search.insert(text="World Hello")
        # in this case, punctuation characters are automatically removed from the query:
        self.assertEqual(pocket_search.search(text='hello $ !').count(), 3)
        # however double quotes are kept to make phrase query possible
        self.assertEqual(pocket_search.search(text='"Hello World"').count(), 1)


class AutocompleteTest(unittest.TestCase):
    '''
    Tests for autocomplete method.
    '''

    def setUp(self):
        self.pocket_search = PocketSearch(writeable=True)
        for elem in [
            "Jones Indiana",
            "Indiana Jones",
            "Star Wars",
            "The return of the Jedi"
        ]:
            self.pocket_search.insert(text=elem)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_args_provided(self):
        '''
        No positional arguments are not allowed
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.autocomplete("Ind")

    def test_autocomplete_multiple_keywords(self):
        '''
        Multiple keywords are not allowed
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.autocomplete(text="Ind", title="Ind")

    def test_autocomplete_with_lookups(self):
        '''
        Multiple keywords are not allowed
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.autocomplete(text__allow_prefix="Ind")

    def test_autocomplete_unknown_field(self):
        '''
        Test if exception is correctly thrown
        '''
        with self.assertRaises(self.pocket_search.FieldError):
            self.pocket_search.autocomplete(product="Ind")

    def test_no_kwarg_given(self):
        '''
        If no keyword argument is provided, all results are returned
        '''
        self.assertEqual(self.pocket_search.autocomplete().count(), 4)

    def test_autocomplete_one_token(self):
        '''
        Both autocomplete queries should bring "Indiana Jones" as first result,
        as "Indiana" is at the beginning of the column, "Jones Indiana" should 
        come second.
        '''
        self.assertEqual(self.pocket_search.autocomplete(
            text="In")[0].text, "Indiana Jones")
        self.assertEqual(self.pocket_search.autocomplete(
            text="In")[1].text, "Jones Indiana")
        self.assertEqual(self.pocket_search.autocomplete(
            text="Ind")[0].text, "Indiana Jones")
        self.assertEqual(self.pocket_search.autocomplete(
            text="In")[1].text, "Jones Indiana")

    def test_order_by(self):
        '''
        Test, if order by can be applied to autocomplete.
        This should bring Jones Indiana as first result, as we sort by -rank
        '''
        self.assertEqual(self.pocket_search.autocomplete(
            text="In").order_by("-rank")[0].text, "Jones Indiana")

    def test_autocomplete_two_tokens(self):
        '''
        Test autocomplete with 2 tokens
        '''
        self.assertEqual(self.pocket_search.autocomplete(
            text="Indiana J")[0].text, "Indiana Jones")

    def test_autocomplete_including_and_or_operators(self):
        '''
        AND/OR keywords cannot be used in autocomplete:
        '''
        self.assertEqual(self.pocket_search.autocomplete(
            text="INDIANA OR JONES").count(), 0)
        self.assertEqual(self.pocket_search.autocomplete(
            text="INDIANA AND JONES").count(), 0)

    def test_autocomplete_three_tokens(self):
        '''
        Test autocomplete with 3 tokens
        '''
        self.assertEqual(self.pocket_search.autocomplete(
            text="return of the")[0].text, "The return of the Jedi")

    def test_special_characters_in_query(self):
        '''
        Test if quoting, works. Special characters are not allowed 
        in autocomplete queries
        '''
        self.assertEqual(self.pocket_search.autocomplete(text="*").count(), 0)


class Unicode61Tests(unittest.TestCase):
    '''
    Tests for Unicode61 tokenizer
    '''

    def test_valid_invalid_diacritics(self):
        '''
        Test invalid diacritics options
        '''
        with self.assertRaises(Unicode61.TokenizerError):
            Unicode61(remove_diacritics="-1")
            Unicode61(remove_diacritics="8")
            Unicode61(remove_diacritics="b")
            # not allowed, values must be strings
            Unicode61(remove_diacritics=2)

    def test_tokenize(self):
        '''
        Basic test to see if the tokenize method can 
        simulate the tokenization process of FTS5's unicode61 tokenizer
        '''
        under_test = "(This) 'is' a-toke2nize;te^st."
        tokens = Unicode61().tokenize(under_test)
        self.assertEqual(len(tokens), 6)

    def test_additional_separator(self):
        '''
        Test if the tokenize method respects additional separators
        '''
        under_test = "(This)X'is'Ya-toke2nizeZtest."
        tokens = Unicode61(separators="XYZ").tokenize(under_test)
        self.assertEqual(len(tokens), 5)

    def test_tokenize_custom_categories_and_separators(self):
        '''
        Customize the categories and separators argument
        '''
        under_test = "(This)X'is'Ya-toke42nizeZtest."
        tokens = Unicode61(
            categories="N*", separators="4").tokenize(under_test)
        # this indicates that only numbers are valid tokens, thus
        # everything else is considered a separator character
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0], "2")


class TokenizerTests(unittest.TestCase):
    '''
    Test the behavior of various tokenizers
    '''

    class SchemaDiacritics(Schema):

        class Meta:
            tokenizer = Unicode61()

        text = Text(index=True)

    def test_remove_diacritics(self):
        '''
        Test if search recognizes characters with diacritics
        '''
        self.SchemaDiacritics.Meta.tokenizer = Unicode61(remove_diacritics="0")
        pocket_search = PocketSearch(schema=self.SchemaDiacritics)
        pocket_search.insert(text="äö")
        self.assertEqual(pocket_search.search(text="ao").count(), 0)
        pocket_search.close()

    def test_keep_diacritics(self):
        '''
        Setting remove diacritics to 1 or 2 will keep the diacritics
        '''
        for val in ["1", "2"]:
            self.SchemaDiacritics.Meta.tokenizer = Unicode61(
                remove_diacritics=val)
            pocket_search = PocketSearch(schema=self.SchemaDiacritics)
            pocket_search.insert(text="äö")
            self.assertEqual(pocket_search.search(text="ao").count(), 1)
            pocket_search.close()

    def test_categories(self):
        '''
        Configure the tokenizer in a way that it only considers numbers 
        to be valid tokens
        '''
        self.SchemaDiacritics.Meta.tokenizer = Unicode61(categories="N*")
        pocket_search = PocketSearch(schema=self.SchemaDiacritics)
        pocket_search.insert(text="a b c 1 2 3")

        self.assertEqual(pocket_search.search(text="a").count(), 0)
        self.assertEqual(pocket_search.search(text="b").count(), 0)
        self.assertEqual(pocket_search.search(text="c").count(), 0)
        self.assertEqual(pocket_search.search(text="1").count(), 1)
        self.assertEqual(pocket_search.search(text="2").count(), 1)
        self.assertEqual(pocket_search.search(text="3").count(), 1)
        pocket_search.close()

    def test_add_separator(self):
        '''
        Add the character 'X', 'Y' and 'Z' as additional separator character
        '''
        self.SchemaDiacritics.Meta.tokenizer = Unicode61(separators="XYZ")
        pocket_search = PocketSearch(schema=self.SchemaDiacritics)
        pocket_search.insert(text="aXbXcXd BYZD")
        self.assertEqual(pocket_search.search(text="X").count(), 0)
        self.assertEqual(pocket_search.search(text="a").count(), 1)
        self.assertEqual(pocket_search.search(text="B").count(), 1)
        self.assertEqual(pocket_search.search(text="Y").count(), 0)
        self.assertEqual(pocket_search.search(text="Z").count(), 0)
        self.assertEqual(pocket_search.search(text="D").count(), 1)
        pocket_search.close()

    def test_mix_categories_and_separators(self):
        under_test = "(This)X'is'Ya-toke42nizeZtest."
        self.SchemaDiacritics.Meta.tokenizer = Unicode61(
            categories="N*", separators="4")
        pocket_search = PocketSearch(schema=self.SchemaDiacritics)
        pocket_search.insert(text=under_test)
        # This results in only one token as everything else is considered a separator
        self.assertEqual(len(list(pocket_search.tokens())), 1)
        pocket_search.close()

    def test_token_chars(self):
        '''
        Test additional token chars.
        '''
        under_test = "A more: \\complex ':-)' example for tokenization@test.test (using emoticons.)"
        self.SchemaDiacritics.Meta.tokenizer = Unicode61(tokenchars="@")
        pocket_search = PocketSearch(schema=self.SchemaDiacritics)
        pocket_search.insert(text=under_test)
        self.assertEqual(pocket_search.search(
            text="tokenization@test.test").count(), 1)


class CharacterTest(unittest.TestCase):
    '''
    Tokenization-related tests
    '''

    def setUp(self):
        self.data = [
            "äö",
            "ao",
            "break-even",
            "bleɪd",
            "(bracket)",
            "(bracket )",
            "(bracket]",
            "U.S.A.",
            "I50.1.3",
            "I50 13",
            "ˌrʌnɚ",
            "'x'"
        ]
        self.pocket_search = PocketSearch(writeable=True)
        for elem in self.data:
            self.pocket_search.insert(text=elem)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_hash(self):
        '''
        Test searching for hash symbols.
        '''
        self.assertEqual(self.pocket_search.search(text="#").count(), 0)

    def test_search_hyphen(self):
        '''
        Test search for hyphen symbols. 
        '''
        self.assertEqual(self.pocket_search.search(
            text="break even").count(), 1)
        self.assertEqual(self.pocket_search.search(
            text="break-even").count(), 1)
        self.assertEqual(self.pocket_search.search(
            text="breakeven").count(), 0)

    def test_search_punctuation(self):
        '''
        As punctuation is removed there is no difference between a search for I50. and I50
        '''
        self.assertEqual(self.pocket_search.search(
            text__allow_prefix="I50.*").count(), 2)

    def test_search_special_characters(self):
        '''
        Test default behavior. By default, diacritics are removed from all Latin script characters.
        This means, that a search for äö is equivalent to a search for ao.
        '''
        self.assertEqual(self.pocket_search.search(text="äö").count(), 2)

    def test_search_special_characters2(self):
        '''
        Another test covering search for characters with diacritics
        '''
        self.assertEqual(self.pocket_search.search(text="bleɪd").count(), 1)

    def test_search_brackets(self):
        '''
        Test search for a string that is wrapped in brackets.
        '''
        self.assertEqual(self.pocket_search.search(text="bracket").count(), 3)

    def test_search_punctuation1(self):
        '''
        Test searching for abbrevated terms.
        '''
        self.assertEqual(self.pocket_search.search(text="u s a").count(), 1)

    def test_search_punctuation2(self):
        '''
        The search for USA should fail in this case.
        '''
        self.assertEqual(self.pocket_search.search(text="usa").count(), 0)

    def test_search_punctuation3(self):
        '''
        The search for U.S.A. instead should work.
        '''
        self.assertEqual(self.pocket_search.search(text="u.s.a").count(), 1)

    def test_quoting(self):
        '''
        Quotes should be removed from the tokens, so this should work
        '''
        self.assertEqual(self.pocket_search.search(text="x").count(), 1)


class MultipleFieldRankingtest(unittest.TestCase):

    def setUp(self):
        self.pocket_search = PocketSearch(schema=Page, writeable=True)
        self.data = [
            ("A", "A", "C B C A"),
            ("B", "B", "C C A A"),
            ("C", "A", "A A C C"),
        ]
        self.pocket_search = PocketSearch(schema=Page, writeable=True)
        for title, category, content in self.data:
            self.pocket_search.insert(
                title=title, category=category, text=content)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_rank_multiple_fields_and_query(self):
        self.assertEqual(self.pocket_search.search(
            text="A", title="A", category="A")[0].title, "A")
        # As all fields are AND'ed - this query will show no results
        self.assertEqual(self.pocket_search.search(
            text="C", title="C", category="C").count(), 0)
        # Now order the results by title, this should bring "A" first:
        # results = self.pocket_search.search(text="C",title="C",category="C").order_by("title")
        # self.assertEqual(results[0].title,"A")


class StemmingTests(unittest.TestCase):
    '''
    Stemming tests are currently only here 
    to illustrate that stemming is not supported.
    In future (once PorterStemmer is supported) these 
    tests will be extended.
    '''

    def setUp(self):
        self.data = [
            "Tests need to be performed on a regular basis.",
            "Die Anforderungen müssen genau definiert sein."
        ]
        self.pocket_search = PocketSearch(writeable=True)
        for content in self.data:
            self.pocket_search.insert(text=content)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_search(self):
        # The default behavior: no stemming is performed
        self.assertEqual(self.pocket_search.search(text="test").count(), 0)
        self.assertEqual(self.pocket_search.search(
            text="anforderung").count(), 0)


class MultipleFieldIndexTest(unittest.TestCase):

    def setUp(self):
        # Data taken from Wikipedia (also using some special characters)
        self.data = [
            ("Blade Runner",
             "Blade Runner [bleɪd ˌrʌnɚ], deutscher Verleihtitel zeitweise auch Der Blade Runner, ist ein am 25. Juni 1982 erschienener US-amerikanischer Science-Fiction-Film des Regisseurs Ridley Scott."),
        ]
        self.pocket_search = PocketSearch(schema=Movie, writeable=True)
        for title, content in self.data:
            self.pocket_search.insert(title=title, text=content)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_all_fields_available_in_results(self):
        self.assertEqual(self.pocket_search.search(
            text="ˌrʌnɚ")[0].title, "Blade Runner")

    def test_set_values_in_results(self):
        self.assertEqual(self.pocket_search.search(
            text="ˌrʌnɚ").values("title")[0].title, "Blade Runner")

    def test_set_non_existing_field_in_results(self):
        with (self.assertRaises(Schema.SchemaError)):
            self.assertEqual(self.pocket_search.search(text="ˌrʌnɚ").values(
                "title323232")[0].title, "Blade Runner")

    def test_set_illegal_order_by(self):
        with (self.assertRaises(Schema.SchemaError)):
            self.assertEqual(self.pocket_search.search(text="ˌrʌnɚ").order_by(
                "title323232")[0].title, "Blade Runner")

    def test_search_movie(self):
        self.assertEqual(self.pocket_search.search(text="Blade").count(), 1)
        self.assertEqual(self.pocket_search.search(title="runner").count(), 1)

    def test_combined_field_search(self):
        self.assertEqual(self.pocket_search.search(
            text="Blade", title="runner").count(), 1)


class FieldTypeTests(unittest.TestCase):

    class AllFields(Schema):

        # implicitly tests if non-fts index generation work
        f1 = Int(index=True)
        f2 = Text(index=True)
        f3 = Blob()
        f4 = Real()
        f5 = Datetime()
        f6 = Date()

    def setUp(self):
        self.pocket_search = PocketSearch(schema=self.AllFields)
        self.pocket_search.insert(f1=32,
                                  f2='text',
                                  f3='abc'.encode("utf-8"),
                                  f4=2/3,
                                  f5=datetime.datetime.now(),
                                  f6=datetime.date.today())

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_apply_highlight_to_non_fts_field(self):
        '''
        When the highlight function is applied to non-FTS
        field, a query error should be raised:
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(f1=32).highlight("f1")
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(f1=32).highlight("f3")
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(f1=32).highlight("f4")
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(f1=32).highlight("f5")
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(f1=32).highlight("f6")

    def test_create(self):
        result = self.pocket_search.search(id=1)
        self.assertEqual(type(result[0].f6), datetime.date)
        # search for dates

    def test_search_dates_equals(self):
        year = datetime.date.today().year
        month = datetime.date.today().month
        day = datetime.date.today().day
        eq = self.assertEqual
        eq(self.pocket_search.search(f6__year=year).count(), 1)
        eq(self.pocket_search.search(f6__month=month).count(), 1)
        eq(self.pocket_search.search(f6__day=day).count(), 1)

    def test_search_dates_range(self):
        year = datetime.date.today().year
        month = datetime.date.today().month
        day = datetime.date.today().day
        self.assertEqual(self.pocket_search.search(
            f6__year__gte=year-1, f6__year__lte=year+1).count(), 1)


class StructuredDataTests(unittest.TestCase):

    class Product(Schema):

        price = Int()
        description = Text(index=True)
        category = Text()  # not part of FT index

    def setUp(self):
        self.pocket_search = PocketSearch(schema=self.Product)
        for product, price, category in [
            ("Apple", 3, "Fruit"),
            ("Orange", 4, "Fruit"),
            ("Peach", 5, "Fruit"),
            ("Banana", 6, "Fruit"),
        ]:
            self.pocket_search.insert(
                description=product, price=price, category=category)

    def tearDown(self):
        self.pocket_search.close()
        return super().tearDown()

    def test_filter_numeric_values_equal(self):
        self.assertEqual(self.pocket_search.search(price=3).count(), 1)

    def test_filter_numeric_values_greater_than(self):
        self.assertEqual(self.pocket_search.search(price__gt=3).count(), 3)

    def test_filter_numeric_values_greater_than_equal(self):
        self.assertEqual(self.pocket_search.search(price__gte=3).count(), 4)

    def test_filter_numeric_values_lesser_than(self):
        self.assertEqual(self.pocket_search.search(price__lt=3).count(), 0)

    def test_filter_numeric_values_lesser_than_equal(self):
        self.assertEqual(self.pocket_search.search(price__lte=3).count(), 1)

    def test_search_category(self):
        # This will lead to a standard "equal" search not invoking FTS
        self.assertEqual(self.pocket_search.search(
            category="Fruit").count(), 4)

    def test_search_category_operators(self):
        # Should work, as sqlite3 allows this:
        self.assertEqual(self.pocket_search.search(
            category__lte="Fruit").count(), 4)

    def test_filter_combined(self):
        self.assertEqual(self.pocket_search.search(
            price__lte=3, description="apple").count(), 1)

    def test_price_range(self):
        self.assertEqual(self.pocket_search.search(
            price__lt=6, price__gt=4).count(), 1)

    def test_filter_combined_and_or(self):
        self.assertEqual(self.pocket_search.search(
            price__lte=4, description__allow_boolean="apple OR Orange").count(), 2)


class FileSystemReaderTests(unittest.TestCase):

    class FileSchema(Schema):

        text = Text(index=True)
        filename = Text(is_id_field=True)

    def test_build_index(self):
        self.files_to_index = []
        with tempfile.TemporaryDirectory() as tmpdirname:
            for file_name, contents in [
                ("a.txt", "Hello world !"),
                ("b.txt", "Good bye world !"),
                ("c.txt", "Hello again, world !"),
            ]:
                f = open(os.path.join(tmpdirname, file_name),
                         "w", encoding="utf-8")
                f.write(contents)
                f.close()
            pocket_search = PocketSearch(schema=self.FileSchema)
            reader = FileSystemReader(
                base_dir=tmpdirname, file_extensions=[".txt"])
            pocket_search.build(reader)
            self.assertEqual(pocket_search.search(text="world").count(), 3)
            self.assertEqual(pocket_search.search(text="bye").count(), 1)
            self.assertEqual(pocket_search.search(filename="d.txt").count(), 0)
            # rebuild the index, the number of documents should not
            # change as they have only been updated
            pocket_search.build(reader)
            self.assertEqual(pocket_search.search(text="world").count(), 3)
            pocket_search.close()


class SpellCheckerTest(unittest.TestCase):
    '''
    Tests for spell checking class
    '''

    class TestSchema(Schema):
        '''
        Test schema supporting spell checking
        '''

        class Meta:
            spell_check = True

        title = Text(index=True)
        text = Text(index=True)

    def test_suggest_spell_check_not_enabled(self):
        '''
        A QueryError should be raised if someone 
        tries to access spell checking when they 
        have not been enabled in schema.
        '''
        p = PocketSearch()
        with self.assertRaises(Query.QueryError):
            p.suggest("test")
        p.close()

    def test_suggest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.db_name = temp_dir + os.sep + "test.db"
            with PocketWriter(db_name=self.db_name, schema=self.TestSchema) as pocketwriter:
                for title, text in [
                    ("Blade Runner", "Written in 1982"),
                    ("Indiana Jones 1", "Written in the eighties"),
                    ("Indiana Jones 2", "Again in the eighties"),
                    ("Hello", "World")
                ]:
                    pocketwriter.insert(title=title, text=text)
                pocketwriter.spell_checker().build()
            with PocketReader(db_name=self.db_name, schema=self.TestSchema) as pocketreader:
                results = pocketreader.suggest(
                    "' lInddjiana agn jin th?i _writen& eigh  ")
                expected = {'agn': [('again', 2)],
                            'eigh': [('eighties', 4)],
                            'jin': [('in', 1), ('again', 3), ('indiana', 5)],
                            'lInddjiana': [('indiana', 4), ('in', 8), ('again', 8)],
                            'th': [('the', 1)],
                            'writen': [('written', 1)]}
                for token, suggestions in results.items():
                    self.assertEqual(token in expected, True)
                    # self.assertEqual(expected[token]==suggestions[token],True)
                # some edge cases
                self.assertEqual(len(pocketreader.suggest("")), 0)
                self.assertEqual(len(pocketreader.suggest("!?.*")), 0)
                # this will be ignored (only one character):
                self.assertEqual(len(pocketreader.suggest("h")), 0)
                # test standard search
                pocketreader.search(title="blade")[0].text


class SchemaUpdateTests(unittest.TestCase):
    '''
    Tests for updating a schema
    '''

    class Article(Schema):
        '''
        Base schema
        '''
        body = Text(index=True)

    class NewArticle(Schema):
        '''
        One field added
        '''
        title = Text(index=True)
        body = Text(index=True)

    def test_change_schema(self):
        '''
        Test schema migration
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            with PocketWriter(db_name=db_name, schema=self.Article) as writer:
                writer.insert(body="A")
                writer.insert(body="B")
            with PocketReader(db_name=db_name, schema=self.Article) as reader:
                with PocketWriter(db_name=db_name, index_name="document_v2", schema=self.NewArticle) as writer:
                    for article in reader.search():
                        writer.insert(title='some default', body=article.body)
            with PocketReader(index_name="document_v2", db_name=db_name, schema=self.NewArticle) as reader:
                self.assertEqual(reader.search(
                    title="some default").count(), 2)


class CustomIDFieldTest(unittest.TestCase):
    '''
    Tests for custom ID fields
    '''

    class CustomIDSchema(Schema):
        '''
        Simple schema that uses its own id field
        '''

        content_id = IdField()
        text = Text(index=True)

    def test_custom_id(self):
        '''
        Test if inserts, updates and deletes work with custom ids
        '''
        p = PocketSearch(schema=self.CustomIDSchema)
        p.insert(text="Test")
        self.assertEqual(p.search(text="Test").count(), 1)
        self.assertEqual(p.search(text="Test")[0].content_id, 1)
        p.update(rowid=1, text="Updated text")
        self.assertEqual(p.search(text="Test").count(), 0)
        self.assertEqual(p.search(text="Updated text").count(), 1)
        p.delete(rowid=1)
        self.assertEqual(p.search(text="Updated text").count(), 0)
        p.close()


class LegacyTableTest(unittest.TestCase):
    '''
    Tests for creating indices on an already existing table
    '''

    class LegacyTableSchema(Schema):
        '''
        Schema for the search index. Must correspond to 
        the definition of the legacy table
        '''

        class Meta:
            spell_check = True

        title = Text(index=True)
        body = Text(index=True)
        length = Real()

    class LegacyTableSchemaMissingField(Schema):

        title2 = Text(index=True)

    def _create_database(self, db_name):
        conn = sqlite3.connect(db_name)
        print(db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE document (
                body TEXT,                       
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                length float
                
            )
        ''')
        cursor.execute('''
            CREATE TABLE no_id_field (
                body TEXT,                       
                title TEXT,
                length float
                
            )
        ''')
        cursor.execute('''
                INSERT INTO document (title, body) VALUES (?, ?)
            ''', ("My title", "My content"))
        cursor.execute('''
                INSERT INTO document (title, body) VALUES (?, ?)
            ''', ("My title2", "test"))
        conn.commit()
        conn.close()

    def test_no_id_legacy_table(self):
        '''
        Test exception, if a field in the 
        schema definition but is missing in the 
        legacy table definition
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir+os.sep+"test.db"
            # Create table manually
            self._create_database(db_name)
            with self.assertRaises(PocketSearch.DatabaseError):
                PocketSearch(index_name="no_id_field", db_name=db_name,
                             schema=self.LegacyTableSchemaMissingField, writeable=True)

    def test_unknown_field_legacy_table(self):
        '''
        Test exception, if a field in the 
        schema definition but is missing in the 
        legacy table definition
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir+os.sep+"test.db"
            # Create table manually
            self._create_database(db_name)
            with self.assertRaises(PocketSearch.DatabaseError):
                PocketSearch(index_name="document", db_name=db_name,
                             schema=self.LegacyTableSchemaMissingField, writeable=True)

    def test_legacy_table(self):
        '''
        Creates table in a legacy.db, we then try to create 
        a full text search index around this table.
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir+os.sep+"test.db"
            # Create table manually
            self._create_database(db_name)
            with PocketWriter(index_name="document", db_name=db_name, schema=self.LegacyTableSchema) as writer:
                writer.spell_checker().build()
            with PocketReader(index_name="document", db_name=db_name, schema=self.LegacyTableSchema) as reader:
                record = reader.search(body="test")[0]
                self.assertEqual(record.id, 2)
                record = reader.search(body="My content")[0]
                self.assertEqual(record.id, 1)
                # Test spell checking:
                results = reader.suggest("cntent")
                self.assertEqual(results["cntent"][0][0], "content")
            with PocketWriter(index_name="document", db_name=db_name, schema=self.LegacyTableSchema) as writer:
                # Now try inserting data the regular way:
                writer.insert(body="a", title="b", length=1)
                self.assertEqual(writer.search(title="my title").count(), 1)
                self.assertEqual(writer.search(title="b").count(), 1)


class ConnectionPoolTest(unittest.TestCase):
    '''
    Test con-current access to writeable connections
    '''

    def setUp(self):
        connection_pool.connections.clear()

    def test_multiple_in_memory_databases(self):
        '''
        It should be possible to open 3 pocketsearch 
        objects in memory that should not interfere 
        with each other
        '''
        p1 = PocketSearch()
        p1.insert(text="p1")
        p2 = PocketSearch()
        p2.insert(text="p2")
        p3 = PocketSearch()
        p3.insert(text="p3")
        p3.insert(text="p3")
        self.assertEqual(p1.search().count(), 1)
        self.assertEqual(p2.search().count(), 1)
        self.assertEqual(p3.search().count(), 2)
        p1.close()
        p2.close()
        p3.close()

    def test_no_connection_available(self):
        '''
        We use two PocketSearch instances with the first one 
        not having closed its connection. Thus, the second 
        instance should return an connection error
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            p1 = PocketSearch(db_name=db_name, writeable=True)
            p1.insert(text="a")
            with self.assertRaises(ConnectionPool.ConnectionError):
                PocketSearch(db_name=db_name, writeable=True)

    def test_connection_available(self):
        '''
        In this test, the first instance properly closes the 
        connection and the second instance can access the database
        '''
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            p1 = PocketSearch(db_name=db_name, writeable=True)
            p1.insert(text="a")
            p1.close()
            p2 = PocketSearch(db_name=db_name, writeable=True)
            p2.insert(text="b")
            p2.close()


class TestConcurrentWrites(unittest.TestCase):
    '''
    This test runs NUM_THREADS concurrent threads and performs 
    a number of inserts given in the NUM_INSERTS variables. 
    It is tested, if the thread writing to the database gets 
    an exclusive lock for the write operations.
    '''

    NUM_THREADS = 32
    NUM_INSERTS = 64

    def write_data(self, data, db_name):
        '''
        Write dummy data to database
        '''
        with PocketWriter(db_name=db_name) as writer:
            for i in range(0, self.NUM_INSERTS):
                writer.insert(text=data + str(i))

    def test_concurrent_writes(self):
        # Start two threads to perform concurrent writes
        threads = []
        with tempfile.TemporaryDirectory() as temp_dir:
            db_name = temp_dir + os.sep + "test.db"
            for i in range(0, self.NUM_THREADS):
                thread = threading.Thread(target=self.write_data, args=(
                    "Writing data from Thread %i " % i, db_name))
                threads.append(thread)
                thread.start()

            # Wait for all threads to finish
            for thread in threads:
                thread.join()
            p = PocketSearch(db_name=db_name)
            self.assertEqual(p.search().count(),
                             self.NUM_THREADS*self.NUM_INSERTS)


if __name__ == '__main__':
    unittest.main()
