import os.path
import unittest
import tempfile
import datetime

from pocketsearch import FileSystemIndex, Text, PocketSearch, Schema, Query, Field, Int, Real, Blob, Date, Datetime, IdField


class Movie(Schema):
    '''
    A simple movie schema we use for tests.
    '''

    title = Text(index=True)
    text = Text(index=True)


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


class SchemaTest(unittest.TestCase):
    '''
    Tests for schema generation
    '''

    def test_create_schema(self):
        schema = Movie(name="movie")
        for field in ["title", "text"]:
            self.assertEqual(field in schema.fields, True)

    def test_use_underscores_in_fields(self):
        with self.assertRaises(Schema.SchemaError):
            BrokenSchemaUnderscores(name="broken")

    def test_use_reserved_keywords(self):
        with self.assertRaises(Schema.SchemaError):
            BrokenSchema(name="broken")


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


class OperatorSearch(BaseTest):
    '''
    Tests covering the usage of boolean operators and prefix search
    '''

    def test_search_prefix(self):
        # by default, prefix search is not supported:
        self.assertEqual(self.pocket_search.search(text="fran*").count(), 0)

    def test_search_prefix_explicit(self):
        # by default, prefix search is not supported:
        self.assertEqual(self.pocket_search.search(text__allow_prefix="fran*").count(), 1)

    def test_search_and_or_query_default(self):
        # by default, AND/OR queries are not supported:
        self.assertEqual(self.pocket_search.search(text='france AND paris').count(), 0)
        self.assertEqual(self.pocket_search.search(text='france OR paris').count(), 0)

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

    def test_combine_search_results_illegal_calls(self):
        '''
        These are all invalid queries. When we perform
        a union order by or value arguments cannot be
        provided.
        '''
        with self.assertRaises(Query.QueryError):
            q1 = self.pocket_search.search(text="paris") | self.pocket_search.search(text="england").order_by("rank")
        with self.assertRaises(Query.QueryError):
            q1 = self.pocket_search.search(text="paris").order_by("rank") | self.pocket_search.search(text="england")
        with self.assertRaises(Query.QueryError):
            self.pocket_search.search(text="paris").values("id") | self.pocket_search.search(text="paris").values("id")

    def test_combine_search_results(self):
        # This is a correct query:
        q1 = self.pocket_search.search(text="paris") | self.pocket_search.search(text="england")
        self.assertEqual(q1.count(), 2)

    def test_order_by(self):
        r = self.pocket_search.search(text="is").values("id", "rank", "text").order_by("-text")
        self.assertEqual(r[0].text, self.data[0])
        self.assertEqual(r[1].text, self.data[2])
        self.assertEqual(r[2].text, self.data[1])


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

    def test_rank_multiple_field_or_query(self):
        pass


class StemmingTests(unittest.TestCase):

    def setUp(self):
        # Data taken from Wikipedia (also using some special characters)
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

        f1 = Int()
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

    def test_build_index(self):
        self.files_to_index = []
        with tempfile.TemporaryDirectory() as tmpdirname:
            for file_name, contents in [
                ("a.txt", "Hello world !"),
                ("b.txt", "Good bye world !"),
                ("c.txt", "Hello again, world !"),
            ]:
                f = open(os.path.join(tmpdirname, file_name), "w")
                f.write(contents)
                f.close()
            index = FileSystemIndex(base_dir=tmpdirname, file_extensions=[".txt"])
            index.build()
            self.assertEqual(index.search(text="world").count(), 3)
            self.assertEqual(index.search(text="bye").count(), 1)
            self.assertEqual(index.search(filename="d.txt").count(), 0)
            # rebuild the index, the number of documents should not
            # change as they have only been updated
            index.build()
            self.assertEqual(index.search(text="world").count(), 3)


if __name__ == '__main__':
    unittest.main()
