
from pyparsing import ParseException

import rdflib

from rdflib_sparql.processor import SPARQLProcessor

g=rdflib.Graph()

#g.load('/home/ggrimnes/2006/04/orange/data/foaf.rdf')
#g.load('/home/ggrimnes/projects/rdflib/rdflib-sparql/test/DAWG/data-r2/basic/data-1.ttl', format='turtle')

a=rdflib.URIRef('urn:a')
b=rdflib.URIRef('urn:b')
c=rdflib.URIRef('urn:c')

x=rdflib.URIRef('urn:x')
y=rdflib.URIRef('urn:y')
z=rdflib.URIRef('urn:z')

d=rdflib.Literal('cheese', lang="no")


g.add((a,x,b))
g.add((a,x,c))
g.add((b,y,d))

s=SPARQLProcessor(g)

try:

    r=s.query('''prefix : <urn:> select * where { ?x :p [ :v1 ?v1 ; :v2 ?v2 ] }''')
    #r=s.query('''CONSTRUCT { ?a <urn:name> ?b } WHERE { ?a <urn:x> ?b }''')

    #r=s.query('''SELECT  * WHERE { ?s <urn:b> 'cake'^^<urn:cake> }''')
    #r=s.query('''ASK WHERE { ?s <urn:x> ?o  OPTIONAL { ?o <urn:y> ?o2 } }''')
    
    #r=s.query('''PREFIX foaf: <http://xmlns.com/foaf/0.1/> SELECT  * WHERE { ?s a foaf:Person ; foaf:name 'Martin May' }''')
    #r=s.query('''PREFIX foaf: <http://xmlns.com/foaf/0.1/> SELECT  * WHERE { ?s a foaf:Person ; foaf:name ?name . FILTER (?name='Martin May') }''')
    
    #r=s.query('''PREFIX foaf: <http://xmlns.com/foaf/0.1/> SELECT  * WHERE { ?s a foaf:Person ; foaf:name ?name .  }''')

#    r=s.query('''PREFIX : <http://example.org/x/> PREFIX  xsd:    <http://www.w3.org/2001/XMLSchema#> SELECT * WHERE { :x :p "asd"^^:int }''')

except ParseException, err:
    print err.line
    print " "*(err.column-1) + "^"
    print err
    raise


for x in r:
    print x

#for x in r.bindings:
#    print x
