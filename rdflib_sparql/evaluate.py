from rdflib import Variable, URIRef, Literal, Graph, ConjunctiveGraph

from rdflib_sparql.parserutils import CompValue, Expr, value
from rdflib_sparql.operators import EBV
from rdflib_sparql.algebra import triples
from rdflib_sparql.sparql import QueryContext, NotBoundError, AlreadyBound, SPARQLError


def _diff(a,b, expr): 
    res=set()
    for x in a: 
        if all(not x.compatible(y) or not _ebv(expr,x.merge(y)) for y in b): 
            res.add(x)

    return res

def _join(a,b):
    res=set()
    for x in a: 
        for y in b: 
            if x.compatible(y):
                res.add(x.merge(y))
    return res

def _ebv(expr, ctx): 

    """
    Return true/false for the given expr
    Either the expr is itself true/false
    or evaluates to something, with the given ctx

    an error is false
    """

    try: 
        return EBV(expr)
    except SPARQLError: 
        pass 
    if isinstance(expr, Expr):         
        try: 
            return EBV(expr.eval(ctx))
        except SPARQLError: 
            return False # filter error == False
    elif isinstance(expr, CompValue): 
        raise Exception("Weird - filter got a CompValue without evalfn! %r"%expr)
    return False


def _filter(a,expr): 
    for c in a:
        if _ebv(expr, c):
            yield c



def evalBGP(ctx, bgp): 
    
    if not bgp:
        yield ctx.solution()
        return 

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

            for _ctx in evalBGP(ctx,bgp[1:]): 
                yield _ctx

        finally:
            if None in (_s,_p,_o): 
                ctx.pop()



    
    
def evalJoin(ctx, join): 

    a=set(evalPart(ctx, join.p1))
    b=set(evalPart(ctx, join.p2))
    return _join(a,b)

def evalUnion(ctx, union): 
    res=set()
    res.update(evalPart(ctx, union.p1))
    res.update(evalPart(ctx, union.p2))
    return res

def evalLeftJoin(ctx, join): 

    a=set(evalPart(ctx, join.p1))
    b=set(evalPart(ctx, join.p2))
    res=set()
    res.update(_filter(_join(a,b), join.expr))
    res.update(_diff(a,b,join.expr))

    return res

def evalFilter(ctx, part): 
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
    elif part.name=='Minus':
        raise Exception('Minus NotYetImplemented!')    
    elif part.name=='Graph':
        return evalGraph(ctx, part)
    elif part.name=='Union':
        return evalUnion(ctx, part)
    elif part.name=='ToMultiSet':
        return evalMultiset(ctx,part)
    elif part.name=='Extend':
        raise Exception('Extend NotYetImplemented!')

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
    res,var=evalPart(ctx, slice.p)
    
    if slice.length:
        return list(res)[slice.start:slice.start+slice.length],var
    else: 
        return list(res)[slice.start:],var

def evalReduced(ctx, part): 
    return evalPart(ctx, part.p) # TODO!

def evalDistinct(ctx, part): 
    res,var=evalPart(ctx, part.p)

    nodups=[]
    done=set()
    for x in res: 
        if x not in done:
            nodups.append(x)
            done.add(x)

    return nodups, var

def evalProject(ctx, project): 
    res=evalPart(ctx, project.p)
    if project.PV: 
        return [ row.project(project.PV) for row in res], project.PV
    else: 
        return res, project.PV
    
       

def evalSelectQuery(ctx, query):

    res={}
    res["type_"]="SELECT"    
    res["bindings"],res["vars_"]=evalPart(ctx, query.p)

    return res

def evalAskQuery(ctx, query):            
    bindings,var=evalPart(ctx, query.p)
        
    res={}
    res["type_"]="ASK"
    res["askAnswer"]=False
    for x in bindings: 
        res["askAnswer"]=True
        break

    return res

def evalConstructQuery(ctx, query):

    template=triples(query.template)

    graph=Graph()

    bindings,var=evalPart(ctx, query.p)

    for c in bindings:
        for t in template:
            s,p,o=[c.absolutize(x) for x in t]

            _s=ctx[s]
            _p=ctx[p]
            _o=ctx[o]

            if _s is not None and \
                    _p is not None and \
                    _o is not None:

                graph.add((_s,_p,_o))

    res={}
    res["type_"]="CONSTRUCT"
    res["graph"]=graph    

    return res


def evalQuery(graph, query, initBindings, initNs):
    ctx=QueryContext(graph)

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

    return evalPart(ctx, main)
