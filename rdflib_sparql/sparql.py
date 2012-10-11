import collections
import itertools

from rdflib.namespace import NamespaceManager
from rdflib import Variable, BNode, Graph, URIRef, Literal


from parserutils import CompValue

class SPARQLError(Exception): 
    def __init__(self,msg=None): 
        Exception.__init__(self,msg)

class NotBoundError(SPARQLError):
    def __init__(self): 
        SPARQLError.__init__(self)

class AlreadyBound(SPARQLError): 
    """Raised when trying to bind a variable that is already bound!"""
    def __init__(self): 
        SPARQLError.__init__(self)

class Bindings(dict):
    def __init__(self, outer=None, d=[]): 
        dict.__init__(self, d)
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

class FrozenBindings(collections.Mapping):
    """
    An immutable hashable dict

    Taken from http://stackoverflow.com/a/2704866/81121

    """

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        # It would have been simpler and maybe more obvious to 
        # use hash(tuple(sorted(self._d.iteritems()))) from this discussion
        # so far, but this solution is O(n). I don't know what kind of 
        # n we are going to run into, but sometimes it's hard to resist the 
        # urge to optimize when it will gain improved algorithmic performance.
        if self._hash is None:
            self._hash = 0
            for key, value in self.iteritems():
                self._hash ^= hash(key)
                self._hash ^= hash(value)
        return self._hash

    def vars(self, vars):
        return FrozenBindings(x for x in self.iteritems() if x[0] in vars)
    
    def compatible(self, other): 
        for k in self: 
            if k in other:
                if self[k]!=other[k]: return False
        for k in other:
            if k in self: 
                if self[k]!=other[k]: return False
        return True
    
    def merge(self, other): 
        res=FrozenBindings(itertools.chain(self.iteritems(), other.iteritems()))

        return res
    
    def str(self):
        return self._d.str()

class QueryContext(object): 

    def __init__(self, graph=None): 
        self.bindings=Bindings()
        self.graph=graph
        self.namespace_manager=NamespaceManager(Graph())  # ns man needs a store
        self.base=None
        self.vars=set()

        self.bnodes=collections.defaultdict(BNode)


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
            return FrozenBindings((k,v) for k,v in self.bindings.iteritems() if k in vars)
        else:
            return FrozenBindings(self.bindings.iteritems())

    def __setitem__(self, key, value): 
        if key in self.bindings and self.bindings[key]!=value:
            raise AlreadyBound()
            
        self.bindings[key]=value

    def push(self, d=[]):
        self.bindings=Bindings(self.bindings,d)
        
    def pop(self):
        self.bindings=self.bindings.outer
        if self.bindings==None:
            raise Exception("We've bottomed out of the bindings stack!")

    def resolvePName(self, prefix, localname): 
        return URIRef(self.namespace_manager.store.namespace(prefix or "")+(localname or ""))
    
    def absolutize(self, iri):
    
        """
        Apply BASE / PREFIXes to URIs 
        (and to datatypes in Literals)
        """
    
        if isinstance(iri, CompValue): 
            if iri.name=='pname':
                return self.resolvePName(iri.prefix, iri.localname)
            if iri.name=='literal':
                return Literal(iri.string, lang=iri.lang, datatype=self.absolutize(iri.datatype))        
        elif isinstance(iri, Variable): 
            self.vars.add(iri)
        elif isinstance(iri,URIRef) and not ':' in iri: # TODO: Better check for relative URI?
            return URIRef(self.base+iri)
        return iri

