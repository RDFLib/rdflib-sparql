

from rdflib import Literal, Variable

from rdflib_sparql.parserutils import CompValue, Expr
from rdflib_sparql.operators import and_, simplify as simplifyFilters


TrueFilter=Expr('TrueFilter', lambda _1, _2: Literal(True))


# ---------------------------

def OrderBy(p, expr): 
    return CompValue('OrderBy', p=p, expr=expr)

def ToMultiSet(p):
    return CompValue('ToMultiSet', p=p)

def Union(p1,p2): 
    return CompValue('Union', p1=p1, p2=p2)

def Join(p1,p2): 
    return CompValue('Join', p1=p1, p2=p2)

def Minus(p1,p2): 
    return CompValue('Minus', p1=p1, p2=p2)

def Graph(term, graph): 
    return CompValue('Graph', term=term, p=graph)

def BGP(triples=None):
    return CompValue('BGP', triples=triples or [])

def LeftJoin(p1,p2,expr):
    return CompValue('LeftJoin', p1=p1, p2=p2, expr=expr)

def Filter(expr, p): 
    return CompValue('Filter', expr=expr, p=p)

def Extend(p, expr, var): 
    return CompValue('Extend', p=p, expr=expr, var=var)

def Project(p, PV): 
    return CompValue('Project', p=p, PV=PV)

def triples(l): 
    l=reduce(lambda x,y: x+y, l)
    if (len(l) % 3) != 0: 
        #import pdb ; pdb.set_trace()
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



def translateGroupOrUnionGraphPattern(graphPattern): 
    A=None

    for g in graphPattern.graph: 
        g=translateGroupGraphPattern(g)
        if not A: 
            A=g
        else:
            A=Union(A,g)
    return A


def translateGraphGraphPattern(graphPattern): 
    return Graph(graphPattern.term, translateGroupGraphPattern(graphPattern.graph))

def translateInlineData(graphPattern): 
    raise Exception("NotYetImplemented!")

def translateGroupGraphPattern(graphPattern):     
    """
    http://www.w3.org/TR/sparql11-query/#convertGraphPattern
    """

    if graphPattern.name=='SubSelect': 
        return ToMultiSet(translate(graphPattern))

    if not graphPattern.part: graphPattern.part=[] # empty { }

    filters=findFilters(graphPattern.part)
    filters=simplifyFilters(filters) 

    g=[]
    for p in graphPattern.part: 
        if p.name=='TriplesBlock': 
            # merge adjacent TripleBlocks
            if not (g and g[-1].name=='BGP'): 
                g.append(BGP())
            g[-1]["triples"]+=triples(p.triples)
        elif p.name=='Bind': 
            g.append(Extend(p=g[-1] if g else None, **p))
        else: 
            g.append(p)

    G=BGP()
    for p in g:
        if p.name=='OptionalGraphPattern':
            A=translateGroupGraphPattern(p.graph)
            if A.name=='Filter':
                G=LeftJoin(G,A,A.expr)
            else: 
                G=LeftJoin(G, A, TrueFilter)
        elif p.name=='MinusGraphPattern': 
            G=Minus(p1=G, p2=translateGroupGraphPattern(p.graph))
        elif p.name=='GroupOrUnionGraphPattern':
            G=Join(p1=G, p2=translateGroupOrUnionGraphPattern(p))
        elif p.name=='GraphGraphPattern': 
            G=Join(p1=G, p2=translateGraphGraphPattern(p))
        elif p.name=='InlineData': 
            G=Join(p1=G, p2=translateInlineData(p))
        elif p.name in ('BGP', 'Extend'): 
            G=Join(p1=G, p2=p)            
        elif p.name=='Filter': 
            pass # already collected above
        else: 
            raise Exception('Unknown part in GroupGraphPattern: '+p.name)
        
            
    if filters: 
        G=Filter(expr=filters, p=G)
        
    return G
    
def hasAggregate(x):
    if x is None: return False
    if isinstance(x, CompValue):
        if x.name.startswith('Aggregate_'): 
            return True
        return any(hasAggregate(v) for v in x.values())
    return False
            

def findVars(x): 
    if x is None: return []
    if isinstance(x, Variable): return set([x])    

    res=set()
        
    if isinstance(x, CompValue):
        for y in x.values(): 
            res.update(findVars(y))

    if isinstance(x, (tuple,list)):
        for y in x:
            res.update(findVars(y))

    return res
    
    

def translate(q, values=None): 
    """
    http://www.w3.org/TR/sparql11-query/#convertSolMod

    """

    # all query types have a where part
    M=translateGroupGraphPattern(q.where)

    if q.groupby: 
        M=CompValue('Group', p=M, expr=q.groupby.condition)
    elif hasAggregate(q.having) or \
            hasAggregate(q.orderby) or \
            any(hasAggregate(x) for x in q.expr or []):
        M=CompValue('Group', p=M)

    E=[] # aggregates

    # TODO: aggregates!

    # HAVING
    if q.having: 
        M=Filter(expr=simplifyFilters(and_(q.having.condition)), p=M)

    # VALUES
    if values:
        M=Join(p1=M, p2=ToMultiSet(values))

    # TODO: Var scope + collect
    VS=findVars(M)

    PV=set()
    if not q.var and not q.expr: 
        # select * 
        PV=VS
    else: 
        PV.update(q.var)
        if q.evar:
            PV.update(q.evar)
            E+=zip(q.evar, q.expr)

    for v,e in E: 
        M=Extend(M,v,e)

    # ORDER BY
    if q.orderby:
        M=OrderBy(M, [CompValue('OrderCondition', expr=simplifyFilters(c.expr), order=c.order) for c in q.orderby.condition])

    # PROJECT
    M=Project(M, PV)
    
    if q.modifier:
        if q.modifier=='DISTINCT':
            M=CompValue('Distinct',p=M)
        elif q.modifier=='REDUCED':
            M=CompValue('Reduced', p=M)

    if q.limitoffset: 
        offset=0
        if q.limitoffset.offset:             
            offset=q.limitoffset.offset.toPython()

        if q.limitoffset.limit: 
            M=CompValue('Slice',p=M,start=offset,length=q.limitoffset.limit.toPython())
        else: 
            M=CompValue('Slice',p=M,start=offset)



    return M


def simplify(q): 
    return q
    
def translateQuery(q): 
    """
    We get in: 
    (prologue, selectquery, [values])
    """

    P=translate(q[1], q[2] if len(q)>2 else None)    
    
    if q[1].name=='ConstructQuery': 
        res=q[0],CompValue(q[1].name, p=P, template=q[1].template)
    else: 
        res=q[0],CompValue(q[1].name, p=P)

    res=simplify(res)

    return res
    

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
    pp(q[1])

if __name__=='__main__': 
    import sys
    import rdflib_sparql.parser
    import os.path

    if os.path.exists(sys.argv[1]): 
        q=file(sys.argv[1]).read()
    else: 
        q=sys.argv[1]

    print pprintAlgebra(translateQuery(rdflib_sparql.parser.QueryUnit.parseString(q)))
