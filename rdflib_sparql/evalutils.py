
from rdflib import Variable, Literal

from rdflib_sparql.operators import EBV
from rdflib_sparql.parserutils import Expr, CompValue
from rdflib_sparql.sparql import SPARQLError, NotBoundError

def _diff(a,b, expr): 
    res=set()
    for x in a: 
        if all(not x.compatible(y) or not _ebv(expr,x.merge(y)) for y in b): 
            res.add(x)

    return res

def _minus(a,b): 
    res=set()
    for x in a: 
        if all(not x.compatible(y) for y in b):
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
    elif isinstance(expr, Variable): 
        try: 
            return EBV(ctx[expr])
        except: 
            return False
    return False

def _eval(expr, ctx):
    if isinstance(expr, Literal): 
        return expr
    if isinstance(expr, Expr):         
        return expr.eval(ctx)
    elif isinstance(expr, Variable): 
        try: 
            return ctx[expr]
        except KeyError: 
            return NotBoundError("Variable %s is not bound"%expr)
    elif isinstance(expr, CompValue): 
        raise Exception("Weird - _eval got a CompValue without evalfn! %r"%expr)
    else: 
        raise Exception("Cannot eval thing: %s (%s)"%(expr, type(expr)))


def _filter(a,expr): 
#    import pdb; pdb.set_trace()
    for c in a:
        if _ebv(expr, c):
            yield c
