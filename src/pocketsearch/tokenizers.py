'''
FTS5 tokenizer configuration for PocketSearch schemas.

Tokenizer classes translate to the ``tokenize`` option on FTS5 virtual tables
and can also tokenize query strings in Python (e.g. for spell checking).
'''

import abc
import unicodedata


class Tokenizer(abc.ABC):
    '''
    Base class for tokenizers
    '''

    class TokenizerError(Exception):
        '''
        Thrown if the initialization of the tokenizer fails
        '''

    def __init__(self, name):
        self.name = name
        self.properties = {}

    def add_property(self, name, value):
        '''
        Add a property to the tokenizer
        '''
        if value is not None:
            self.properties[name] = self.Property(name, value)

    class Property:
        '''
        Property associated with tokenizer
        '''

        def __init__(self, name, value):
            self.name = name
            self.value = value

    def to_sql(self):
        properties = " ".join(["%s '%s'" % (p.name, p.value)
                              for p in self.properties.values()])
        return "tokenize=\"{name} {properties}\"".format(name=self.name, properties=properties)


class Unicode61(Tokenizer):
    '''
    Unicode61 tokenizer (see https://www.sqlite.org/fts5.html for more details)
    '''

    VALID_DIACRITICS = ["0", "1", "2"]

    def __init__(self, remove_diacritics="2", categories=None, tokenchars=None, separators=""):
        super().__init__("unicode61")
        if remove_diacritics not in self.VALID_DIACRITICS and remove_diacritics is not None:
            raise self.TokenizerError(
                "Invalid valid for remove_diacritics. Valid options are %s" % self.VALID_DIACRITICS)
        self.add_property("remove_diacritics", remove_diacritics)
        if categories is None:
            categories = "L* N* Co"
        self.add_property("categories", categories)
        self.add_property("tokenchars", tokenchars)
        self.add_property("separators", separators)

    def is_tokenchar(self, character):
        '''
        Test if the given character is a token character (True) or 
        separator (False)
        '''
        categories = self.properties.get("categories").value.split()
        if "tokenchars" in self.properties:
            tokenchars = self.properties["tokenchars"].value.split()
        else:
            tokenchars = []
        additional_separators = self.properties.get("separators")
        if additional_separators is not None:
            if character in additional_separators.value:
                return False
        if character in tokenchars:
            return True
        ch_category = unicodedata.category(character)
        return ch_category in categories or ch_category[0]+"*" in categories

    def tokenize(self, input_str, keep=[]):
        '''
        Based on the settings of unicode61 tokenizer given, split the 
        input_str into individual tokens and return them as a list of 
        tokens.
        You can provide additional characters to be considered as tokens 
        in the keep arguments. 
        When quote is set to True, tokens containing punctuation will be 
        automatically quoted.
        '''
        output_str = ""
        for character in str(input_str):
            if character in keep:
                output_str += character
                continue
            if self.is_tokenchar(character):
                output_str += character
            else:
                output_str += " "
        return [ch for ch in output_str.split(" ") if len(ch) > 0]
