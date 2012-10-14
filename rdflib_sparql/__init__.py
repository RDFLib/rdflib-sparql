"""
If true, using FROM <uri> and FROM NAMED <uri> 
will load/parse more data
"""
SPARQL_LOAD_GRAPHS=True

"""
If True - the default graph in the RDF Dataset is the union of all 
named graphs (like RDFLib's ConjunctiveGraph)
"""
SPARQL_DEFAULT_GRAPH_UNION=True

import parser
import operators
import parserutils

