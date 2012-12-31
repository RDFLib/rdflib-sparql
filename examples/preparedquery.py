
"""

Prepared queries

"""

import rdflib
from rdflib_sparql.processor import prepareQuery

q = prepareQuery(
    'select ?s where { ?person <http://xmlns.com/foaf/0.1/knows> ?s .}')

g = rdflib.Graph()
g.load("foaf.rdf")

tim = rdflib.URIRef("http://www.w3.org/People/Berners-Lee/card#i")

for row in g.query(q, initBindings={'person': tim}):
    print row
