
import functools

from rdflib import Literal, Variable

from rdflib_sparql.parserutils import CompValue, Expr
from rdflib_sparql.operators import and_, simplify as simplifyFilters

from pyparsing import ParseResults

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

def Group(p, expr=None): 
    return CompValue('Group', p=p, expr=expr)



def triples(l): 
    l=reduce(lambda x,y: x+y, l)
    if (len(l) % 3) != 0: 
        #import pdb ; pdb.set_trace()
        raise Exception('these aint triples')
    return [(l[x],l[x+1],l[x+2]) for x in range(0,len(l),3)]

def translatePath(p):
    if isinstance(p, CompValue): 
        if p.name in ('PathAlternative','PathSequence') and len(p.part)==1:
            return p.part[0]
        if p.name == 'PathElt' and not p.mod: 
            return p.part
        
            

def convertExists(e):

    def _c(n): 
        if isinstance(n, CompValue):
            if n.name in ('Builtin_EXISTS', 'Builtin_NOTEXISTS'):
                n.graph=translateGroupGraphPattern(n.graph)


    e=traverse(e, visitPost=_c)

    return e

def findFilters(parts):

    filters=[]
    
    for p in parts:
        if p.name=='Filter':
            filters.append(convertExists(p.expr))

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
    return ToMultiSet(translateValues(graphPattern))

def translateGroupGraphPattern(graphPattern):     
    """
    http://www.w3.org/TR/sparql11-query/#convertGraphPattern
    """

    if graphPattern.name=='SubSelect': 
        return ToMultiSet(translate(graphPattern)[0])

    if not graphPattern.part: graphPattern.part=[] # empty { }

    filters=findFilters(graphPattern.part)

    g=[]
    for p in graphPattern.part: 
        if p.name=='TriplesBlock': 
            # merge adjacent TripleBlocks
            if not (g and g[-1].name=='BGP'): 
                g.append(BGP())
            g[-1]["triples"]+=triples(p.triples)
        elif p.name=='Bind': 
            if not g:
                g.append(BGP())
            g[-1]=Extend(g[-1], p.expr, p.var)
        else: 
            g.append(p)

    G=BGP()
    for p in g:
        if p.name=='OptionalGraphPattern':
            A=translateGroupGraphPattern(p.graph)
            if A.name=='Filter':
                G=LeftJoin(G, A.p, A.expr)
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
        elif p.name=='ServiceGraphPattern': 
            G=Join(p1=G, p2=p)
        elif p.name in ('BGP', 'Extend'): 
            G=Join(p1=G, p2=p)            
        elif p.name=='Filter': 
            pass # already collected above
        else: 
            raise Exception('Unknown part in GroupGraphPattern: %s - %s'%(type(p), p.name))
        
            
    if filters: 
        G=Filter(expr=filters, p=G)
        
    return G
    


 

class StopTraversal(Exception): 
    def __init__(self, rv): 
        self.rv=rv


def _traverse(e,visitPre=lambda n: None,visitPost=lambda n: None):
    """
    Traverse a parse-tree, visit each node    

    if visit functions return a value, replace current node
    and do not recurse further
    """
    _e=visitPre(e)
    if _e: return _e 
    
    
    if e is None: return None

    if isinstance(e, (list, ParseResults)):
        return [_traverse(x,visitPre,visitPost) for x in e]
    elif isinstance(e, tuple):
        return tuple([_traverse(x,visitPre,visitPost) for x in e])
    
    elif isinstance(e, CompValue): 
        for k,val in e.iteritems():
            e[k]=_traverse(val, visitPre,visitPost)

    _e=visitPost(e)
    if _e: return _e 

    return e

def traverse(tree,visitPre=lambda n: None, visitPost=lambda n: None,complete=None):
    """
    Traverse tree, visit each node with visit function
    visit function may raise StopTraversal to stop traversal
    if complete!=None, it is returned on complete traversal, 
    otherwise the transformed tree is returned
    """
    try:
        r=_traverse(tree,visitPre,visitPost)
        if complete is not None: return complete
        return r
    except StopTraversal,st:
        return st.rv

def _hasAggregate(x):
    """
    Traverse parse(sub)Tree
    return true if any aggregates are used
    """

    if isinstance(x, CompValue):
        if x.name.startswith('Aggregate_'): 
            raise StopTraversal(True)



def _aggs(e,A):
    """
    Collect Aggregates in A
    replaces aggregates with variable references
    """
    
    #TODO: nested Aggregates?

    if isinstance(e, CompValue) and e.name.startswith('Aggregate_'):
        A.append(e)
        aggvar=Variable('__agg_%d__'%len(A))
        e["res"]=aggvar
        return aggvar

            
def _findVars(x, res):
    """
    Find all variables in a tree
    """
    if isinstance(x, Variable): res.add(x)
    if isinstance(x, CompValue) and x.name=="Bind": 
        res.add(x.var)
        return x # stop recursion and finding vars in the expr
    

def _sample(e,v=None):
    """
    For each unaggregated variable V in expr
    Replace V with Sample(V)
    """
    if isinstance(e, CompValue) and e.name.startswith("Aggregate_"):
        return e # do not replace vars in aggregates
    if isinstance(e, Variable) and v!=e: 
        return CompValue('Aggregate_Sample', vars=e)

def _simplifyFilters(e):
    if isinstance(e,Expr):
        return simplifyFilters(e)

def translateAggregates(q,M):
    E=[]
    A=[]

    #import pdb; pdb.set_trace()

    # collect/replace aggs in :
    #    select expr as ?var
    if q.evar:
        es=[]
        for e,v in zip(q.expr, q.evar): 
            e=traverse(e,functools.partial(_sample,v=v))
            e=traverse(e,functools.partial(_aggs,A=A))
            es.append(e)
        q.expr=es

    # having clause
    if traverse(q.having,_hasAggregate,complete=False):
        q.having=traverse(q.having, _sample)
        traverse(q.having,functools.partial(_aggs,A=A))

    # order by
    if traverse(q.orderby,_hasAggregate,complete=False):
        q.orderby=traverse(q.orderby, _sample)
        traverse(q.orderby,functools.partial(_aggs,A=A))


    # sample all other select vars
    # TODO: only allowed for vars in group-by?
    if q.var: 
        for v in q.var:
            rv=Variable('__agg_%d__'%(len(A)+1))
            A.append(CompValue('Aggregate_Sample', vars=v, res=rv))
            E.append((rv, v))

    return CompValue('AggregateJoin', A=A, p=M),E

def translateValues(v): 
    # if len(v.var)!=len(v.value):
    #     raise Exception("Unmatched vars and values in ValueClause: "+str(v))
    
    res=[]
    if not v.var: return res
    if not v.value: return res
    if not isinstance(v.value[0], list):
        
        for val in v.value: 
            res.append({ v.var[0]: val })
    else: 
        for vals in v.value: 
            res.append(dict(zip(v.var, vals)))
            
    return CompValue('values', res=res)

def translate(q): 
    """
    http://www.w3.org/TR/sparql11-query/#convertSolMod

    """

    #import pdb; pdb.set_trace()
    _traverse(q, _simplifyFilters)

    q.where=traverse(q.where, visitPost=translatePath)

    # TODO: Var scope test
    VS=set()
    traverse(q.where, functools.partial(_findVars, res=VS))

    
    # all query types have a where part
    M=translateGroupGraphPattern(q.where)

    aggregate=False
    if q.groupby: 
        conditions=[]
        # convert "GROUP BY (?expr as ?var)" to an Extend
        for c in q.groupby.condition:
            if isinstance(c,CompValue) and c.name=='GroupAs':
                M=Extend(M, c.expr, c.var)
                c=c.var
            conditions.append(c)
            
        M=Group(p=M, expr=conditions)
        aggregate=True
    elif traverse(q.having, _hasAggregate, complete=False) or \
            traverse(q.orderby, _hasAggregate, complete=False) or \
            any(traverse(x, _hasAggregate, complete=False) for x in q.expr or []):
        # if any aggregate is used, implicit group by
        M=Group(p=M)
        aggregate=True

    
    if aggregate:
        M,E=translateAggregates(q,M)
    else: 
        E=[]


    # HAVING
    if q.having: 
        M=Filter(expr=and_(*q.having.condition), p=M)

    # VALUES
    if q.valuesClause:
        M=Join(p1=M, p2=ToMultiSet(translateValues(q.valuesClause)))

    PV=set()
    if not q.var and not q.expr: 
        # select * 
        PV=VS
    else: 
        if q.var:
            PV.update(q.var)
        if q.evar:
            PV.update(q.evar)
            E+=zip(q.expr, q.evar)

    for e,v in E: 
        M=Extend(M,e,v)

    # ORDER BY
    if q.orderby:
        M=OrderBy(M, [CompValue('OrderCondition', expr=c.expr, order=c.order) for c in q.orderby.condition])

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



    return M, PV


def simplify(n): 
    if isinstance(n, CompValue) and n.name=='Join':
        if n.p1.name=='BGP' and len(n.p1.triples)==0:
            return n.p2
        if n.p2.name=='BGP' and len(n.p2.triples)==0:
            return n.p1

    
def translateQuery(q): 
    """
    We get in: 
    (prologue, selectquery, [values])
    """

    P,PV=translate(q[1])
    datasetClause=q[1].datasetClause
    if q[1].name=='ConstructQuery': 

        template=triples(q[1].template) if q[1].template else None

        res=q[0],CompValue(q[1].name, p=P, 
                           template=template,
                           datasetClause=datasetClause)
    else: 
        res=q[0],CompValue(q[1].name, p=P, datasetClause=datasetClause, PV=PV)

    res=traverse(res,visitPost=simplify)

    return res
    

def pprintAlgebra(q): 
    def pp(p, ind="    "):
        # if isinstance(p, list): 
        #     print "[ "
        #     for x in p: pp(x,ind)
        #     print "%s ]"%ind
        #     return 
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
