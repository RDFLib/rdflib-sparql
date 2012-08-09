

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


