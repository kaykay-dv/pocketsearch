import os
import sqlite3

class PocketSearch:

    def __init__(self,db_name="pocketsearch.db",
                      index_name="documents",
                      create_index=True):
        self.db_name = db_name
        self.index_name = index_name
        self.connection = sqlite3.connect(self.db_name)
        self.cursor = self.connection.cursor()
        self.db_name = db_name
        self.index_name = index_name
        if create_index:
            self.cursor.execute('''
            CREATE VIRTUAL TABLE if not exists %s USING FTS5(
                content
            )
            ''') % self.db_name    

    def insert(self,content):
        self.cursor.execute("insert into documents (content) values ('%s')" % self.clean(content))
        self.connection.commit()

    def clean(self,abstract):
        '''
        Tokenizes the given document.
        '''
        
        for ch in ["\n","\r","\t",
                   "-", "*" , "+", "/",
                   "(",")","[","]","{","}",
                   ":",".",",",";","?","!",
                   '"',"'",">>","<<",
                   "\\"]:
            abstract = abstract.replace(ch, " ")
        return abstract

    def search(self,query):
        q="select * , rank from documents where content match '%s' order by rank" % query
        return self.cursor.execute(q).fetchall()

if __name__ == "__main__":
    p = PocketSearch()   
    count=0
    for root, dirs, files in os.walk("/Users/karlkreiner/Desktop/code/git/eu_parliament/DCEP/"):
            for file in files:
                if file.endswith(".txt"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as file:
                        p.insert(file.read())
                        count=count+1
                        print(count)
    p.insert("This is a test.")
    print(p.search("test"))