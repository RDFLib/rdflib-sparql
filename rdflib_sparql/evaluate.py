import collections

from rdflib import Variable, Graph, ConjunctiveGraph, BNode

from rdflib_sparql.parserutils import value
from rdflib_sparql.sparql import QueryContext, AlreadyBound, FrozenBindings, SPARQLError
from rdflib_sparql.evalutils import _filter, _eval, _join, _diff, _minus

from rdflib_sparql.aggregates import evalAgg


"""
These method recursively evaluate the SPARQL Algebra 

evalQuery is the entry-point, it will setup context and 
return the SPARQLResult object

evalPart is called on each level and will delegate to the right method

A rdflib_sparql.sparql.QueryContext is passed along, keeping
information needed for evaluation

A list of dicts (solution mappings) is returned, apart from GroupBy which may also return a dict of list of dicts

"""

def evalBGP(ctx, bgp): 

    """
    A basic graph pattern
    """
    
    if not bgp:
        return [ctx.solution()]

    res=[]
    s,p,o=[ctx.absolutize(x) for x in bgp[0]]

    _s=ctx[s]
    _p=ctx[p]
    _o=ctx[o]

    for ss,sp,so in ctx.graph.triples((_s,_p,_o)):
        try: 
            if None in (_s,_p,_o): 
                ctx.push()

            if _s==None: ctx[s]=ss

            try: 
                if _p==None: ctx[p]=sp
            except AlreadyBound: 
                continue

            try: 
                if _o==None: ctx[o]=so
            except AlreadyBound: 
                continue

            res+=evalBGP(ctx,bgp[1:])

        finally:
            if None in (_s,_p,_o): 
                ctx.pop()

    return res

def evalExtend(ctx, extend): 
    # TODO: Deal with dict returned from evalPart from GROUP BY
    
    res=[]
    for c in evalPart(ctx, extend.p):
        e=_eval(extend.expr,c)
        if not isinstance(e, SPARQLError):
            res.append(c.merge({extend.var: e}))
        else: 
            res.append(c)
    return res
               
        
    
def evalJoin(ctx, join): 

    # TODO: Deal with dict returned from evalPart from GROUP BY
    # only ever for join.p1

    a=set(evalPart(ctx, join.p1))
    b=set(evalPart(ctx, join.p2))
    return _join(a,b)

def evalUnion(ctx, union): 
    res=set()
    res.update(evalPart(ctx, union.p1))
    res.update(evalPart(ctx, union.p2))
    return res

def evalMinus(ctx, minus): 
    a=set(evalPart(ctx, minus.p1))
    b=set(evalPart(ctx, minus.p2))
    return _minus(a,b)

def evalLeftJoin(ctx, join): 

    a=set(evalPart(ctx, join.p1))
    b=set(evalPart(ctx, join.p2))
    res=set()
    res.update(_filter(_join(a,b), join.expr))
    res.update(_diff(a,b,join.expr))

    return res

def evalFilter(ctx, part): 
    #import pdb; pdb.set_trace()

    # TODO: Deal with dict returned from evalPart!

    return _filter(evalPart(ctx, part.p), part.expr)

def evalGraph(ctx, part): 
    ctx=ctx.clone()
    graph=ctx[ctx.absolutize(part.term)]
    if graph is None:
        for graph in ctx.dataset.contexts(): 

            # in SPARQL the default graph is NOT a named graph
            if graph==ctx.dataset.default_context: 
                continue 

            ctx.pushGraph(graph)
            ctx.push()
            ctx[part.term]=graph.identifier
            for x in evalPart(ctx, part.p):
                yield x
            ctx.pop()
            ctx.popGraph()
    else: 
        if not isinstance(ctx.dataset, ConjunctiveGraph): 
            raise Exception("Non-conjunctive-graph doesn't know about graphs!")
        ctx.pushGraph(ctx.dataset.get_context(graph))
        for x in evalPart(ctx, part.p):
            yield x
        
def evalMultiset(ctx, part): 
    #import pdb; pdb.set_trace()
    return evalPart(ctx, part.p)

def evalPart(ctx, part):
    if part.name=='BGP':
        return evalBGP(ctx,part.triples)
    elif part.name=='Filter': 
        return evalFilter(ctx,part)
    elif part.name=='Join': 
        return evalJoin(ctx, part)
    elif part.name=='LeftJoin':
        return evalLeftJoin(ctx, part)
    elif part.name=='Graph':
        return evalGraph(ctx, part)
    elif part.name=='Union':
        return evalUnion(ctx, part)
    elif part.name=='ToMultiSet':
        return evalMultiset(ctx,part)
    elif part.name=='Extend':        
        return evalExtend(ctx, part)
    elif part.name=='Minus': 
        return evalMinus(ctx, part)

    elif part.name=='Project': 
        return evalProject(ctx, part)
    elif part.name=='Slice': 
        return evalSlice(ctx, part)
    elif part.name=='Distinct': 
        return evalDistinct(ctx, part)
    elif part.name=='Reduced': 
        return evalReduced(ctx, part)

    elif part.name=='OrderBy': 
        return evalOrderBy(ctx, part)
    elif part.name=='Group': 
        return evalGroup(ctx, part)
    elif part.name=='AggregateJoin':
        return evalAggregateJoin(ctx, part)

    elif part.name=='SelectQuery': 
        return evalSelectQuery(ctx,part)
    elif part.name=='AskQuery':
        return evalAskQuery(ctx,part)
    elif part.name=='ConstructQuery':
        return evalConstructQuery(ctx,part)
    elif part.name=='DescribeQuery':
        raise Exception('DESCRIBE not implemented')


    else: 
        #import pdb ; pdb.set_trace()
        raise Exception('I dont know: %s'%part.name)
        
        


def evalGroup(ctx, group): 

    """
    http://www.w3.org/TR/sparql11-query/#defn_algGroup
    """

    p=evalPart(ctx, group.p)
    if not group.expr: 
        return {1:p}
    else: 
        res=collections.defaultdict(list)
        for c in p: 
            k=tuple(_eval(e, c) for e in group.expr)
            res[k].append(c)
        return res
        
def evalAggregateJoin(ctx, agg): 
    #import pdb ; pdb.set_trace()
    p=evalPart(ctx, agg.p)
    # p is always a Group, we always get a dict back

    res=[]
    for row in p: 
        bindings={}
        for a in agg.A: 
            evalAgg(a,p[row],bindings)

        res.append(FrozenBindings(ctx, bindings))
    return res


def evalOrderBy(ctx, part): 

    res=evalPart(ctx, part.p)
    
    for e in reversed(part.expr): 

        def val(x): 
            try: 
                return value(x, e.expr) 
            except: 
                return None
        
        reverse=bool(e.order and e.order=='DESC')
        res=sorted(res, key=val, reverse=reverse)
    
    return res
        

def evalSlice(ctx, slice): 
    res=evalPart(ctx, slice.p)
    
    if slice.length is not None:
        return list(res)[slice.start:slice.start+slice.length]
    else: 
        return list(res)[slice.start:]

def evalReduced(ctx, part): 
    return evalPart(ctx, part.p) # TODO!

def evalDistinct(ctx, part): 
    res=evalPart(ctx, part.p)

    nodups=[]
    done=set()
    for x in res: 
        if x not in done:
            nodups.append(x)
            done.add(x)

    return nodups

def evalProject(ctx, project): 
    res=evalPart(ctx, project.p)

    return [ row.project(project.PV) for row in res]

    
       

def evalSelectQuery(ctx, query):            

    res={}
    res["type_"]="SELECT"        
    res["bindings"]=evalPart(ctx, query.p)
    res["vars_"]=query.PV 
    return res

def evalAskQuery(ctx, query):            
    res={}
    res["type_"]="ASK"
    res["askAnswer"]=False
    for x in evalPart(ctx, query.p):
        res["askAnswer"]=True
        break

    return res

def evalConstructQuery(ctx, query):
    template=query.template

    graph=Graph()

    for c in evalPart(ctx, query.p):
        bnodeMap=collections.defaultdict(BNode) 
        for t in template:
            s,p,o=[c.absolutize(x) for x in t]

            _s=c.get(s)
            _p=c.get(p)
            _o=c.get(o)

            # instantiate new bnodes for each solution
            _s,_p,_o=[bnodeMap[x] if isinstance(x,BNode) else y for x,y in zip(t,(_s,_p,_o))]

            if _s is not None and \
                    _p is not None and \
                    _o is not None:

                graph.add((_s,_p,_o))

    res={}
    res["type_"]="CONSTRUCT"
    res["graph"]=graph    

    return res


def evalQuery(graph, query, initBindings, initNs, base=None):
    ctx=QueryContext(graph)
    if base:
        ctx.base=base

    if initBindings:
        for k,v in initBindings.iteritems(): 
            if not isinstance(k, Variable):
                k=Variable(k)
            ctx[k]=v
        ctx.push() # nescessary?

    if initNs:
        for k,v in initNs:
            ctx.namespace_manager.bind(k,v)

    prologue=query[0]
    for x in prologue:
        if x.name=='Base': 
            ctx.base=x.iri
        elif x.name=='PrefixDecl':
            ctx.namespace_manager.bind(x.prefix, ctx.absolutize(x.iri))

    main=query[1]

    #import pdb; pdb.set_trace()
    if main.datasetClause:
        ctx=ctx.clone() # or push/pop?

        firstDefault=False
        for d in main.datasetClause:
            if d.default:

                if firstDefault:
                    # replace current default graph
                    dg=ctx.dataset.get_context(BNode())
                    ctx.pushGraph(dg)
                
                g=ctx.absolutize(d.default)
                ctx.load(g, default=True)

            elif d.named:
                g=ctx.absolutize(d.named)
                ctx.load(g, default=False)
        
    return evalPart(ctx, main)
