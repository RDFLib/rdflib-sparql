from rdflib import Variable, URIRef

from rdflib_sparql.parserutils import CompValue
from rdflib_sparql.sparql import QueryContext


def absolutize(ctx, iri):
    if isinstance(iri, CompValue) and iri.name=='pname':
        return ctx.resolvePName(iri.prefix, iri.localname)
    if not isinstance(iri, URIRef): 
        return iri
    if not ':' in iri: 
        return ctx.base+iri
    return iri

def triples(l): 
    assert (len(l) % 3) == 0, 'these aint triples'
    return [(l[x],l[x+1],l[x+2]) for x in range(0,len(l),3)]

def matchBGP(bgp, ctx): 
    
    if not bgp:
        yield ctx
        return 
    
    s,p,o=[absolutize(ctx,x) for x in bgp[0]]

    _s=ctx[s]
    _p=ctx[p]
    _o=ctx[o]

    for ss,sp,so in ctx.graph.triples((_s,_p,_o)):
        if not all((_s,_p,_o)): 
            ctx.push()

        if not _s: ctx[s]=ss
        if not _p: ctx[p]=sp
        if not _o: ctx[o]=so
        
        for _ctx in matchBGP(bgp[1:],ctx): 
            yield _ctx
        
        if not all((_s,_p,_o)): 
            ctx.pop()



def evalGroupOrUnionGraphPattern(ctx,pattern):
    # pattern.graph is a list of GroupGraphPatterns to union
    pass

def evalGroupGraphPatternSub(ctx, pattern):
    pass
    



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
            ctx.namespace_manager.bind(x.prefix, absolutize(ctx,x.iri))
            
    
    # valuesClause = query[2]

    selQuery=query[1]

    if isinstance(selQuery, CompValue):

        if selQuery.name=='SelectQuery': 
            return evalSelectQuery(ctx,selQuery)

    raise Exception('Urk!')

def evalPart(ctx, part):
    if part.name=='TriplesBlock':
        for c in matchBGP(triples(part.triples), ctx):
            yield c
    else: 
        raise Exception('I dont know: %s'%part.name)

def evalParts(ctx, parts):
    if not parts:
        yield ctx
        return

    for c in evalPart(ctx, parts[0]): 
        for s in evalParts(c, parts[1:]):
            yield s
    
            

def evalSelectQuery(ctx,query):

    selectVars=None
    limit=None
    offset=0

    bindings=[]
    if query.solutionmodifier:
        limit=query.solutionmodifier.limit
        offset=query.solutionmodifier.offset

    if query.var: 
        selectVars=query.var

    distinct=query.modifier and query.modifier=='DISTINCT'
    distinctSet=set()

    i=0
    for c in evalParts(ctx, query.where[0].part):
        if i>=offset:
            solution=c.solution(selectVars)
            if distinct:                
                solutionTuple=tuple(sorted(solution.iteritems())) # dicts are not hashable
                if solutionTuple not in distinctSet:
                    bindings.append(solution)
                    distinctSet.add(solutionTuple)
            else: 
                bindings.append(solution)
        i+=1
        if limit!=None and i>=limit+offset: 
            break

    res={}
    res["type_"]="SELECT"

    
    res["bindings"]=bindings

    if selectVars:
        res["vars_"]=selectVars    
    elif bindings:
        res["vars_"]=bindings[0].keys()
    else: 
        res["vars_"]=[]

    return res
