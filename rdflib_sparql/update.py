"""

Code for carrying out Update Operations

"""

from rdflib_sparql.sparql import QueryContext
from rdflib_sparql.evalutils import _fillTemplate, _join
from rdflib_sparql.evaluate import evalBGP

def _graphOrDefault(ctx, g):
    if g=='DEFAULT':
        return ctx.graph
    else:
        return ctx.dataset.get_context(g)


def _graphAll(ctx, g): 
    """
    return a list of graphs
    """
    if g=='DEFAULT':
        return [ctx.graph]
    elif g=='NAMED': 
        return [c for c in ctx.dataset.contexts() if c.identifier!=ctx.graph.identifier]
    elif g=='ALL': 
        return list(ctx.dataset.contexts())
    else: 
        return [ctx.dataset.get_context(g)]

def evalLoad(ctx,u):
    """
    http://www.w3.org/TR/sparql11-update/#load
    """

    if u.graphiri:         
        ctx.load(u.iri, default=False, publicID=u.graphiri)
    else: 
        ctx.load(u.iri, default=True)

def evalCreate(ctx,u):
    """
    http://www.w3.org/TR/sparql11-update/#create
    """
    g=ctx.datset.get_context(u.graphiri)
    if len(g)>0: 
        raise Exception("Graph %s already exists."%g.identifier)
    raise Exception("Create not implemented!")

def evalClear(ctx,u):
    """
    http://www.w3.org/TR/sparql11-update/#clear
    """

    for g in _graphAll(ctx,u.graphiri): 
        g.remove((None,None,None))


def evalInsertData(ctx,u):
    """
    http://www.w3.org/TR/sparql11-update/#insertData
    """
    # add triples
    g=ctx.graph
    g+=u.triples

    # add quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads: 
        cg=ctx.dataset.get_context(g)
        cg+=u.quads[g]


def evalDeleteData(ctx,u):
    """
    http://www.w3.org/TR/sparql11-update/#deleteData
    """
    # remove triples
    g=ctx.graph
    g-=u.triples

    # remove quads
    # u.quads is a dict of graphURI=>[triples]
    for g in u.quads: 
        cg=ctx.dataset.get_context(g)
        cg-=u.quads[g]



def evalDeleteWhere(ctx,u):
    """
    http://www.w3.org/TR/sparql11-update/#deleteWhere
    """

    res=evalBGP(ctx, u.triples ) 
    for g in u.quads: 
        cg=ctx.dataset.get_context(g)
        ctx.pushGraph(cg)
        res=_join(res, evalBGP(ctx, u.quads[g]))
        ctx.popGraph()
    
    for c in res:
        g=ctx.graph
        g-=_fillTemplate(u.triples, c)

        for g in u.quads:
            cg=ctx.dataset.get_context(g)
            cg-=_fillTemplate(u.quads[g], c)
            

def evalModify(ctx,u):
    raise Exception("Modify not implemented!")


def evalAdd(ctx,u):
    """

    add all triples from src to dst

    http://www.w3.org/TR/sparql11-update/#add
    """
    src,dst=u.graph

    srcg=_graphOrDefault(ctx, src)
    dstg=_graphOrDefault(ctx, dst)

    dstg+=srcg


def evalMove(ctx,u):
    """

    remove all triples from dst
    add all triples from src to dst
    remove all triples from src

    http://www.w3.org/TR/sparql11-update/#move
    """

    src,dst=u.graph

    srcg=_graphOrDefault(ctx, src)
    dstg=_graphOrDefault(ctx, dst)

    dstg.remove((None,None,None))

    dstg+=srcg

    srcg.remove((None,None,None))


def evalCopy(ctx,u):
    """

    remove all triples from dst
    add all triples from src to dst
   
    http://www.w3.org/TR/sparql11-update/#copy
    """

    src,dst=u.graph

    srcg=_graphOrDefault(ctx, src)
    dstg=_graphOrDefault(ctx, dst)

    if srcg.identifier==dstg.identifier:
        return 
    dstg.remove((None,None,None))

    dstg+=srcg





def evalUpdate(graph, update): 
    """

    http://www.w3.org/TR/sparql11-update/#updateLanguage

    'A request is a sequence of operations [...] Implementations MUST
    ensure that operations of a single request are executed in a
    fashion that guarantees the same effects as executing them in
    lexical order.

    Operations all result either in success or failure.

    If multiple operations are present in a single request, then a
    result of failure from any operation MUST abort the sequence of
    operations, causing the subsequent operations to be ignored.'

    This will return None on success and raise Exceptions on error

    """

    for u in update: 

        ctx=QueryContext(graph)

        try: 
            if u.name=='Load':
                evalLoad(ctx, u)
            elif u.name=='Clear':
                evalClear(ctx, u)
            elif u.name=='Drop':
                # rdflib does not record empty graphs, so clear == drop
                evalClear(ctx, u) 
            elif u.name=='Create':
                evalCreate(ctx, u)
            elif u.name=='Add':
                evalAdd(ctx, u)
            elif u.name=='Move':
                evalMove(ctx, u)
            elif u.name=='Copy':
                evalCopy(ctx, u)
            elif u.name=='InsertData':
                evalInsertData(ctx, u)
            elif u.name=='DeleteData':
                evalDeleteData(ctx, u)
            elif u.name=='DeleteWhere':
                evalDeleteWhere(ctx, u)
            elif u.name=='Modify':
                evalModify(ctx, u)
            else: 
                raise Exception('Unknown update operation: %s'%(u,))
        except: 
            if not u.silent: raise



    
