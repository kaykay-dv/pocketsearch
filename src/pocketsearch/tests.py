'''
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE FOR ANY DAMAGES OR OTHER LIABILITY,
WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sys
import os.path
import unittest
import tempfile
import datetime
import logging

from pocketsearch import FileSystemReader, Text, PocketSearch, Schema, Query, Field, Int, Real, Blob, Date, Datetime, Q

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
    pass

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
        schema = SchemaCustomField(name="broken")
        with self.assertRaises(Schema.SchemaError):
            schema.custom_field.to_sql()

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
        self.pocket_search = PocketSearch(index_name="text_data",writeable=True)
        for elem in self.data:
            self.pocket_search.insert(text=elem)

class SQLFunctionTests(BaseTest):

    def test_highlight(self):
        self.assertEqual("*fox*" in self.pocket_search.search(text="fox").highlight("text")[0].text,True)

    def test_highlight_alternative_marker(self):
        self.assertEqual("<b>fox</b>" in self.pocket_search.search(text="fox").highlight("text",marker_start="<b>",marker_end="</b>")[0].text,True)

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
        result = self.pocket_search.search(text="forward index").snippet("text")[0].text
        eq = self.assertEqual
        eq("*forward*" in result,True)
        eq("*index*" in result,True)
        # Test alternative before/after text
        result = self.pocket_search.search(text="forward index").snippet("text",text_before="<b>",text_after="</b>")[0].text
        eq("<b>forward</b>" in result , True)
        eq("<b>index</b>" in result , True)

    def test_snippet_length_too_big(self):
        '''
        Snippets may not exceed 64 tokens
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="forward index").snippet("text",snippet_length=128)

    def test_snippet_length_too_small(self):
        '''
        Snippets must have at least 1 token
        '''        
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="forward index").snippet("text",snippet_length=0)        

class OperatorSearch(BaseTest):
    '''
    Tests covering the usage of boolean operators and prefix search
    '''

    def test_search_len_func(self):
        # test application of len function to search result
        self.assertEqual(len(self.pocket_search.search(text="france")[0:1]), 1)

    def test_search_prefix(self):
        # by default, prefix search is not supported:
        self.assertEqual(self.pocket_search.search(text="fran*").count(), 0)

    def test_search_prefix_explicit(self):
        # by default, prefix search is not supported:
        self.assertEqual(self.pocket_search.search(text__allow_prefix="fran*").count(), 1)

    def test_initial_token_queries_implicit(self):
        self.pocket_search.insert(text="Paris is not the capital of england.")
        # in this case, the ^ operator will be ignored and 2 matches found:
        self.assertEqual(self.pocket_search.search(text="^england").count(), 2)

    def test_initial_token_queries_explicit(self):
        self.pocket_search.insert(text="Paris is not the capital of england.")
        # search for results where england can be found at the begining:
        self.assertEqual(self.pocket_search.search(text__allow_initial_token="^england").count(), 1)
        self.assertEqual(self.pocket_search.search(text__allow_initial_token__allow_prefix="^engl*").count(),1)

    def test_search_and_or_query_default(self):
        # by default, AND/OR queries are not supported:
        self.assertEqual(self.pocket_search.search(text='france AND paris').count(), 0)
        self.assertEqual(self.pocket_search.search(text='france OR paris').count(), 0)

    def test_near_query(self):
        # NEAR queries are not supported at the moment
        self.assertEqual(self.pocket_search.search(text='NEAR(one, two)').count(),0) 

    def test_combined_lookups(self):
        self.assertEqual(self.pocket_search.search(text__allow_boolean__allow_prefix='france OR engl*').count(), 2)

    def test_search_and_or_query_explicit(self):
        # Allow AND + OR
        self.assertEqual(self.pocket_search.search(text__allow_boolean='france AND paris').count(), 1)
        self.assertEqual(self.pocket_search.search(text__allow_boolean='france OR paris').count(), 1)
        self.assertEqual(self.pocket_search.search(text__allow_boolean='france OR england OR fence').count(), 3)

    def test_negation_default(self):
        # By default, negation is not supported
        self.assertEqual(self.pocket_search.search(text="NOT france").count(), 0)

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
            prefix_index=[2,3,4]
        body = Text(index=True)

    class PrefixIndex2(Schema):
        '''
        Prefix index definition with negative numbers
        '''
        class Meta:
            prefix_index=[2,-3,4]
        body = Text(index=True)

    class PrefixIndex3(Schema):
        '''
        Prefix index definition, wrong data type
        '''
        class Meta:
            prefix_index="2,3,4"

        body = Text(index=True)

    class PrefixIndex4(Schema):
        '''
        Prefix index definition with duplicate values
        '''
        class Meta:
            prefix_index=[2,2,4]
        body = Text(index=True)        

    class PrefixIndex5(Schema):
        '''
        Prefix index definition with duplicate values
        '''
        class Meta:
            prefix_index=[0,1]
        body = Text(index=True)  

    class PrefixIndex6(Schema):
        '''
        Prefix index definition with non-integer values
        '''
        class Meta:
            prefix_index=["0",1]
        body = Text(index=True) 

    def test_create_prefix_index(self):
        '''
        Test creation of prefix index
        '''
        PocketSearch(schema=self.PrefixIndex1)
        with self.assertRaises(Schema.SchemaError):
            PocketSearch(schema=self.PrefixIndex2)
        with self.assertRaises(Schema.SchemaError):            
            PocketSearch(schema=self.PrefixIndex3)
        PocketSearch(schema=self.PrefixIndex4)
        with self.assertRaises(Schema.SchemaError):
            PocketSearch(schema=self.PrefixIndex6)

class PhraseSearch(unittest.TestCase):

    def test_search_phrase(self):
        pocket_search = PocketSearch(writeable=True)
        pocket_search.insert(text="This is a phrase")
        pocket_search.insert(text="a phrase this is")
        self.assertEqual(pocket_search.search(text="This is a phrase").count(), 2)
        self.assertEqual(pocket_search.search(text="this phrase a is").count(), 2)
        self.assertEqual(pocket_search.search(text='"this is a phrase"').count(), 1)

    def test_multiple_phrases(self):
        pocket_search = PocketSearch(writeable=True)
        pocket_search.insert(text="This is a phrase")
        self.assertEqual(pocket_search.search(text='"this is" "a phrase"').count(), 1)
        self.assertEqual(pocket_search.search(text='"this is" "phrase a"').count(), 0)


class IndexTest(BaseTest):

    def test_write_to_read_only_index(self):
        pocket_search = PocketSearch(writeable=False)
        pocket_search.writeable = False  # in.memory dbs are writeable by default so we set the flag manually
        with self.assertRaises(pocket_search.IndexError):
            pocket_search.insert(text="21")

    def test_optimize_within_tranascation(self):
        pocket_search = PocketSearch()
        pocket_search.insert(text="123")        
        pocket_search.commit()
        #with self.assertRaises(Exception):
        # this should not work, as vacuum is not allowed at this stage
        pocket_search.optimize()


    def test_use_insert_update_with_lookups(self):
        pocket_search = PocketSearch()
        with self.assertRaises(pocket_search.FieldError):
            pocket_search.insert(text__allow_boolean="123")
        pocket_search.insert(text="123")
        with self.assertRaises(pocket_search.FieldError):
            pocket_search.update(rowid=1, text__allow_boolean="The DOG jumped over the fence. Now he is beyond the fence.")

    def test_unknown_field(self):
        pocket_search = PocketSearch(writeable=True)
        with self.assertRaises(pocket_search.FieldError):
            pocket_search.insert(non_existing_field_in_schema="21")

    def test_count(self):
        self.assertEqual(self.pocket_search.search(text="is").count(), 3)
        self.assertEqual(self.pocket_search.search(text="notinindex").count(), 0)

    def test_indexing(self):
        self.assertEqual(self.pocket_search.search(text="fence")[0].text, self.data[0])
        self.assertEqual(self.pocket_search.search(text="is")[0].text, self.data[1])

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
        r = self.pocket_search.search(text="is").values("id", "rank", "text").order_by("-text")
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
        for code,name,price in [
            ("A01","Apple",4),
            ("A02","Peach",7),
            ("A03","Orange",8),
            ("B01","Grapefruit",5),
            ("B02","Banana",9),
            ("C01","Apple and Orange",3),            
        ]:
            self.pocketsearch.insert(code=code,product=name,price=price)

    def test_deprecated_union_search(self):
        # FIXME: test if log message is actually written
        self.pocketsearch.search(product="apple") | self.pocketsearch.search(product="peach")


    def test_or_same_keyword(self):
        q = self.pocketsearch.search(Q(product='apple') | Q(product='Peach'))
        self.assertEqual(q.count(),3)

    def test_phrase_query(self):
        q = self.pocketsearch.search(Q(product='"apple and orange"'))
        self.assertEqual(q.count(),1)        
        q = self.pocketsearch.search(Q(product='orange and apple'))
        self.assertEqual(q.count(),1)        

    def test_initial_token_query(self):
        # This should only bring one result back:
        q = self.pocketsearch.search(Q(price__gte=3) & Q(product__allow_initial_token="^Orange"))
        self.assertEqual(q.count(),1)

    def test_and(self):
        q = self.pocketsearch.search(Q(product="Apple") & Q(code__allow_prefix="A*") & Q(price__gte=2))
        self.assertEqual(q.count(),1)
        # Test the other way around:
        q = self.pocketsearch.search(Q(price__gte=2) & Q(product="Apple") & Q(code__allow_prefix="A*"))
        self.assertEqual(q.count(),1)        
        # Mixed
        q = self.pocketsearch.search(Q(code__allow_prefix="A*") & Q(price__gte=2) & Q(product="Apple"))
        self.assertEqual(q.count(),1) 

    def test_or(self):
        q = self.pocketsearch.search(Q(price__gte=9) | Q(price__lte=3)) 
        self.assertEqual(q.count(),2)

    def test_combined_and_or(self):
        q = self.pocketsearch.search(Q(price__gte=1) & Q(price__lte=5) & Q(product="Apple") | Q(product="Orange"))
        self.assertEqual(q.count(),2)

    def test_mixed_q_query(self):
        with self.assertRaises(Query.QueryError):
            self.pocketsearch.search(Q(price__gte=1) & Q(price__lte=5), product="apple")

    def test_q_objects_multiple_kw_arguments(self):
        with self.assertRaises(Query.QueryError):
            self.pocketsearch.search(Q(price__gte=1,price__lte=5))

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

    def test_get_entry(self):
        document = self.pocket_search.get(rowid=1)
        self.assertEqual(document.id, 1)

    def test_get_non_existing_entry(self):
        with self.assertRaises(self.pocket_search.DocumentDoesNotExist):
            self.pocket_search.get(rowid=1000)

    def test_delete_entry(self):
        self.pocket_search.delete(rowid=1)
        # Entry if "fox" should have disappeared:
        self.assertEqual(self.pocket_search.search(text="fox").count(), 0)

    def test_update_entry(self):
        self.pocket_search.update(rowid=1, text="The DOG jumped over the fence. Now he is beyond the fence.")
        self.assertEqual(self.pocket_search.search(text="fox").count(), 0)
        self.assertEqual(self.pocket_search.search(text="dog").count(), 1)
        self.assertEqual(self.pocket_search.search().count(), 3)

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

    def test_autocomplete_multiple_keywords(self):
        '''
        Multiple keywords are not allowed
        '''
        with self.assertRaises(Query.QueryError):
            self.pocket_search.autocomplete(text="Ind",title="Ind")

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
        self.assertEqual(self.pocket_search.autocomplete().count(),4)

    def test_autocomplete_one_token(self):
        '''
        Both autocomplete queries should bring "Indiana Jones" as first result,
        as "Indiana" is at the beginning of the column, "Jones Indiana" should 
        come second.
        '''
        self.assertEqual(self.pocket_search.autocomplete(text="In")[0].text,"Indiana Jones")
        self.assertEqual(self.pocket_search.autocomplete(text="In")[1].text,"Jones Indiana")
        self.assertEqual(self.pocket_search.autocomplete(text="Ind")[0].text,"Indiana Jones")
        self.assertEqual(self.pocket_search.autocomplete(text="In")[1].text,"Jones Indiana")

    def test_order_by(self):
        '''
        Test, if order by can be applied to autocomplete.
        This should bring Jones Indiana as first result, as we sort by -rank
        '''
        self.assertEqual(self.pocket_search.autocomplete(text="In").order_by("-rank")[0].text,"Jones Indiana")

    def test_autocomplete_two_tokens(self):
        '''
        Test autocomplete with 2 tokens
        '''        
        self.assertEqual(self.pocket_search.autocomplete(text="Indiana J")[0].text,"Indiana Jones")

    def test_autocomplete_including_and_or_operators(self):
        '''
        AND/OR keywords cannot be used in autocomplete:
        '''
        self.assertEqual(self.pocket_search.autocomplete(text="INDIANA OR JONES").count(),0)
        self.assertEqual(self.pocket_search.autocomplete(text="INDIANA AND JONES").count(),0)

    def test_autocomplete_three_tokens(self):
        '''
        Test autocomplete with 3 tokens
        '''
        self.assertEqual(self.pocket_search.autocomplete(text="return of the")[0].text,"The return of the Jedi")

    def test_special_characters_in_query(self):
        '''
        Test if quoting, works. Special characters are not allowed 
        in autocomplete queries
        '''
        self.assertEqual(self.pocket_search.autocomplete(1,text="*").count(),0)

class CharacterTest(unittest.TestCase):

    def setUp(self):
        self.data = [
            "äö",
            "break-even",
            "bleɪd",
            "(bracket)",
            "(bracket )",
            "(bracket]",
            "U.S.A.",
            "ˌrʌnɚ",
            "'x'"
        ]
        self.pocket_search = PocketSearch(writeable=True)
        for elem in self.data:
            self.pocket_search.insert(text=elem)

    def test_hash(self):
        self.assertEqual(self.pocket_search.search(text="#").count(), 0)

    def test_search_hyphen(self):
        self.assertEqual(self.pocket_search.search(text="break even").count(), 1)
        self.assertEqual(self.pocket_search.search(text="break-even").count(), 1)
        self.assertEqual(self.pocket_search.search(text="breakeven").count(), 0)

    def test_search_special_characters(self):
        self.assertEqual(self.pocket_search.search(text="äö").count(), 1)

    def test_search_special_characters2(self):
        self.assertEqual(self.pocket_search.search(text="bleɪd").count(), 1)

    def test_search_brackets(self):
        self.assertEqual(self.pocket_search.search(text="bracket").count(), 3)

    def test_search_punctuation1(self):
        self.assertEqual(self.pocket_search.search(text="u s a").count(), 1)

    def test_search_punctuation2(self):
        self.assertEqual(self.pocket_search.search(text="usa").count(), 0)

    def test_search_punctuation3(self):
        self.assertEqual(self.pocket_search.search(text="u.s.a").count(), 1)

    def test_quoting(self):
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
            self.pocket_search.insert(title=title, category=category, text=content)

    def test_rank_multiple_fields_and_query(self):
        self.assertEqual(self.pocket_search.search(text="A", title="A", category="A")[0].title, "A")
        # As all fields are AND'ed - this query will show no results
        self.assertEqual(self.pocket_search.search(text="C", title="C", category="C").count(), 0)
        # Now order the results by title, this should bring "A" first:
        #results = self.pocket_search.search(text="C",title="C",category="C").order_by("title")
        # self.assertEqual(results[0].title,"A")


class StemmingTests(unittest.TestCase):

    def setUp(self):
        self.data = [
            "Tests need to be performed on a regular basis.",
            "Die Anforderungen müssen genau definiert sein."
        ]
        self.pocket_search = PocketSearch(writeable=True)
        for content in self.data:
            self.pocket_search.insert(text=content)

    def test_search(self):
        # The default behavior: no stemming is performed
        self.assertEqual(self.pocket_search.search(text="test").count(), 0)
        self.assertEqual(self.pocket_search.search(text="anforderung").count(), 0)


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

    def test_all_fields_available_in_results(self):
        self.assertEqual(self.pocket_search.search(text="ˌrʌnɚ")[0].title, "Blade Runner")

    def test_set_values_in_results(self):
        self.assertEqual(self.pocket_search.search(text="ˌrʌnɚ").values("title")[0].title, "Blade Runner")

    def test_set_non_existing_field_in_results(self):
        with(self.assertRaises(Schema.SchemaError)):
            self.assertEqual(self.pocket_search.search(text="ˌrʌnɚ").values("title323232")[0].title, "Blade Runner")

    def test_set_illegal_order_by(self):
        with(self.assertRaises(Schema.SchemaError)):
            self.assertEqual(self.pocket_search.search(text="ˌrʌnɚ").order_by("title323232")[0].title, "Blade Runner")

    def test_search_movie(self):
        self.assertEqual(self.pocket_search.search(text="Blade").count(), 1)
        self.assertEqual(self.pocket_search.search(title="runner").count(), 1)

    def test_combined_field_search(self):
        self.assertEqual(self.pocket_search.search(text="Blade", title="runner").count(), 1)


class FieldTypeTests(unittest.TestCase):

    class AllFields(Schema):

        f1 = Int(index=True) # implicitly tests if non-fts index generation work
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
        self.assertEqual(self.pocket_search.search(f6__year__gte=year-1, f6__year__lte=year+1).count(), 1)


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
            self.pocket_search.insert(description=product, price=price, category=category)


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
        self.assertEqual(self.pocket_search.search(category="Fruit").count(), 4)

    def test_search_category_operators(self):
        # Should work, as sqlite3 allows this:
        self.assertEqual(self.pocket_search.search(category__lte="Fruit").count(), 4)

    def test_filter_combined(self):
        self.assertEqual(self.pocket_search.search(price__lte=3, description="apple").count(), 1)

    def test_price_range(self):
        self.assertEqual(self.pocket_search.search(price__lt=6, price__gt=4).count(), 1)

    def test_filter_combined_and_or(self):
        self.assertEqual(self.pocket_search.search(price__lte=4, description__allow_boolean="apple OR Orange").count(), 2)


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
                f = open(os.path.join(tmpdirname, file_name), "w", encoding="utf-8")
                f.write(contents)
                f.close()
            pocket_search = PocketSearch(schema=self.FileSchema)
            reader = FileSystemReader(base_dir=tmpdirname, file_extensions=[".txt"])
            pocket_search.build(reader)
            self.assertEqual(pocket_search.search(text="world").count(), 3)
            self.assertEqual(pocket_search.search(text="bye").count(), 1)
            self.assertEqual(pocket_search.search(filename="d.txt").count(), 0)
            # rebuild the index, the number of documents should not
            # change as they have only been updated
            pocket_search.build(reader)
            self.assertEqual(pocket_search.search(text="world").count(), 3)


if __name__ == '__main__':
    unittest.main()
