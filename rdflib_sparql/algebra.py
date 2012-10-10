


from rdflib_sparql.parserutils import CompValue 
from rdflib_sparql.operators import and_, simplify

def triples(l): 
    if (len(l) % 3) != 0: 
        import pdb ; pdb.set_trace()
        raise Exception('these aint triples')
    return [(l[x],l[x+1],l[x+2]) for x in range(0,len(l),3)]


def findFilters(parts):

    filters=[]
    
    #if query.having:
    #    filters=query.having.condition

    for p in parts:
        if p.name=='Filter':
            filters.append(p.expr)

    if filters:
        return and_(*filters)
    
    return None


def ToMultiSet(x): 
    raise Exception('NotYetImplemented!')

def translateGroupOrUnionGraphPattern(graphPattern): 
    A=None

    for g in graphPattern.graph: 
        g=translateGroupGraphPattern(g)
        if not A: 
            A=g
        else:
            A=CompValue('Union', p1=A, p2=g)
    return A


def translateGraphGraphPattern(graphPattern): 
    return CompValue('Graph', term=graphPattern.term, graph=translateGroupGraphPattern(graphPattern.graph))

def translateInlineData(graphPattern): 
    raise Exception("NotYetImplemented!")

def translateGroupGraphPattern(graphPattern):     
    """
    http://www.w3.org/TR/sparql11-query/#convertGraphPattern
    """

    filters=findFilters(graphPattern)
    filters=simplify(filters) # TODO move me!

    g=[]
    for p in graphPattern: 
        if p.name=='TriplesBlock': 
            # merge adjacent TripleBlocks
            if not (g and g[-1].name=='BGP'): 
                g.append(CompValue('BGP', triples=[]))
            g[-1]["triples"]+=triples(p.triples)
        elif p.name=='Bind': 
            g.append(CompValue('Extend', P=g[-1] if g else None, **p))
        else: 
            g.append(p)

    G=CompValue('BGP', triples=[])
    for p in g:
        if p.name=='OptionalGraphPattern':
            A=translateGroupGraphPattern(p.graph)
            if A.name=='Filter':
                G=CompValue('LeftJoin', p1=G, p2=A.A, expr=A.F)
            else: 
                G=CompValue('LeftJoin', p1=G, p2=A, expr=True)
        elif p.name=='MinusGraphPattern': 
            G=CompValue('Minus', p1=G, p2=translateGroupGraphPattern(p.graph))
        elif p.name=='GroupOrUnionGraphPattern':
            G=CompValue('Join', p1=G, p2=translateGroupOrUnionGraphPattern(p))
        elif p.name=='GraphGraphPattern': 
            G=CompValue('Join', p1=G, p2=translateGraphGraphPattern(p))
        elif p.name=='InlineData': 
            G=CompValue('Join', p1=G, p2=translateInlineData(p))
        elif p.name=='BGP': 
            G=CompValue('Join', p1=G, p2=p)
        elif p.name=='Filter': 
            pass # already collected above
        else: 
            raise Exception('Unknown part in GroupGraphPattern: '+p.name)
        
            
    if filters: 
        G=CompValue('Filter', expr=filters, G=G)
        
    return G
    

def translate(q): 
        
    # all query types have a where part
    q.where["part"]=translateGroupGraphPattern(q.where.part)

    if q.having: 
        q.where["part"]=CompValue('Filter', expr=and_(q.having.condition), G=q.where["part"])

    return q

    
def translateQuery(q): 
    if len(q)>2:
        return q[0],CompValue('Join', p1=translate(q[1]), p2=ToMultiSet(q[2]))
    else: 
        return q[0],translate(q[1])

def pprintAlgebra(q): 
    def pp(p, ind="    "):
        if not isinstance(p, CompValue): 
            print p
            return
        print "%s("%(p.name, )
        for k in p: 
            print "%s%s ="%(ind,k,),
            pp(p[k],ind+"    ")
        print "%s)"%ind
    pp(q[1].where.part)

if __name__=='__main__': 
    import sys
    import rdflib_sparql.parser

    print pprintAlgebra(translateQuery(rdflib_sparql.parser.QueryUnit.parseString(sys.argv[1])))
