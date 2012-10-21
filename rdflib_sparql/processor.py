
from rdflib import BNode, Variable
from rdflib.query import Processor, Result

from rdflib_sparql.sparql import Query
from rdflib_sparql.parser import parseQuery
from rdflib_sparql.evaluate import evalQuery
from rdflib_sparql.algebra import translateQuery

"""
Code for tying SPARQL Engine into RDFLib
"""

class SPARQLResult(Result):
    
    def __init__(self, type_, vars_=None, bindings=None, 
                 askAnswer=None, graph=None): 
        Result.__init__(self,type_)
        self.vars=vars_
        self.bindings=bindings
        self.askAnswer=askAnswer
        self.graph=graph


class SPARQLProcessor(Processor): 

    def __init__(self, graph):
        self.graph=graph

    def query(self, strOrQuery, initBindings={}, initNs={}, base=None, DEBUG=False):
        """
        Evaluate a query with the given initial bindings, and initial namespaces
        The given base is used to resolve relative URIs in the query and 
        will be overridden by any BASE given in the query
        """
        
        if not isinstance(strOrQuery, Query):
            parsetree=parseQuery(strOrQuery)
            query=translateQuery(parsetree,base)
        else: 
            query=strOrQuery
        
        return SPARQLResult(**evalQuery(self.graph, query, initBindings, initNs, base))
        
