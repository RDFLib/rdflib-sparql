
from rdflib import Graph, Namespace, RDF
from rdflib.query import Result

from rdflib_sparql.processor import SPARQLProcessor
from rdflib_sparql.results.rdfresults import RDFResultParser

from nose.tools import eq_ as eq

MF=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#')
QT=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-query#')

def do_test_single(t):
    name,data,query,res=t

    g=Graph()
    g.load(data, format='turtle')
    
    if res.endswith('ttl'):
        resg=Graph()
        resg.load(res, format='turtle')
        res=RDFResultParser().parse(resg)
    else:
        res=Result.parse(file(res[7:]),format='xml') # relies on rdfextras

    s=SPARQLProcessor(g)

    res2=s.query(file(query[7:]).read())

    eq(res.type, res2.type, 'Types do not match: %r != %r'%(res.type, res2.type))
    eq(set(res.vars),set(res2.vars), 'Vars do not match: %r != %r'%(set(res.vars),set(res2.vars)))
    eq(res.bindings, res2.bindings, 'Bindings do not match: %r != %r'%(res.bindings, res2.bindings))
    

def read_manifest(f): 

    g=Graph()
    g.load(f, format='turtle')

    for m in g.subjects(RDF.type, MF.Manifest):
        
        for col in g.objects(m, MF.include):
            for i in g.items(col):
                for x in read_manifest(i):
                    yield x 

        for col in g.objects(m,MF.entries):
            for e in g.items(col):
                
                a=g.value(e, MF.action)
                query=g.value(a, QT.query)
                data=g.value(a, QT.data)
                res=g.value(e, MF.result)
                name=g.value(e, MF.name)
                
                yield str(name),str(data),str(query),str(res)
                
                        

def test_dawg():

    for t in read_manifest("test/DAWG/data-r2/manifest-evaluation.ttl"):
        yield do_test_single, t
