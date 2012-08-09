import re
import operator as pyop # python operators

from rdflib_sparql.parserutils import CompValue
from rdflib import BNode, Variable, Literal, XSD

from pyparsing import ParseResults

from rdflib_sparql.sparql import SPARQLError, NotBoundError

""" 
This contains evaluation functions for expressions 

They get bound as instances-methods to the CompValue objects from parserutils

"""


def Builtin_REGEX(expr, ctx):
    """
    Invokes the XPath fn:matches function to match text against a regular
    expression pattern.
    The regular expression language is defined in XQuery 1.0 and XPath 2.0
    Functions and Operators section 7.6.1 Regular Expression Syntax
    """

    text = expr.text
    pattern = expr.pattern
    flags = expr.flags

    if flags:
        cFlag = 0

        # Maps XPath REGEX flags (http://www.w3.org/TR/xpath-functions/#flags)
        # to Python's re flags
        flagMap=dict([('i', re.IGNORECASE), ('s', re.DOTALL), ('m', re.MULTILINE)])
        cFlag=reduce(pyop.or_, [flagMap.get(f,0) for f in flags])

        return bool(re.compile(pattern,cFlag).search(text))

    else:
        return bool(re.compile(pattern).search(text))

def UnaryNot(expr,ctx):    
    return EBV(expr.expr)

def UnaryMinus(expr,ctx):
    return -numeric(expr.expr)

def MultiplicativeExpression(expr,ctx):

    # because of the way the mul-expr production handled operator precedence
    # we sometimes have nothing to do
    if not expr.other: 
        return expr.expr

    res=numeric(expr.expr)
    for op,e in zip(expr.op, expr.other): 
        e=numeric(e)
        if op=='*':
            res*=e
        else: 
            res/=e

    return Literal(res)

def AdditiveExpression(expr,ctx):

    # because of the way the add-expr production handled operator precedence
    # we sometimes have nothing to do
    if not expr.other: 
        return expr.expr

    res=numeric(expr.expr)
    for op,e in zip(expr.op, expr.other): 
        e=numeric(e)
        if op=='+':
            res+=e
        else: 
            res-=e

    return Literal(res)

def RelationalExpression(e, ctx):

    expr=e.expr
    other=e.other

    # because of the way the add-expr production handled operator precedence
    # we sometimes have nothing to do
    if not other: 
        return expr

    ops=dict( [ ('>', pyop.gt), 
                ('<', pyop.lt),
                ('=', pyop.eq),
                ('!=', pyop.ne),
                ('>=', pyop.ge),
                ('<=', pyop.le),
                ('IN', pyop.contains),
                ('NOT IN', lambda x,y: not pyop.contains(x,y))] )
    
    if isinstance(expr, Variable): raise NotBoundError()

    if not isinstance(expr, Literal): raise SPARQLError()
    if not isinstance(other, Literal): raise SPARQLError()

    return ops[e.op](expr, other)
    
    
    
    
    
    

def numeric(expr): 
    """
    return a number from a literal
    http://www.w3.org/TR/xpath20/#promotion

    or TypeError
    """    

    if not isinstance(expr, Literal): 
        raise TypeError("%s is not a literal!"%expr)

    if expr.datatype not in (XSD.float, XSD.double, 
                         XSD.decimal, XSD.integer, 
                         XSD.nonPositiveInteger, XSD.negativeInteger, 
                         XSD.nonNegativeInteger, XSD.positiveInteger, 
                         XSD.unsignedLong, XSD.unsignedInt, XSD.unsignedShort, XSD.unsignedByte, 
                         XSD.long, XSD.int, XSD.short, XSD.byte ):
        raise TypeError("%s does not have a numeric datatype!"%expr)
    
    return expr.toPython()

def EBV(rt):
    """
    * If the argument is a typed literal with a datatype of xsd:boolean,
      the EBV is the value of that argument.
    * If the argument is a plain literal or a typed literal with a
      datatype of xsd:string, the EBV is false if the operand value
      has zero length; otherwise the EBV is true.
    * If the argument is a numeric type or a typed literal with a datatype
      derived from a numeric type, the EBV is false if the operand value is
      NaN or is numerically equal to zero; otherwise the EBV is true.
    * All other arguments, including unbound arguments, produce a type error.

    """

    if isinstance(rt, Literal):

        if rt.datatype == XSD.boolean:
            ebv = rt.toPython()

        elif rt.datatype == XSD.string or rt.datatype is None:
            ebv = len(rt) > 0

        else:
            pyRT = rt.toPython()

            if isinstance(pyRT,Literal):
                #Type error, see: http://www.w3.org/TR/rdf-sparql-query/#ebv
                raise TypeError("http://www.w3.org/TR/rdf-sparql-query/#ebv")
            else:
                ebv = pyRT != 0

        return ebv

    else:
        raise TypeError("http://www.w3.org/TR/rdf-sparql-query/#ebv")
