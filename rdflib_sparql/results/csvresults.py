"""

This module implements a parser and serializer for the CSV SPARQL result formats

http://www.w3.org/TR/sparql11-results-csv-tsv/

"""


import csv

from rdflib import Variable, BNode, URIRef, Literal

from rdflib.query import Result, ResultException, ResultSerializer, ResultParser


class CSVResultParser(ResultParser): 
    def __init__(self): 
        self.delim=","

    def parse(self, source):
        
        r=Result('SELECT')
        
        reader=csv.reader(source, delimiter=self.delim)
        r.vars=[Variable(x) for x in reader.next()]
        r.bindings=[]

        for row in reader: 
            r.bindings.append(self.parseRow(row, r.vars))

        return r
        
    def parseRow(self, row, v): 
        return dict((var,val) for var,val in zip(v, [ self.convertTerm(t) for t in row ]) if val!=None)
    
    def convertTerm(self, t): 
        if t=="": return None
        if t.startswith("_:"): return BNode(t) # or generate new IDs?
        if t.startswith("http://") or t.startswith("https://"): # TODO: more?
            return URIRef(t)
        return Literal(t)
        


                                  

class CSVResultSerializer(ResultSerializer):
    
    def __init__(self, result): 
        ResultSerializer.__init__(self, result)

        self.delim=","
        if result.type!="SELECT": 
            raise Exception("CSVSerializer can only serialize select query results")

    def serialize(self, stream, encoding=None): 
        
        out=csv.writer(stream, delimiter=self.delim)

        vs=list(self.result.vars)
        out.writerow(vs)
        for row in self.result.bindings:
            out.writerow([self.serializeTerm(row.get(v)) for v in vs])
        
    def serializeTerm(self, term): 
        if term is None: return ""
        return term.encode("utf-8")
        
