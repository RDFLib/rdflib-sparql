
"""

Query using graph.query

Result is iterable over the result rows
result.vars contains the variables

or result.bindings is a list of dicts of variables bindings

"""

import rdflib

g = rdflib.Graph()
g.load("foaf.rdf")

for row in g.query(
        'select ?s where { [] <http://xmlns.com/foaf/0.1/knows> ?s .}'):
    print row
