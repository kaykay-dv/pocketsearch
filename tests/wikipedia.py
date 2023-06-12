import xml.sax
import pocketsearch
import psutil
import matplotlib.pyplot as plt

def plot(file_name,xlabel,ylabel,title,data):
    '''
    Plots time series
    '''
    plt.plot([r[0] for r in data], [r[1] for r in data])
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=45)
    plt.savefig(file_name)

pid = psutil.Process()

class Wikipedia(pocketsearch.Schema):
    '''
    Simple schema for Wikipedia abstracts
    '''

    title = pocketsearch.Text()
    text = pocketsearch.Text(index=True)
    document_rank = pocketsearch.Int(index=True)

class WikipediaAbstractSAXParser(xml.sax.ContentHandler):
    '''
    Simple parser that reads title and abstract from the 
    Wikipedia dump.
    '''

    def __init__(self):
        self.current_element = ""
        self.wiki_pages=[]
        self.count=0
        self.timer = pocketsearch.Timer()
        # set the write buffer to 1500 to speed up inserts
        self.index = pocketsearch.PocketSearch(db_name="en_wikipedia.db",schema=Wikipedia,writeable=True,write_buffer_size=1500)
        self.ram_usage = []
        self.avg_docs_indexed = []

    def startElement(self, name, attrs):
        self.current_element = name
        if self.current_element == "doc":
            self.wiki_page = {
                "title" : "",
                "abstract" : "",
                "sublink" : 0
            }
        if self.current_element == "sublink":
            self.wiki_page["sublink"]=self.wiki_page["sublink"]+1

    def endElement(self, name):  
        if name == "doc":
            self.index.insert(title=self.wiki_page.get("title"),
                              document_rank=self.wiki_page.get("sublink"),
                              text=self.wiki_page.get("title") + " " + self.wiki_page.get("abstract"))
            self.count+=1
            if self.count % 1000 == 0:
                memory_info = pid.memory_info()
                current_ram = round(memory_info.rss / 1024 / 1024,2)
                self.ram_usage.append((self.count,current_ram))
                self.avg_docs_indexed.append((self.count,self.timer.get_its()))
            self.timer.snapshot()

    def characters(self, data):
        if self.current_element == "title":
            if data is not None:
                self.wiki_page["title"]+=data
        elif self.current_element == "abstract":
            if data is not None:
                self.wiki_page["abstract"]+=data


if __name__ == "__main__":
    handler = WikipediaAbstractSAXParser()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.parse(".data/enwiki-latest-abstract.xml")
    handler.index.commit() # flush last changes
    handler.index.optimize()
    plot('wikipedia_ram_usage.png','# Number of documents indexed','RAM Usage in MB','RAM Usage over Time',handler.ram_usage)
    plot('wikipedia_avg_docs_indexed.png','# Number of documents indexed','Average number of indexed documents','Average number of indexed documents over time',handler.avg_docs_indexed)
    

