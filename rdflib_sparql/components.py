
class comp(object):
    def __str__(self):
        return '%s(%s)'%(type(self).__name__,", ".join("%s=%s"%(v,getattr(self,v)) for v in dir(self) if not v.startswith("_")))

    def __repr__(self):
        return str(self)

class Filter(comp):
    def __init__(self, constraint):
        self.constraint=constraint


# Expressions

class Expression(comp):
    def eval(ctx):
        raise Exception('Sub-classes implement this!')



# ----


class PName(comp):
    def __init__(self, prefix, localname):
        self.prefix=prefix
        self.localname=localname

class PrefixDecl(comp):
    def __init__(self, prefix, iri): 
        self.prefix=prefix
        self.iri=iri

class OrderBy(comp): 
    def __init__(self, order, comparators):
        """ 
        order = ASC|DESC
        """
        self.order=order
        self.comparators=comparators

class Slice(comp): 
    def __init__(self, limit=-1, offset=0):
        self.limit=limit
        self.offset=offset

class SelectQuery(comp):
    def __init__(self, preModifier, projection, datasetClause, groupGraphPattern, postModifier):         
        """
        preModifier = reduced,disctint,none
        projection = * or vars
        datasetClause = from named ...
        groupGraph = { triples etc. }
        postModifier = group, having, order, limitoffset
        """
        self.preModifier=preModifier
        self.projection=projection
        self.datasetClause=datasetClause
        self.groupGraphPattern=groupGraphPattern
        self.postModifier=postModifier
        

from rdflib import URIRef

# property paths

class Path:
    pass

class InvPath(Path):
    pass

class SequencePath(Path):
    def __init__(self,*args):
        self.args=args

class AlternativePath(Path):
    def __init__(self,*args):
        self.args=args

class ZeroOrMorePath(Path):
    def __init__(self, path):
        self.path=path
    
class OneOrMorePath(Path):
    def __init__(self, path):
        self.path=path

class ZeroOrOne(Path):
    def __init__(self, path):
        self.path=path
    
class NegatedPath(Path): 
    def __init__(self, path):
        self.path=path



def path_alternative(self,other):
    if not isinstance(other, (URIRef, Path)): 
        raise Exception('Only URIRefs or Paths can be in paths!')
    return AlternativePath(self,other)

URIRef.__or__=path_alternative

def path_sequence(self,other):
    if not isinstance(other, (URIRef, Path)): 
        raise Exception('Only URIRefs or Paths can be in paths!')
    return AlternativePath(self,other)

URIRef.__div__=path_sequence


