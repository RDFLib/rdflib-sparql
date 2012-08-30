import re
import operator as pyop # python operators

from rdflib_sparql.parserutils import CompValue, Expr
from rdflib import BNode, Variable, Literal, XSD
from rdflib.term import Node

from pyparsing import ParseResults

from rdflib_sparql.sparql import SPARQLError, NotBoundError

""" 
This contains evaluation functions for expressions 

They get bound as instances-methods to the CompValue objects from parserutils
using setEvalFn

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

        return Literal(bool(re.compile(pattern,cFlag).search(text)))

    else:
        return Literal(bool(re.compile(pattern).search(text)))

def Builtin_STRLEN(e, ctx):
    l=e.arg
    if not isinstance(l,Literal): raise SPARQLError('Can only get length of literal: %s'%l)
    
    return Literal(len(l))

def Builtin_STR(e, ctx):
    arg=e.arg
    #if not isinstance(l,Literal): raise SPARQLError('Can only get length of literal: %s'%l)
    
    return unicode(arg) # hmm


def Builtin_LCASE(e, ctx):    
    l=e.arg
    if not isinstance(l,Literal): raise SPARQLError('Can only lower-case literal: %s'%l)
    
    return Literal(l.tolower())

def Builtin_LANGMATCHES(e,ctx):
    langTag=e.arg1
    langRange=e.arg2

    if not isinstance(langTag, Literal): raise SPARQLError('Expected a string/literal')
    if not isinstance(langRange, Literal): raise SPARQLError('Expected a string/literal')

    return Literal(_lang_range_check(langRange,langTag))
    
    

def Builtin_UCASE(e, ctx):    
    l=e.arg
    if not isinstance(l,Literal): raise SPARQLError('Can only upper-case literal: %s'%l)
    
    return Literal(l.toupper())


def Builtin_LANG(e,ctx):
    l=e.arg
    if not isinstance(l,Literal): raise SPARQLError('Can only get language of literal: %s'%l)
    
    return Literal(l.language)

def Builtin_DATATYPE(e,ctx):
    l=e.arg
    if not isinstance(l,Literal): raise SPARQLError('Can only get datatype of literal: %s'%l)
    
    return l.datatype

def Builtin_sameTerm(e,ctx):
    a=e.arg1
    b=e.arg2
    return Literal(a==b)

def Builtin_BOUND(e, ctx):
    n=e.get('arg', variables=True)
    
    return Literal(not isinstance(n, Variable))

def UnaryNot(expr,ctx):    
    return Literal(EBV(expr.expr))

def UnaryMinus(expr,ctx):
    return Literal(-numeric(expr.expr))

def MultiplicativeExpression(e,ctx):

    expr=e.expr
    other=e.other

    # because of the way the mul-expr production handled operator precedence
    # we sometimes have nothing to do
    if other is None: 
        return expr

    res=numeric(expr)
    for op,e in zip(e.op, other): 
        e=numeric(e)
        if op=='*':
            res*=e
        else: 
            res/=e

    return Literal(res)

def AdditiveExpression(e,ctx):

    expr=e.expr
    other=e.other

    # because of the way the add-expr production handled operator precedence
    # we sometimes have nothing to do
    if other is None: 
        return expr

    res=numeric(expr)
    for op,e in zip(e.op, other): 
        e=numeric(e)
        if op=='+':
            res+=e
        else: 
            res-=e

    return Literal(res)


XSD_DTs=set((XSD.integer, XSD.decimal, XSD.float, XSD.double, XSD.string, XSD.boolean, XSD.dateTime, XSD.nonPositiveInteger, XSD.negativeInteger, XSD.long, XSD.int, XSD.short, XSD.byte, XSD.nonNegativeInteger, XSD.unsignedLong, XSD.unsignedInt, XSD.unsignedShort, XSD.unsignedByte, XSD.positiveInteger))

def RelationalExpression(e, ctx):

    expr=e.expr
    other=e.other
    op=e.op

    # because of the way the add-expr production handled operator precedence
    # we sometimes have nothing to do
    if other==None: 
        return expr

    ops=dict( [ ('>', pyop.gt), 
                ('<', pyop.lt),
                ('=', pyop.eq),
                ('!=', pyop.ne),
                ('>=', pyop.ge),
                ('<=', pyop.le),
                ('IN', pyop.contains),
                ('NOT IN', lambda x,y: not pyop.contains(x,y))] )

    #import pdb ; pdb.set_trace()

    if not op in ('=', '!='): 
        if not isinstance(expr, Literal): raise SPARQLError("Compare non-literals is an error: %s"%expr )
        if not isinstance(other, Literal): raise SPARQLError("Compare non-literals is an error: %s"%other )
    else:
        if not isinstance(expr, Node): raise SPARQLError('I cannot compare this non-node: %s'%expr)
        if not isinstance(other, Node): raise SPARQLError('I cannot compare this non-node: %s'%other)

        if type(expr)!=type(other): raise SPARQLError('Comparing different types of RDF terms is an error!')

        if isinstance(expr, Literal) and isinstance(other, Literal): 
            if unicode(expr)!=unicode(other):
                if expr.datatype and expr.datatype not in XSD_DTs: raise SPARQLError('I do not know how to compare literals with datatype: %s'%expr.datatype)
                if other.datatype and other.datatype not in XSD_DTs: raise SPARQLError('I do not know how to compare literals with datatype: %s'%other.datatype)

    return Literal(ops[op](expr, other))
    

def ConditionalAndExpression(e, ctx):

    # TODO: handle returned errors

    expr=e.expr
    other=e.other

    # because of the way the add-expr production handled operator precedence
    # we sometimes have nothing to do
    if other is None: 
        return expr
    
    return Literal(all(EBV(x) for x in [expr]+other))

def ConditionalOrExpression(e, ctx):

    # TODO: handle errors

    expr=e.expr
    other=e.other

    # because of the way the add-expr production handled operator precedence
    # we sometimes have nothing to do
    if other is None: 
        return expr
    
    return Literal(any(EBV(x) for x in [expr]+other))
    

def and_(*args): 
    if len(args)==1: 
        return args[0]
    
    a={ 'expr': args[0], 'other': list(args[1:]) }

    return Expr('ConditionalAndExpression', a, ConditionalAndExpression)
    

def simplify(expr): 
    if isinstance(expr, ParseResults) and len(expr)==1: 
        return simplify(expr[0])

    if isinstance(expr, (list,ParseResults)): 
        return map(simplify, expr)
    if not isinstance(expr, CompValue): return expr
    if expr.name.endswith('Expression'):
        if expr.other is None:
            return simplify(expr.expr)
        
    for k in expr.keys():
        expr[k]=simplify(expr[k])
        #expr['expr']=simplify(expr.expr)
        #    expr['other']=simplify(expr.other)

    return expr

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
            return rt.toPython()

        elif rt.datatype == XSD.string or rt.datatype is None:
            return len(rt) > 0

        else:
            pyRT = rt.toPython()

            if isinstance(pyRT,Literal):
                #Type error, see: http://www.w3.org/TR/rdf-sparql-query/#ebv
                raise TypeError("http://www.w3.org/TR/rdf-sparql-query/#ebv - Could not determine the EBV for : %s"%rt)
            else:
                return pyRT != 0

    else:
        raise TypeError("http://www.w3.org/TR/rdf-sparql-query/#ebv - Only literals have Boolean values! %s"%rt)



def _lang_range_check(range, lang) :
	"""
	Implementation of the extended filtering algorithm, as defined in point 3.3.2,
	of U{RFC 4647<http://www.rfc-editor.org/rfc/rfc4647.txt>}, on matching language ranges and language tags.
	Needed to handle the C{rdf:PlainLiteral} datatype.
	@param range: language range
	@param lang: language tag
	@rtype: boolean

        @author: U{Ivan Herman<a href="http://www.w3.org/People/Ivan/">}

        Taken from http://dev.w3.org/2004/PythonLib-IH/RDFClosure/RestrictedDatatype.py

	"""
	def _match(r,l) :
		"""Matching of a range and language item: either range is a wildcard or the two are equal
		@param r: language range item
		@param l: language tag item
		@rtype: boolean
		"""
		return r == '*' or r == l
	
	rangeList = range.strip().lower().split('-')
	langList  = lang.strip().lower().split('-')
	if not _match(rangeList[0], langList[0]) : return False
	
	rI = 1
	rL = 1
	while rI < len(rangeList) :
		if rangeList[rI] == '*' :
			rI += 1
			continue
		if rL >= len(langList) :
			return False
		if _match(rangeList[rI], langList[rL]) :
			rI += 1
			rL += 1
			continue
		if len(langList[rL]) == 1 :
			return False
		else :
			rL += 1
			continue
	return True
