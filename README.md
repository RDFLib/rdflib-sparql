RDFLib-SPARQL
=============

A SPARQL 1.1 implementation for RDFLib

This replaces the old implementation available in RDFExtras, hopefully
with more maintainable code.

Usage: 
------

Install with setuptools, either easy_install or pip will register the
SPARQL processor with RDFLib automatically. I cannot recommend this
strongly enough.

(you should also uninstall rdfextras - although my test with both
installed still gave me the NEW sparql implementation - but I belive
this was random, i.e. depending on a hash value of something)

Then query like you always would - see also *./examples/query.py*

Prepared Queries
----------------

Queries can be parsed/translated beforehand - and the initBindings
kwarg to graph.query can be used to fill in variables that are known:

```python
import rdflib_sparql.processor
query=rdflib_sparql.processor.prepareQuery( ...queryString... ) 
...
graph.query(query, initBindings={ 'person': rdflib.URIRef('http://dbpedia.org/resource/Tim_Berners-Lee') } )
...
```

Property Paths
--------------

SPARQL PropertyPaths are also available as "pseudo properties" in python code. 
See *./examples/foafpath.py* and docs in *rdflib_sparql/paths.py*

SPARQL Update
-------------

SPARQL Update is implemented - but no HTTP/SPARQL Protocol yet.
SPARQL Update requests can be evaluated with `rdflib_sparql.processor.processUpdate`

see also *./examples/update.py*

Status: 
-------

Currently about 90% of SPARQL 1.0 and SPARQL 1.1 Query tests pass. This should be much better than the RDFExtras implementation. 

For test results, see also: 

http://www.w3.org/2009/sparql/implementations/

So far, only functional testing has been done, i.e. performance may be rubbish. 

If you would like to dig into the code, see DEVELOPERS

I would welcome any feedback on this!

- Gunnar 
http://gromgull.net


