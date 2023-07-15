# Formatting search results
FTS5 provides 2 functions to highlight tokens found in text and extracting snippets from a text. 
There are 2 methods to support this in pocketsearch:

## Highlighting results

```Python
pocket_search.search(text="hello").highlight("text")[0].text
'*Hello* World !'
```

The keyword arguments marker_start and marker_end allow you to control how highlighting is done:

```Python
pocket_search.search(text="hello").highlight("text",marker_start="[",marker_end="]")[0].text
'[Hello] World !'
```

The positional arguments of the highlight method represent the fields you want to hightlight. 

If you have very long text, you might want to only show a snippet with all terms found in your +
search results. This can be done with the snippet method. Assuming we have the article 
on Wikipedia article on [inverted indices](https://en.wikipedia.org/wiki/Inverted_index) in our database we can extract snippets like this:

```Python
pocket_search.search(text="inverted file").snippet("text",snippet_length=16)[0].text
'In computer science, an *inverted* index (also referred to as a postings list, postings *file*, or...'
```

## Extracting snippets from text

Similar to the highlight method, the snippet method highlights tokens found. snippet_length defines 
the maximum number of tokens that should be contained in the snippet. It must be greater than 0 and lesser 
than 64. You can change the markers by providing text_before and text_after arguments:

```Python
pocket_search.search(text="inverted file").snippet("text",snippet_length=16,text_before="<",text_after=">")[0].text
```
