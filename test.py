
import rdflib

from rdflib_sparql.processor import SPARQLProcessor

g=rdflib.Graph()

g.load('/home/ggrimnes/2006/04/orange/data/foaf.rdf')

s=SPARQLProcessor(g)

r=s.query('prefix foaf: <http://xmlns.com/foaf/0.1/> select distinct * where { ?s a foaf:Person . }')

for x in r:
    print x
