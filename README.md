RDFLib-SPARQL
=============

A SPARQL 1.1 implementation for RDFLib.

This replaces the old implementation available in RDFExtras, hopefully
with more maintainable code.

[![Build Status](https://travis-ci.org/RDFLib/rdflib-sparql.png?branch=master)](https://travis-ci.org/RDFLib/rdflib-sparql)

Usage: 
------

Install with setuptools, either easy_install or pip will register the
SPARQL processor with RDFLib automatically. I cannot recommend this
strongly enough.

(you should also uninstall rdfextras - although my test with both
installed still gave me the NEW sparql implementation - but I belive
this was random, i.e. depending on a hash value of something)

```python
#./examples/query.py

g = rdflib.Graph()
g.load("foaf.rdf")

for row in g.query(
    'select ?s where { [] <http://xmlns.com/foaf/0.1/knows> ?s .}'):
    print row
```

Prepared Queries
----------------

Queries can be parsed/translated beforehand - and the initBindings
kwarg to graph.query can be used to fill in variables that are known:

```python
# ./examples/preparedquery.py

import rdflib
from rdflib_sparql.processor import prepareQuery

q = prepareQuery(
    'select ?s where { ?person <http://xmlns.com/foaf/0.1/knows> ?s .}')

g = rdflib.Graph()
g.load("foaf.rdf")

tim = rdflib.URIRef("http://www.w3.org/People/Berners-Lee/card#i")

for row in g.query(q, initBindings={'person': tim}): 
    print row

```

Property Paths
--------------

SPARQL PropertyPaths are also available as "pseudo properties" in python
code. See docs in *rdflib_sparql/paths.py*

```python
# ./examples/foafpath.py

g = Graph()
g.load("foaf.rdf")

tim = URIRef("http://www.w3.org/People/Berners-Lee/card#i")

print("Timbl knows:")

# find name of everyone tim knows:
for o in g.objects(tim, FOAF.knows/FOAF.name):
    print o
```

SPARQL Update
-------------

SPARQL Update is implemented - but no HTTP/SPARQL Protocol yet.
SPARQL Update requests can be evaluated with
`rdflib_sparql.processor.processUpdate`

```python
# ./examples/update.py*

import rdflib
from rdflib_sparql.processor import processUpdate

g = rdflib.Graph()
g.load("foaf.rdf")

processUpdate(g, '''
PREFIX foaf: <http://xmlns.com/foaf/0.1/> 
PREFIX dbpedia: <http://dbpedia.org/resource/> 
INSERT 
    { ?s a dbpedia:Human . } 
WHERE 
    { ?s a foaf:Person . }
''')

for x in g.subjects(
        rdflib.RDF.type, 
        rdflib.URIRef('http://dbpedia.org/resource/Human')): 
    print(x)

```

Status: 
-------

Currently about 90% of SPARQL 1.0 and SPARQL 1.1 Query tests pass. This
should be much better than the RDFExtras implementation. 

For test results, see also: 

http://www.w3.org/2009/sparql/implementations/

So far, only functional testing has been done, i.e. performance may be rubbish. 

If you would like to dig into the code, see DEVELOPERS

I would welcome any feedback on this!

- Gunnar 
http://gromgull.net


