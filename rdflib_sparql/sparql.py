from rdflib.namespace import NamespaceManager
from rdflib import Variable, BNode, Graph, URIRef

class SPARQLError(Exception): 
    def __init__(self): 
        Exception.__init__(self)

class NotBoundError(SPARQLError):
    def __init__(self): 
        SPARQLError.__init__(self)


class Bindings(dict):
    def __init__(self, outer=None): 
        self.outer=outer
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except: 
            if not self.outer: raise
            return self.outer[key]
        
    def iteritems(self):
        d=self
        while d!=None:
            for i in dict.iteritems(d):
                yield i
            d=d.outer
        
        

class QueryContext(object): 

    def __init__(self, graph=None): 
        self.bindings=Bindings()
        self.graph=graph
        self.namespace_manager=NamespaceManager(Graph())  # ns man needs a store
        self.base=None

    def __getitem__(self, key):
        # in SPARQL BNodes are just labels
        if not isinstance(key, (BNode, Variable)):
            return key
        try:
            return self.bindings[key]
        except KeyError:
            return None

    def solution(self,vars=None): 
        """
        Return a static copy of the current variable bindings as dict
        """
        if vars: 
            return dict((k,v) for k,v in self.bindings.iteritems() if k in vars)
        else:
            return dict(self.bindings.iteritems())

    def __setitem__(self, key, value): 
        self.bindings[key]=value

    def push(self):
        self.bindings=Bindings(self.bindings)
        
    def pop(self):
        self.bindings=self.bindings.outer
        if self.bindings==None:
            raise Exception("We've bottomed out of the bindings stack!")

    def resolvePName(self, prefix, localname): 
        return URIRef(self.namespace_manager.store.namespace(prefix)+localname)
