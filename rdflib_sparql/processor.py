
from rdflib import BNode, Variable
from rdflib.query import Processor, Result

from rdflib_sparql.parser import parseQuery
from rdflib_sparql.evaluate import evalQuery

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

    def query(self, strOrQuery, initBindings={}, initNs={}, DEBUG=False):
        
        query=parseQuery(strOrQuery)

        # clean-up / optimize!
        
        return SPARQLResult(**evalQuery(self.graph, query, initBindings, initNs))
        
