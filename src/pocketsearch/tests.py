import unittest

import index
import schema

class Movie(schema.Schema):

    title = schema.Field()
    content = schema.Field()

class BrokenSchema(schema.Schema):

    select = schema.Field()

class SchemaTest(unittest.TestCase):

    def test_create_schema(self):
        schema = Movie()
        for field in ["title","content"]:
            self.assertEqual(field in schema.fields,True)

    def test_use_reserved_keywords(self):
        with self.assertRaises(schema.Schema.SchemaError):
            BrokenSchema()

class BaseTest(unittest.TestCase):

    def setUp(self):
        self.data = [
            "The fox jumped over the fence. Now he is beyond the fence.",
            "England is in Europe.",            
            "Paris is the captial of france.",
        ]
        self.pocket_search = index.PocketSearch(writeable=True)
        for elem in self.data:
            self.pocket_search.insert(content=elem) 

class IndexTest(BaseTest):

    def test_write_to_read_only_index(self):
        pocket_search = index.PocketSearch(writeable=False)
        with self.assertRaises(pocket_search.IndexError):
            pocket_search.insert(content="21")

    def test_unknown_field(self):
        pocket_search = index.PocketSearch(writeable=True)
        with self.assertRaises(pocket_search.FieldError):
            pocket_search.insert(non_existing_field_in_schema="21")

    def test_count(self):
        self.assertEqual(self.pocket_search.search(content="is").count(),3)
        self.assertEqual(self.pocket_search.search(content="notinindex").count(),0)

    def test_indexing(self):
        self.assertEqual(self.pocket_search.search(content="fence")[0].content,self.data[0])
        self.assertEqual(self.pocket_search.search(content="is")[0].content,self.data[0])

    def test_get_all(self):
        self.assertEqual(self.pocket_search.search().count(),3)

    def test_get_rowid(self):
        self.pocket_search.search()[0].rowid

    def test_slicing_open(self):
        with self.assertRaises(index.Query.QueryError):
            results = self.pocket_search.search(content="is")[0:]

    def test_negative_slicing_start(self):
        with self.assertRaises(index.Query.QueryError):
            results = self.pocket_search.search(content="is")[-1:]

    def test_negative_slicing_end(self):
        with self.assertRaises(index.Query.QueryError):
            results = self.pocket_search.search(content="is")[:-4]

    def test_start_stop_none(self):
        with self.assertRaises(index.Query.QueryError):
            self.pocket_search.search(content="is")[:]

    def test_non_numeric_index(self):
        with self.assertRaises(index.Query.QueryError):
            self.pocket_search.search(content="is")["a"]

    def test_slicing(self):
        results = self.pocket_search.search(content="is")[0:2]
        self.assertEqual(results[0].content,self.data[0])
        self.assertEqual(results[1].content,self.data[1])

    def test_iteration(self):
        for idx,item in enumerate(self.pocket_search.search(content="is")):
            item.content # just check, if it possible to call the attribute

    def test_order_by(self):
        r = self.pocket_search.search(content="is").order_by("content")
        self.assertEqual(r[0].content,self.data[0])
        self.assertEqual(r[1].content,self.data[1])
        self.assertEqual(r[2].content,self.data[2])

class IndexUpdateTests(BaseTest):

    def test_get_entry(self):
        document = self.pocket_search.get(rowid=1)

    def test_get_non_existing_entry(self):
        with self.assertRaises(self.pocket_search.DocumentDoesNotExist):
            self.pocket_search.get(rowid=1000)

    def test_delete_entry(self):
        self.pocket_search.delete(rowid=1)
        # Entry if "fox" should have disappeared:
        self.assertEqual(self.pocket_search.search(content="fox").count(),0)

    def test_update_entry(self):
        self.pocket_search.update(rowid=1,content="The DOG jumped over the fence. Now he is beyond the fence.")
        self.assertEqual(self.pocket_search.search(content="fox").count(),0)
        self.assertEqual(self.pocket_search.search(content="dog").count(),1)
        self.assertEqual(self.pocket_search.search().count(),3)

class CharacterTest(unittest.TestCase):

    def setUp(self):
        self.data = [
            "äö",
            "break-even",
            "bleɪd",
            "(bracket)",
            "(bracket )",            
                "(bracket]",    
            "U.S.A."   ,
            "ˌrʌnɚ"  ,
            "'x'"   
        ]
        self.pocket_search = index.PocketSearch(writeable=True)
        for elem in self.data:
            self.pocket_search.insert(content=elem)    

    def test_search_hyphen(self):
        self.assertEqual(self.pocket_search.search(content="break even").count(),1)
        self.assertEqual(self.pocket_search.search(content="break-even").count(),1)
        self.assertEqual(self.pocket_search.search(content="breakeven").count(),0)

    def test_search_special_characters(self):
        self.assertEqual(self.pocket_search.search(content="äö").count(),1)

    def test_search_ascii(self):
        self.assertEqual(self.pocket_search.search(content="ao").count(),0)

    def test_search_special_characters2(self):
        self.assertEqual(self.pocket_search.search(content="bleɪd").count(),1)

    def test_search_brackets(self):
        self.assertEqual(self.pocket_search.search(content="bracket").count(),3)

    def test_search_punctuation1(self):
        self.assertEqual(self.pocket_search.search(content="u s a").count(),1)

    def test_search_punctuation2(self):
        self.assertEqual(self.pocket_search.search(content="usa").count(),0)

    def test_search_punctuation3(self):
        self.assertEqual(self.pocket_search.search(content="u.s.a").count(),1)

    def test_quoting(self):
        self.assertEqual(self.pocket_search.search(content="x").count(),1)

class MultipleFieldIndexTest(unittest.TestCase):

    def setUp(self):
        # Data taken from Wikipedia (also using some special characters)
        self.data = [
            ("Blade Runner","Blade Runner [bleɪd ˌrʌnɚ], deutscher Verleihtitel zeitweise auch Der Blade Runner, ist ein am 25. Juni 1982 erschienener US-amerikanischer Science-Fiction-Film des Regisseurs Ridley Scott."),
        ]
        self.pocket_search = index.PocketSearch(schema=Movie,writeable=True)
        for title , content in self.data:
            self.pocket_search.insert(title=title,content=content)

    def test_all_fields_available_in_results(self):
        self.assertEqual(self.pocket_search.search(content="ˌrʌnɚ")[0].title,"Blade Runner")

    def test_set_values_in_results(self):
        self.assertEqual(self.pocket_search.search(content="ˌrʌnɚ").values("title")[0].title,"Blade Runner")

    def test_set_non_existing_field_in_results(self):
        with(self.assertRaises(index.Query.QueryError)):
            self.assertEqual(self.pocket_search.search(content="ˌrʌnɚ").values("title323232")[0].title,"Blade Runner")

    def test_set_illegal_order_by(self):
        with(self.assertRaises(index.Query.QueryError)):
            self.assertEqual(self.pocket_search.search(content="ˌrʌnɚ").order_by("title323232")[0].title,"Blade Runner")

    def test_search_movie(self):
        self.assertEqual(self.pocket_search.search(content="Blade").count(),1)
        self.assertEqual(self.pocket_search.search(title="runner").count(),1)

    def test_combined_field_search(self):
        self.assertEqual(self.pocket_search.search(content="Blade",title="runner").count(),1)

if __name__ == '__main__':
    unittest.main()