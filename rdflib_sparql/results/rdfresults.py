from rdflib import Graph, Namespace, RDF, Variable

from rdflib.query import Result, ResultParser

RS=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/result-set#')

class RDFResultParser(ResultParser):
    def parse(self, source):
        return RDFResult(source)

class RDFResult(Result):
    
    def __init__(self, source): 
        Result.__init__(self, 'SELECT')
        
        if not isinstance(source,Graph):
            graph=Graph()
            graph.load(source)
        else: 
            graph=source
            
        rs=graph.value(RDF.type, RS.ResultSet) # there better be only one :)

        self.vars=[Variable(v) for v in graph.objects(rs,RS.resultVariable)]
        
        self.bindings=[]

        for s in graph.objects(rs,RS.solution): 
            sol={}
            for b in graph.objects(s,RS.bindings):
                sol[Variable(graph.value(b,RS.variable))]=graph.value(b,RS.value)

        
