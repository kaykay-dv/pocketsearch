'''
Index readers for populating PocketSearch from external sources.

``IndexReader`` subclasses yield document dictionaries consumed by
``PocketSearch.build()``. ``FileSystemReader`` walks a directory tree and
indexes text files using the bundled ``FSSchema``.
'''

import abc
import os

from .fields import Text
from .schema import Schema
from .utils import Timer


class IndexReader(abc.ABC):
    '''
    An abstract base class for index readers. Reader classes
    scan through a source (e.g. the file system or some web site)
    and retrieve documents that should be indexed.
    '''

    def read(self):
        '''
        Subclasses need to implement this method.
        It should return a list of dictionaries
        where each dictionary entry represents
        a document in the schema.
        '''
        raise NotImplementedError()


class FileSystemReader(IndexReader):
    '''
    Index files and their contents from a directory.
    The FileSystemReader expects a schema containing
    following fields:

    - filename (TEXT, unique=True)
    - text (TEXT, index=True)

    '''

    encoding = "utf-8"

    class FSSchema(Schema):
        '''
        Schema used by the index reader
        '''

        class Meta:
            '''
            FS Schema meta options
            '''
            spell_check = True

        filename = Text(is_id_field=True)
        text = Text(index=True)

    def __init__(self, base_dir="./", file_extensions=None):
        self.timer = Timer()
        if file_extensions is None:
            self.file_extensions = [".txt"]
        else:
            self.file_extensions = file_extensions
        self.base_dir = base_dir

    def file_to_dict(self, file_path, file):
        '''
        Open the file and transform it to a dictionary.
        '''
        return {"filename": file_path, "text": file.read()}

    def read(self):
        '''
        Traverse directory and yield files found matching 
        the given extensions. This expects
        '''
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                for extension in self.file_extensions:
                    if file.endswith(extension):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding=self.encoding) as file:
                            yield self.file_to_dict(file_path, file)
