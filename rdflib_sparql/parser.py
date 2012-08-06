
import re


from pyparsing import Literal, Regex, Optional, OneOrMore, ZeroOrMore, \
    Forward, ParseException, Suppress, Combine, restOfLine, Group, Empty
from pyparsing import CaselessKeyword as Keyword # watch out :) 
#from pyparsing import Keyword as CaseSensitiveKeyword 

from parserutils import Comp, Param

import rdflib_sparql.components as components

import rdflib

DEBUG=False

# ---------------- ACTIONS 

def neg(literal): 
    try: 
        return rdflib.Literal(-literal, datatype=literal.datatype)
    except Exception, e:
        print e
        

def setLanguage(terms):
    terms[0].language=terms[1]
    return terms[0]

def setDataType(terms):
    terms[0].datatype=terms[1]
    return terms[0]

def expandTriples(terms):
    
    """
    Expand ; and , syntax for repeat predicates, subjects
    """
    try:
        res=[]
        if DEBUG:
            print "Terms", terms
        for i,t in enumerate(terms):
            if t==',':
                res.append(res[i-3])
                res.append(res[i-2])
            elif t==';':
                res.append(res[i-2])
            elif isinstance(t,list): 
                res.append(t[0])
                res+=t
            elif t!='.': 
                res.append(t)

        return res
        # print res
        # assert len(res)%3 == 0, "Length of triple-list is not divisible by 3: %d!"%len(res)

        # return [tuple(res[i:i+3]) for i in range(len(res)/3)]
    except: 
        if DEBUG:
            import traceback
            traceback.print_exc()
        raise
        

def expandBNodeTriples(terms):
    """
    expand [ ?p ?o ] syntax for implicit bnodes
    """
    try:
        if DEBUG:
            print "Bnode terms",terms
            print "1",terms[0]
            print "2",[rdflib.BNode()]+terms.asList()[0]
        return [ expandTriples([rdflib.BNode()]+terms.asList()[0]) ] 
    except Exception as e: 
        if DEBUG:
            print ">>>>>>>>",e
        raise

def expandCollection(terms):
    """
    expand ( 1 2 3 ) notation for collections
    """
    if DEBUG:
        print "Collection: ",terms

    res=[]
    for x in terms: 
        b=rdflib.BNode()
        if res:
            res+=[res[-3],rdflib.RDF.rest,b,b,rdflib.RDF.first,x]
        else: 
            res+=[b,rdflib.RDF.first,x]
    res+=[b,rdflib.RDF.rest, rdflib.RDF.nil]

    if DEBUG: 
        print "CollectionOut", res
    return [res]



# SPARQL Grammar from http://www.w3.org/TR/sparql11-query/#grammar


# ------ TERMINALS --------------
 
# [139] IRIREF ::= '<' ([^<>"{}|^`\]-[#x00-#x20])* '>'
IRIREF = Combine(Suppress('<') + Regex(r'[^<>"{}|^`\\%s]*' % ''.join('\\x%02X' % i for i in range(33))) + Suppress('>'))
IRIREF.setParseAction(lambda x: rdflib.URIRef(x[0]))

# [164] P_CHARS_BASE ::= [A-Z] | [a-z] | [#x00C0-#x00D6] | [#x00D8-#x00F6] | [#x00F8-#x02FF] | [#x0370-#x037D] | [#x037F-#x1FFF] | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]

PN_CHARS_BASE_re = u'A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\U00010000-\U000EFFFF'

# [165] PN_CHARS_U ::= PN_CHARS_BASE | '_'
PN_CHARS_U_re = '_'+PN_CHARS_BASE_re

# [167] PN_CHARS ::= PN_CHARS_U | '-' | [0-9] | #x00B7 | [#x0300-#x036F] | [#x203F-#x2040]
PN_CHARS_re = u'\\-0-9\u00B7\u0300-\u036F\u203F-\u2040'+PN_CHARS_U_re
#PN_CHARS = Regex(u'[%s]'%PN_CHARS_re, flags=re.U)

# [168] PN_PREFIX ::= PN_CHARS_BASE ((PN_CHARS|'.')* PN_CHARS)?
PN_PREFIX = Regex(ur'[%s](?:[%s\.]*[%s])?'%(PN_CHARS_BASE_re, PN_CHARS_re, PN_CHARS_re), flags=re.U)

# [140] PNAME_NS ::= PN_PREFIX? ':'
PNAME_NS = Combine(Optional(PN_PREFIX) + Suppress(':'))

# [173] PN_LOCAL_ESC ::= '\' ( '_' | '~' | '.' | '-' | '!' | '$' | '&' | "'" | '(' | ')' | '*' | '+' | ',' | ';' | '=' | '/' | '?' | '#' | '@' | '%' )

PN_LOCAL_ESC = Regex('\\\\[_~\\.\\-!$&"\'()*+,;=/?#@%]' )
PN_LOCAL_ESC.setParseAction(lambda x: x[0][1:])

# [172] HEX ::= [0-9] | [A-F] | [a-f]
# HEX = Regex('[0-9A-Fa-f]') # not needed

# [171] PERCENT ::= '%' HEX HEX
PERCENT = Regex('%[0-9a-fA-F]{2}')
PERCENT.setParseAction(lambda x: unichr(int(x[0][1:],16)))

# [170] PLX ::= PERCENT | PN_LOCAL_ESC
PLX = PERCENT | PN_LOCAL_ESC

# [169] PN_LOCAL ::= (PN_CHARS_U | ':' | [0-9] | PLX ) ((PN_CHARS | '.' | ':' | PLX)* (PN_CHARS | ':' | PLX) )?
PN_LOCAL = Combine((Regex(u'[%s0-9:]'%PN_CHARS_U_re, flags=re.U) | PLX ) + ZeroOrMore((Regex(u'[%s\\.:]'%PN_CHARS_re, flags=re.U) | PLX) + Optional(Regex(u'[%s:]'%PN_CHARS_re, flags=re.U) | PLX) ))


# [141] PNAME_LN ::= PNAME_NS PN_LOCAL
PNAME_LN = PNAME_NS + PN_LOCAL.leaveWhitespace()
PNAME_LN.setParseAction(lambda x: [components.PName(*x)])

# [142] BLANK_NODE_LABEL ::= '_:' ( PN_CHARS_U | [0-9] ) ((PN_CHARS|'.')* PN_CHARS)?
BLANK_NODE_LABEL = Regex(ur'_:[0-9%s](?:[\.%s]*[%s])?'%(PN_CHARS_U_re, PN_CHARS_re, PN_CHARS_re), flags=re.U)
BLANK_NODE_LABEL.setParseAction(lambda x: rdflib.BNode(x[0]))


# [166] VARNAME ::= ( PN_CHARS_U | [0-9] ) ( PN_CHARS_U | [0-9] | #x00B7 | [#x0300-#x036F] | [#x203F-#x2040] )*
VARNAME = Regex(u'[%s0-9][%s0-9\u00B7\u0300-\u036F\u203F-\u2040]*'%(PN_CHARS_U_re, PN_CHARS_U_re), flags=re.U) 

# [143] VAR1 ::= '?' VARNAME
VAR1 = Combine(Suppress('?') + VARNAME)

# [144] VAR2 ::= '$' VARNAME
VAR2 = Combine(Suppress('$') + VARNAME)

# [145] LANGTAG ::= '@' [a-zA-Z]+ ('-' [a-zA-Z0-9]+)*
LANGTAG = Combine(Suppress('@')+Regex('[a-zA-Z]+(?:-[a-zA-Z0-9]+)*'))

# [146] INTEGER ::= [0-9]+
INTEGER = Regex(r"[0-9]+")
#INTEGER.setResultsName('integer')
INTEGER.setParseAction(lambda x: rdflib.Literal(x[0], datatype=rdflib.XSD.integer))

# [155] EXPONENT ::= [eE] [+-]? [0-9]+
EXPONENT_re = '[eE][+-]?[0-9]+'

# [147] DECIMAL ::= [0-9]* '.' [0-9]+
DECIMAL = Regex(r'[0-9]*\.[0-9]+') # (?![eE])
#DECIMAL.setResultsName('decimal')
DECIMAL.setParseAction(lambda x: rdflib.Literal(x[0], datatype=rdflib.XSD.decimal))

# [148] DOUBLE ::= [0-9]+ '.' [0-9]* EXPONENT | '.' ([0-9])+ EXPONENT | ([0-9])+ EXPONENT
DOUBLE = Regex(r'[0-9]+\.[0-9]*%(e)s|\.([0-9])+%(e)s|[0-9]+%(e)s'%{'e':EXPONENT_re})
#DOUBLE.setResultsName('double')
DOUBLE.setParseAction(lambda x: rdflib.Literal(x[0], datatype=rdflib.XSD.double))


# [149] INTEGER_POSITIVE ::= '+' INTEGER
INTEGER_POSITIVE = Suppress('+') + INTEGER.copy().leaveWhitespace()

# [150] DECIMAL_POSITIVE ::= '+' DECIMAL
DECIMAL_POSITIVE = Suppress('+') + DECIMAL.copy().leaveWhitespace()

# [151] DOUBLE_POSITIVE ::= '+' DOUBLE
DOUBLE_POSITIVE = Suppress('+') + DOUBLE.copy().leaveWhitespace()

# [152] INTEGER_NEGATIVE ::= '-' INTEGER
INTEGER_NEGATIVE = Suppress('-') + INTEGER.copy().leaveWhitespace()
INTEGER_NEGATIVE.setParseAction(lambda x: neg(x[0]))

# [153] DECIMAL_NEGATIVE ::= '-' DECIMAL
DECIMAL_NEGATIVE = Suppress('-') + DECIMAL.copy().leaveWhitespace()
DECIMAL_NEGATIVE.setParseAction(lambda x: neg(x[0]))

# [154] DOUBLE_NEGATIVE ::= '-' DOUBLE
DOUBLE_NEGATIVE = Suppress('-') + DOUBLE.copy().leaveWhitespace()
DOUBLE_NEGATIVE.setParseAction(lambda x: neg(x[0]))

# [160] ECHAR ::= '\' [tbnrf\"']
# ECHAR = Regex('\\\\[tbnrf"\']')


# [158] STRING_LITERAL_LONG1 ::= "'''" ( ( "'" | "''" )? ( [^'\] | ECHAR ) )* "'''"
#STRING_LITERAL_LONG1 = Literal("'''") + ( Optional( Literal("'") | "''" ) + ZeroOrMore( ~ Literal("'\\") | ECHAR ) ) + "'''"
STRING_LITERAL_LONG1 = Regex(ur"'''((?:'|'')?(?:[^'\\]|\\['ntbrf\\]))*'''")
STRING_LITERAL_LONG1.setParseAction(lambda x: rdflib.Literal(x[0][3:-3]))

# [159] STRING_LITERAL_LONG2 ::= '"""' ( ( '"' | '""' )? ( [^"\] | ECHAR ) )* '"""'
#STRING_LITERAL_LONG2 = Literal('"""') + ( Optional( Literal('"') | '""' ) + ZeroOrMore( ~ Literal('"\\') | ECHAR ) ) +  '"""'
STRING_LITERAL_LONG2 = Regex(ur'"""(?:(?:"|"")?(?:[^"\\]|\\["ntbrf\\]))*"""')
STRING_LITERAL_LONG2.setParseAction(lambda x: rdflib.Literal(x[0][3:-3]))

# [156] STRING_LITERAL1 ::= "'" ( ([^#x27#x5C#xA#xD]) | ECHAR )* "'"
#STRING_LITERAL1 = Literal("'") + ZeroOrMore( Regex(u'[^\u0027\u005C\u000A\u000D]',flags=re.U) | ECHAR ) + "'"

STRING_LITERAL1 = Regex(ur"'(?:[^\u0027\\\u000A\u000D]|\\['ntbrf])*'(?!')", flags=re.U)
STRING_LITERAL1.setParseAction(lambda x: rdflib.Literal(x[0][1:-1]))

# [157] STRING_LITERAL2 ::= '"' ( ([^#x22#x5C#xA#xD]) | ECHAR )* '"'
#STRING_LITERAL2 = Literal('"') + ZeroOrMore ( Regex(u'[^\u0022\u005C\u000A\u000D]',flags=re.U) | ECHAR ) + '"'

STRING_LITERAL2 = Regex(ur'"(?:[^\u0022\\\u000A\u000D]|\\["ntbrf])*"(?!")', flags=re.U)
STRING_LITERAL2.setParseAction(lambda x: rdflib.Literal(x[0][1:-1]))

# [161] NIL ::= '(' WS* ')'
NIL = Literal('(') + ')'
NIL.setParseAction(lambda x: rdflib.RDF.nil)

# [162] WS ::= #x20 | #x9 | #xD | #xA
# Not needed?
# WS = #x20 | #x9 | #xD | #xA
# [163] ANON ::= '[' WS* ']'
ANON = Literal('[') + ']'
ANON.setParseAction(lambda x: rdflib.BNode())

#A = CaseSensitiveKeyword('a')
A = Literal('a')
A.setParseAction(lambda x: rdflib.RDF.type)


# ------ NON-TERMINALS --------------

# [5] BaseDecl ::= 'BASE' IRIREF
BaseDecl = Comp('Base', Keyword('BASE') + Param('iri',IRIREF))

# [6] PrefixDecl ::= 'PREFIX' PNAME_NS IRIREF
PrefixDecl = Comp('PrefixDecl', Keyword('PREFIX') + Param('prefix',PNAME_NS) + Param('iri',IRIREF))

# [4] Prologue ::= ( BaseDecl | PrefixDecl )*
Prologue = Group ( ZeroOrMore( BaseDecl | PrefixDecl ) ) 

# [108] Var ::= VAR1 | VAR2
Var = VAR1 | VAR2
Var.setParseAction(lambda x: rdflib.term.Variable(x[0]))

# [137] PrefixedName ::= PNAME_LN | PNAME_NS
PrefixedName = PNAME_LN | PNAME_NS

# [136] iri ::= IRIREF | PrefixedName
iri = IRIREF | PrefixedName

# [135] String ::= STRING_LITERAL1 | STRING_LITERAL2 | STRING_LITERAL_LONG1 | STRING_LITERAL_LONG2
String = STRING_LITERAL_LONG1 | STRING_LITERAL_LONG2 | STRING_LITERAL1 | STRING_LITERAL2 

# [129] RDFLiteral ::= String ( LANGTAG | ( '^^' iri ) )?
LangTaggedLiteral = String + Optional( LANGTAG ).leaveWhitespace()
LangTaggedLiteral.setParseAction(setLanguage)
DataTypedLiteral = String + Optional( Combine(Suppress('^^') + iri) ).leaveWhitespace()
DataTypedLiteral.setParseAction(setDataType)
RDFLiteral = LangTaggedLiteral | DataTypedLiteral | String

# [132] NumericLiteralPositive ::= INTEGER_POSITIVE | DECIMAL_POSITIVE | DOUBLE_POSITIVE
NumericLiteralPositive = DOUBLE_POSITIVE | DECIMAL_POSITIVE | INTEGER_POSITIVE 

# [133] NumericLiteralNegative ::= INTEGER_NEGATIVE | DECIMAL_NEGATIVE | DOUBLE_NEGATIVE
NumericLiteralNegative = DOUBLE_NEGATIVE | DECIMAL_NEGATIVE | INTEGER_NEGATIVE

# [131] NumericLiteralUnsigned ::= INTEGER | DECIMAL | DOUBLE
NumericLiteralUnsigned = DOUBLE | DECIMAL | INTEGER

# [130] NumericLiteral ::= NumericLiteralUnsigned | NumericLiteralPositive | NumericLiteralNegative
NumericLiteral = NumericLiteralUnsigned | NumericLiteralPositive | NumericLiteralNegative

# [134] BooleanLiteral ::= 'true' | 'false'
BooleanLiteral = Keyword('true').setParseAction(lambda : rdflib.Literal(True)) |\
    Keyword('false').setParseAction(lambda : rdflib.Literal(False))

# [138] BlankNode ::= BLANK_NODE_LABEL | ANON
BlankNode = BLANK_NODE_LABEL | ANON

# [109] GraphTerm ::= iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | NIL
GraphTerm = iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | NIL

# [106] VarOrTerm ::= Var | GraphTerm
VarOrTerm = Var | GraphTerm

# [107] VarOrIri ::= Var | iri
VarOrIri = Var | iri

# [46] GraphRef ::= 'GRAPH' iri
GraphRef = Comp('GraphRef', Keyword('GRAPH') + Param('iri', iri))

# [47] GraphRefAll ::= GraphRef | 'DEFAULT' | 'NAMED' | 'ALL'
GraphRefAll = GraphRef | Keyword('DEFAULT') | Keyword('NAMED') | Keyword('ALL')

# [45] GraphOrDefault ::= 'DEFAULT' | 'GRAPH'? iri
GraphOrDefault = Keyword('DEFAULT') | Optional(Keyword('GRAPH')) + iri

# [65] DataBlockValue ::= iri | RDFLiteral | NumericLiteral | BooleanLiteral | 'UNDEF'
DataBlockValue = iri | RDFLiteral | NumericLiteral | BooleanLiteral | Keyword('UNDEF')

# [78] Verb ::= VarOrIri | A
Verb = VarOrIri | A



# [85] VerbSimple ::= Var
VerbSimple = Var

# [97] Integer ::= INTEGER
Integer = INTEGER





TriplesNode = Forward()
TriplesNodePath = Forward()

# [104] GraphNode ::= VarOrTerm | TriplesNode
GraphNode = VarOrTerm | TriplesNode

# [105] GraphNodePath ::= VarOrTerm | TriplesNodePath
GraphNodePath = VarOrTerm | TriplesNodePath


# [93] PathMod ::= '?' | '*' | '+'
PathMod = Literal('?') | '*' | '+'

# [96] PathOneInPropertySet ::= iri | A | '^' ( iri | A )
PathOneInPropertySet = iri | A | '^' + ( iri | A )

Path = Forward()

# [95] PathNegatedPropertySet ::= PathOneInPropertySet | '(' ( PathOneInPropertySet ( '|' PathOneInPropertySet )* )? ')'
PathNegatedPropertySet = PathOneInPropertySet | '(' + Optional( PathOneInPropertySet + ZeroOrMore( '|' + PathOneInPropertySet ) ) + ')'

# [94] PathPrimary ::= iri | A | '!' PathNegatedPropertySet | '(' Path ')' | 'DISTINCT' '(' Path ')'
PathPrimary = iri | A | '!' + PathNegatedPropertySet | '(' + Path + ')' | Keyword('DISTINCT') + '(' + Path + ')'

# [91] PathElt ::= PathPrimary Optional(PathMod)
PathElt = (PathPrimary + Optional(PathMod)).leaveWhitespace()

# [92] PathEltOrInverse ::= PathElt | '^' PathElt
PathEltOrInverse = PathElt | '^' + PathElt

# [90] PathSequence ::= PathEltOrInverse ( '/' PathEltOrInverse )*
PathSequence = PathEltOrInverse + ZeroOrMore( '/' + PathEltOrInverse )


# [89] PathAlternative ::= PathSequence ( '|' PathSequence )*
PathAlternative = PathSequence + ZeroOrMore( '|' + PathSequence )

# [88] Path ::= PathAlternative
Path << Group ( PathAlternative ) 

# [84] VerbPath ::= Path
VerbPath = Path

# [87] ObjectPath ::= GraphNodePath
ObjectPath = GraphNodePath

# [86] ObjectListPath ::= ObjectPath ( ',' ObjectPath )*
ObjectListPath = ObjectPath + ZeroOrMore( ',' + ObjectPath )


Expression = Forward()

# [72] ExpressionList ::= NIL | '(' Expression ( ',' Expression )* ')'
ExpressionList = NIL | '(' + Expression + ZeroOrMore( ',' + Expression ) + ')'

GroupGraphPattern = Forward()



# [102] Collection ::= '(' OneOrMore(GraphNode) ')'
Collection = Suppress('(') + OneOrMore(GraphNode) + Suppress(')')
Collection.setParseAction(expandCollection)

# [103] CollectionPath ::= '(' OneOrMore(GraphNodePath) ')'
CollectionPath = Suppress('(') + OneOrMore(GraphNodePath) + Suppress(')')
CollectionPath.setParseAction(expandCollection)

# [80] Object ::= GraphNode
Object = GraphNode

# [79] ObjectList ::= Object ( ',' Object )*
ObjectList = Object + ZeroOrMore( ',' + Object )

# [83] PropertyListPathNotEmpty ::= ( VerbPath | VerbSimple ) ObjectListPath ( ';' ( ( VerbPath | VerbSimple ) ObjectList )? )*
PropertyListPathNotEmpty = ( VerbPath | VerbSimple ) + ObjectListPath + ZeroOrMore( ';' + Optional( ( VerbPath | VerbSimple ) + ObjectList ) )

# [82] PropertyListPath ::= Optional(PropertyListPathNotEmpty)
PropertyListPath = Optional(PropertyListPathNotEmpty)

# [77] PropertyListNotEmpty ::= Verb ObjectList ( ';' ( Verb ObjectList )? )*
PropertyListNotEmpty = Verb + ObjectList + ZeroOrMore( ';' + Optional( Verb + ObjectList ) )

# [76] PropertyList ::= Optional(PropertyListNotEmpty)
PropertyList = Optional(PropertyListNotEmpty)

# [99] BlankNodePropertyList ::= '[' PropertyListNotEmpty ']'
BlankNodePropertyList = Group(Suppress('[') + PropertyListNotEmpty + Suppress(']'))
BlankNodePropertyList.setParseAction(expandBNodeTriples)

# [101] BlankNodePropertyListPath ::= '[' PropertyListPathNotEmpty ']'
BlankNodePropertyListPath = Group( Suppress('[') + PropertyListPathNotEmpty + Suppress(']') )
BlankNodePropertyListPath.setParseAction(expandBNodeTriples)

# [98] TriplesNode ::= Collection | BlankNodePropertyList
TriplesNode << ( Collection | BlankNodePropertyList )

# [100] TriplesNodePath ::= CollectionPath | BlankNodePropertyListPath
TriplesNodePath << ( CollectionPath | BlankNodePropertyListPath )

# [75] TriplesSameSubject ::= VarOrTerm PropertyListNotEmpty | TriplesNode PropertyList
TriplesSameSubject = VarOrTerm + PropertyListNotEmpty | TriplesNode + PropertyList 
TriplesSameSubject.setParseAction(expandTriples)

# [52] TriplesTemplate ::= TriplesSameSubject ( '.' Optional(TriplesTemplate) )?
TriplesTemplate = Forward()
TriplesTemplate << ( TriplesSameSubject + Optional( Suppress('.') + Optional(TriplesTemplate) ) )

# [51] QuadsNotTriples ::= 'GRAPH' VarOrIri '{' Optional(TriplesTemplate) '}'
QuadsNotTriples = Keyword('GRAPH') + VarOrIri + Group ( '{' +  Optional(TriplesTemplate)  + '}' )

# [50] Quads ::= Optional(TriplesTemplate) ( QuadsNotTriples '.'? Optional(TriplesTemplate) )*
Quads = Optional(TriplesTemplate) + ZeroOrMore( QuadsNotTriples + Optional(Suppress('.')) + Optional(TriplesTemplate) )

# [48] QuadPattern ::= '{' Quads '}'
QuadPattern = '{' + Quads + '}'

# [49] QuadData ::= '{' Quads '}'
QuadData = '{' + Quads + '}'

# [81] TriplesSameSubjectPath ::= VarOrTerm PropertyListPathNotEmpty | TriplesNodePath PropertyListPath
TriplesSameSubjectPath = VarOrTerm + PropertyListPathNotEmpty | TriplesNodePath + PropertyListPath
TriplesSameSubjectPath.setParseAction(expandTriples)

# [55] TriplesBlock ::= TriplesSameSubjectPath ( '.' Optional(TriplesBlock) )?
TriplesBlock = Forward()
TriplesBlock << ( TriplesSameSubjectPath + Optional( Suppress('.') + Optional(TriplesBlock) ) )


# [66] MinusGraphPattern ::= 'MINUS' GroupGraphPattern
MinusGraphPattern = Keyword('MINUS') + GroupGraphPattern

# [67] GroupOrUnionGraphPattern ::= GroupGraphPattern ( 'UNION' GroupGraphPattern )*
GroupOrUnionGraphPattern = GroupGraphPattern + ZeroOrMore( Keyword('UNION') + GroupGraphPattern )





# [122] RegexExpression ::= 'REGEX' '(' Expression ',' Expression ( ',' Expression )? ')'
RegexExpression = Comp('RegexExpression',Keyword('REGEX') + '(' + Param('text',Expression) + ',' + Param('pattern',Expression) + Optional( ',' + Param('flags',Expression) ) + ')')


# [123] SubstringExpression ::= 'SUBSTR' '(' Expression ',' Expression ( ',' Expression )? ')'
SubstringExpression = Keyword('SUBSTR') + '(' + Expression + ',' + Expression + Optional( ',' + Expression ) + ')'

# [124] StrReplaceExpression ::= 'REPLACE' '(' Expression ',' Expression ',' Expression ( ',' Expression )? ')'
StrReplaceExpression = Comp('StrReplaceExpression', Keyword('REPLACE') + '(' + Expression + ',' + Expression + ',' + Expression + Optional( ',' + Expression ) + ')' )

# [125] ExistsFunc ::= 'EXISTS' GroupGraphPattern
ExistsFunc = Keyword('EXISTS') + GroupGraphPattern

# [126] NotExistsFunc ::= 'NOT' 'EXISTS' GroupGraphPattern
NotExistsFunc = Keyword('NOT') + Keyword('EXISTS') + GroupGraphPattern


# [127] Aggregate ::= 'COUNT' '(' 'DISTINCT'? ( '*' | Expression ) ')'
# | 'SUM' '(' Optional('DISTINCT') Expression ')'
# | 'MIN' '(' Optional('DISTINCT') Expression ')'
# | 'MAX' '(' Optional('DISTINCT') Expression ')'
# | 'AVG' '(' Optional('DISTINCT') Expression ')'
# | 'SAMPLE' '(' Optional('DISTINCT') Expression ')'
# | 'GROUP_CONCAT' '(' Optional('DISTINCT') Expression ( ';' 'SEPARATOR' '=' String )? ')'

_Distinct = Optional(Keyword('DISTINCT'))
_AggregateParams = '(' + _Distinct + Expression + ')'

Aggregate = Keyword('COUNT') + '(' + _Distinct + ( '*' | Expression ) + ')' \
    | Keyword('SUM') + _AggregateParams \
    | Keyword('MIN') + _AggregateParams \
    | Keyword('MAX') + _AggregateParams \
    | Keyword('AVG') + _AggregateParams \
    | Keyword('SAMPLE') + _AggregateParams \
    | Keyword('GROUP_CONCAT') + '(' + _Distinct + Expression + Optional( ';' + Keyword('SEPARATOR') + '=' + String ) + ')'

# [121] BuiltInCall ::= Aggregate
# | 'STR' '(' + Expression + ')'
# | 'LANG' '(' + Expression + ')'
# | 'LANGMATCHES' '(' + Expression + ',' + Expression + ')'
# | 'DATATYPE' '(' + Expression + ')'
# | 'BOUND' '(' Var ')'
# | 'IRI' '(' + Expression + ')'
# | 'URI' '(' + Expression + ')'
# | 'BNODE' ( '(' + Expression + ')' | NIL )
# | 'RAND' NIL
# | 'ABS' '(' + Expression + ')'
# | 'CEIL' '(' + Expression + ')'
# | 'FLOOR' '(' + Expression + ')'
# | 'ROUND' '(' + Expression + ')'
# | 'CONCAT' ExpressionList
# | SubstringExpression
# | 'STRLEN' '(' + Expression + ')'
# | StrReplaceExpression
# | 'UCASE' '(' + Expression + ')'
# | 'LCASE' '(' + Expression + ')'
# | 'ENCODE_FOR_URI' '(' + Expression + ')'
# | 'CONTAINS' '(' + Expression + ',' + Expression + ')'
# | 'STRSTARTS' '(' + Expression + ',' + Expression + ')'
# | 'STRENDS' '(' + Expression + ',' + Expression + ')'
# | 'STRBEFORE' '(' + Expression + ',' + Expression + ')'
# | 'STRAFTER' '(' + Expression + ',' + Expression + ')'
# | 'YEAR' '(' + Expression + ')'
# | 'MONTH' '(' + Expression + ')'
# | 'DAY' '(' + Expression + ')'
# | 'HOURS' '(' + Expression + ')'
# | 'MINUTES' '(' + Expression + ')'
# | 'SECONDS' '(' + Expression + ')'
# | 'TIMEZONE' '(' + Expression + ')'
# | 'TZ' '(' + Expression + ')'
# | 'NOW' NIL
# | 'UUID' NIL
# | 'STRUUID' NIL
# | 'MD5' '(' + Expression + ')'
# | 'SHA1' '(' + Expression + ')'
# | 'SHA256' '(' + Expression + ')'
# | 'SHA384' '(' + Expression + ')'
# | 'SHA512' '(' + Expression + ')'
# | 'COALESCE' ExpressionList
# | 'IF' '(' Expression ',' Expression ',' Expression ')'
# | 'STRLANG' '(' + Expression + ',' + Expression + ')'
# | 'STRDT' '(' + Expression + ',' + Expression + ')'
# | 'sameTerm' '(' + Expression + ',' + Expression + ')'
# | 'isIRI' '(' + Expression + ')'
# | 'isURI' '(' + Expression + ')'
# | 'isBLANK' '(' + Expression + ')'
# | 'isLITERAL' '(' + Expression + ')'
# | 'isNUMERIC' '(' + Expression + ')'
# | RegexExpression
# | ExistsFunc
# | NotExistsFunc

BuiltInCall = Aggregate \
    | Keyword('STR') + '(' + Expression + ')' \
    | Keyword('LANG') + '(' + Expression + ')' \
    | Keyword('LANGMATCHES') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('DATATYPE') + '(' + Expression + ')' \
    | Keyword('BOUND') + '(' + Var + ')' \
    | Keyword('IRI') + '(' + Expression + ')' \
    | Keyword('URI') + '(' + Expression + ')' \
    | Keyword('BNODE') + ( '(' + Expression + ')' | NIL ) \
    | Keyword('RAND') + NIL \
    | Keyword('ABS') + '(' + Expression + ')' \
    | Keyword('CEIL') + '(' + Expression + ')' \
    | Keyword('FLOOR') + '(' + Expression + ')' \
    | Keyword('ROUND') + '(' + Expression + ')' \
    | Keyword('CONCAT') + ExpressionList \
    | SubstringExpression \
    | Keyword('STRLEN') + '(' + Expression + ')' \
    | StrReplaceExpression \
    | Keyword('UCASE') + '(' + Expression + ')' \
    | Keyword('LCASE') + '(' + Expression + ')' \
    | Keyword('ENCODE_FOR_URI') + '(' + Expression + ')' \
    | Keyword('CONTAINS') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('STRSTARTS') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('STRENDS') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('STRBEFORE') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('STRAFTER') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('YEAR') + '(' + Expression + ')' \
    | Keyword('MONTH') + '(' + Expression + ')' \
    | Keyword('DAY') + '(' + Expression + ')' \
    | Keyword('HOURS') + '(' + Expression + ')' \
    | Keyword('MINUTES') + '(' + Expression + ')' \
    | Keyword('SECONDS') + '(' + Expression + ')' \
    | Keyword('TIMEZONE') + '(' + Expression + ')' \
    | Keyword('TZ') + '(' + Expression + ')' \
    | Keyword('NOW') + NIL \
    | Keyword('UUID') + NIL \
    | Keyword('STRUUID') + NIL \
    | Keyword('MD5') + '(' + Expression + ')' \
    | Keyword('SHA1') + '(' + Expression + ')' \
    | Keyword('SHA256') + '(' + Expression + ')' \
    | Keyword('SHA384') + '(' + Expression + ')' \
    | Keyword('SHA512') + '(' + Expression + ')' \
    | Keyword('COALESCE') + ExpressionList \
    | Keyword('IF') + '(' + Expression + ',' + Expression + ',' + Expression + ')' \
    | Keyword('STRLANG') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('STRDT') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('sameTerm') + '(' + Expression + ',' + Expression + ')' \
    | Keyword('isIRI') + '(' + Expression + ')' \
    | Keyword('isURI') + '(' + Expression + ')' \
    | Keyword('isBLANK') + '(' + Expression + ')' \
    | Keyword('isLITERAL') + '(' + Expression + ')' \
    | Keyword('isNUMERIC') + '(' + Expression + ')' \
    | RegexExpression \
    | ExistsFunc \
    | NotExistsFunc


# [71] ArgList ::= NIL | '(' 'DISTINCT'? Expression ( ',' Expression )* ')'
ArgList = NIL | '(' + _Distinct + Expression + ZeroOrMore( ',' + Expression ) + ')'

# [128] iriOrFunction ::= iri Optional(ArgList)
iriOrFunction = iri + Optional(ArgList)

# [70] FunctionCall ::= iri ArgList
FunctionCall = iri + ArgList



# [16] SourceSelector ::= iri
SourceSelector = iri

# [14] DefaultGraphClause ::= SourceSelector
DefaultGraphClause = SourceSelector

# [15] NamedGraphClause ::= 'NAMED' SourceSelector
NamedGraphClause = Keyword('NAMED') + SourceSelector

# [13] DatasetClause ::= 'FROM' ( DefaultGraphClause | NamedGraphClause )
DatasetClause = Keyword('FROM') + ( DefaultGraphClause | NamedGraphClause )

# [20] GroupCondition ::= BuiltInCall | FunctionCall | '(' Expression ( 'AS' Var )? ')' | Var
GroupCondition = BuiltInCall | FunctionCall | '(' + Expression + Optional( Keyword('AS') + Var ) + ')' | Var

# [19] GroupClause ::= 'GROUP' 'BY' GroupCondition+
GroupClause = Keyword('GROUP') + Keyword('BY') + OneOrMore(GroupCondition)



_Silent = Optional(Keyword('SILENT'))

# [31] Load ::= 'LOAD' 'SILENT'? iri ( 'INTO' GraphRef )?
Load = Keyword('LOAD') + _Silent + iri + Optional( Keyword('INTO') + GraphRef )

# [32] Clear ::= 'CLEAR' 'SILENT'? GraphRefAll
Clear = Keyword('CLEAR') + _Silent + GraphRefAll

# [33] Drop ::= 'DROP' _Silent GraphRefAll
Drop = Keyword('DROP') + _Silent + GraphRefAll

# [34] Create ::= 'CREATE' _Silent GraphRef
Create = Keyword('CREATE') + _Silent + GraphRef

# [35] Add ::= 'ADD' _Silent GraphOrDefault 'TO' GraphOrDefault
Add = Keyword('ADD') + _Silent + GraphOrDefault + Keyword('TO') + GraphOrDefault

# [36] Move ::= 'MOVE' _Silent GraphOrDefault 'TO' GraphOrDefault
Move = Keyword('MOVE') + _Silent + GraphOrDefault + Keyword('TO') + GraphOrDefault

# [37] Copy ::= 'COPY' _Silent GraphOrDefault 'TO' GraphOrDefault
Copy = Keyword('COPY') + _Silent + GraphOrDefault + Keyword('TO') + GraphOrDefault

# [38] InsertData ::= 'INSERT DATA' QuadData
InsertData = Keyword('INSERT DATA') + QuadData

# [39] DeleteData ::= 'DELETE DATA' QuadData
DeleteData = Keyword('DELETE DATA') + QuadData

# [40] DeleteWhere ::= 'DELETE WHERE' QuadPattern
DeleteWhere = Keyword('DELETE WHERE') + QuadPattern

# [42] DeleteClause ::= 'DELETE' QuadPattern
DeleteClause = Keyword('DELETE') + QuadPattern

# [43] InsertClause ::= 'INSERT' QuadPattern
InsertClause = Keyword('INSERT') + QuadPattern

# [44] UsingClause ::= 'USING' ( iri | 'NAMED' iri )
UsingClause = Keyword('USING') + ( iri | Keyword('NAMED') + iri )

# [41] Modify ::= ( 'WITH' iri )? ( DeleteClause Optional(InsertClause) | InsertClause ) ZeroOrMore(UsingClause) 'WHERE' GroupGraphPattern
Modify = Optional( Keyword('WITH') + iri ) + ( DeleteClause + Optional(InsertClause) | InsertClause ) + ZeroOrMore(UsingClause) + Keyword('WHERE') + GroupGraphPattern


# [30] Update1 ::= Load | Clear | Drop | Add | Move | Copy | Create | InsertData | DeleteData | DeleteWhere | Modify
Update1 = Load | Clear | Drop | Add | Move | Copy | Create | InsertData | DeleteData | DeleteWhere | Modify





# [63] InlineDataOneVar ::= Var '{' ZeroOrMore(DataBlockValue) '}'
InlineDataOneVar = Var + '{' + ZeroOrMore(DataBlockValue) + '}'

# [64] InlineDataFull ::= ( NIL | '(' ZeroOrMore(Var) ')' ) '{' ( '(' ZeroOrMore(DataBlockValue) ')' | NIL )* '}'
InlineDataFull = ( NIL | '(' + ZeroOrMore(Var) + ')' ) + '{' + ZeroOrMore( '(' + ZeroOrMore(DataBlockValue) + ')' | NIL ) + '}'

# [62] DataBlock ::= InlineDataOneVar | InlineDataFull
DataBlock = InlineDataOneVar | InlineDataFull


# [28] ValuesClause ::= ( 'VALUES' DataBlock )?
ValuesClause = Optional( Keyword('VALUES') + DataBlock )






# [74] ConstructTriples ::= TriplesSameSubject ( '.' Optional(ConstructTriples) )?
ConstructTriples = Forward()
ConstructTriples << ( TriplesSameSubject + Optional( '.' + Optional(ConstructTriples) ) )

# [73] ConstructTemplate ::= '{' Optional(ConstructTriples) '}'
ConstructTemplate = '{' + Optional(ConstructTriples) + '}'




# [120] BrackettedExpression ::= '(' Expression ')'
BrackettedExpression = Suppress('(') + Group ( Expression ) + Suppress(')')

# [119] PrimaryExpression ::= BrackettedExpression | BuiltInCall | iriOrFunction | RDFLiteral | NumericLiteral | BooleanLiteral | Var
PrimaryExpression = BrackettedExpression | BuiltInCall | iriOrFunction | RDFLiteral | NumericLiteral | BooleanLiteral | Var

# [118] UnaryExpression ::= '!' PrimaryExpression
# | '+' PrimaryExpression
# | '-' PrimaryExpression
# | PrimaryExpression
UnaryExpression = '!' + PrimaryExpression | '+' + PrimaryExpression | '-' + PrimaryExpression | PrimaryExpression

# [117] MultiplicativeExpression ::= UnaryExpression ( '*' UnaryExpression | '/' UnaryExpression )*
MultiplicativeExpression = UnaryExpression + ZeroOrMore( '*' + UnaryExpression | '/' + UnaryExpression )

# [116] AdditiveExpression ::= MultiplicativeExpression ( '+' MultiplicativeExpression | '-' MultiplicativeExpression | ( NumericLiteralPositive | NumericLiteralNegative ) ( ( '*' UnaryExpression ) | ( '/' UnaryExpression ) )* )*
AdditiveExpression = MultiplicativeExpression + ZeroOrMore( '+' + MultiplicativeExpression | '-' + MultiplicativeExpression | ( NumericLiteralPositive | NumericLiteralNegative ) + ZeroOrMore( ( '*' + UnaryExpression ) | ( '/' + UnaryExpression ) ) )

# [115] NumericExpression ::= AdditiveExpression
NumericExpression = AdditiveExpression

# [114] RelationalExpression ::= NumericExpression ( '=' NumericExpression | '!=' NumericExpression | '<' NumericExpression | '>' NumericExpression | '<=' NumericExpression | '>=' NumericExpression | 'IN' ExpressionList | 'NOT' 'IN' ExpressionList )?
RelationalExpression = NumericExpression + Optional( '=' + NumericExpression | '!=' + NumericExpression | '<' + NumericExpression | '>' + NumericExpression | '<=' + NumericExpression | '>=' + NumericExpression | Keyword('IN') + ExpressionList | Keyword('NOT') + Keyword('IN') + ExpressionList )

# [113] ValueLogical ::= RelationalExpression
ValueLogical = RelationalExpression

# [112] ConditionalAndExpression ::= ValueLogical ( '&&' ValueLogical )*
ConditionalAndExpression = ValueLogical + ZeroOrMore( '&&' + ValueLogical )

# [111] ConditionalOrExpression ::= ConditionalAndExpression ( '||' ConditionalAndExpression )*
ConditionalOrExpression = ConditionalAndExpression + ZeroOrMore( '||' + ConditionalAndExpression )

# [110] Expression ::= ConditionalOrExpression
Expression << ConditionalOrExpression


# [69] Constraint ::= BrackettedExpression | BuiltInCall | FunctionCall
Constraint = BrackettedExpression | BuiltInCall | FunctionCall

# [68] Filter ::= 'FILTER' Constraint
Filter = Group( Suppress(Keyword('FILTER')) + Constraint )
Filter.setParseAction(lambda x: components.Filter(*x))




# [57] OptionalGraphPattern ::= 'OPTIONAL' GroupGraphPattern
OptionalGraphPattern = Keyword('OPTIONAL') + GroupGraphPattern

# [58] GraphGraphPattern ::= 'GRAPH' VarOrIri GroupGraphPattern
GraphGraphPattern = Keyword('GRAPH') + VarOrIri + GroupGraphPattern

# [59] ServiceGraphPattern ::= 'SERVICE' _Silent VarOrIri GroupGraphPattern
ServiceGraphPattern = Keyword('SERVICE') + _Silent + VarOrIri + GroupGraphPattern

# [60] Bind ::= 'BIND' '(' Expression 'AS' Var ')'
Bind = Group ( Keyword('BIND') + '(' + Expression + Keyword('AS') + Var + ')' )

# [61] InlineData ::= 'VALUES' DataBlock
InlineData = Keyword('VALUES') + DataBlock

# [56] GraphPatternNotTriples ::= GroupOrUnionGraphPattern | OptionalGraphPattern | MinusGraphPattern | GraphGraphPattern | ServiceGraphPattern | Filter | Bind | InlineData
GraphPatternNotTriples = GroupOrUnionGraphPattern | OptionalGraphPattern | MinusGraphPattern | GraphGraphPattern | ServiceGraphPattern | Filter | Bind | InlineData

# [54] GroupGraphPatternSub ::= Optional(TriplesBlock) ( GraphPatternNotTriples '.'? Optional(TriplesBlock) )*
GroupGraphPatternSub = Optional(TriplesBlock) + ZeroOrMore( GraphPatternNotTriples + Optional('.') + Optional(TriplesBlock) )
















# ----------------

# [22] HavingCondition ::= Constraint
HavingCondition = Constraint

# [21] HavingClause ::= 'HAVING' HavingCondition+
HavingClause = Suppress(Keyword('HAVING')) + Group ( OneOrMore(HavingCondition) )
HavingClause.setParseAction(lambda x: components.Filter(*x))

# [24] OrderCondition ::= ( ( 'ASC' | 'DESC' ) BrackettedExpression )
# | ( Constraint | Var )
OrderCondition = ( ( Keyword('ASC') | Keyword('DESC') | Empty().setParseAction(lambda : 'ASC') ) + Group(BrackettedExpression) ) | Empty().setParseAction(lambda : 'ASC') + Group ( Constraint | Var )

# [23] OrderClause ::= 'ORDER' 'BY' OneOrMore(OrderCondition)
OrderClause =  Suppress(Keyword('ORDER') + Keyword('BY')) + Group ( OneOrMore(OrderCondition) )
OrderCondition.setParseAction(lambda x: components.OrderBy(*x))

# [26] LimitClause ::= 'LIMIT' INTEGER
LimitClause = Suppress(Keyword('LIMIT')) + INTEGER
LimitClause.setParseAction(lambda x: components.Slice(limit=x[0]))

# [27] OffsetClause ::= 'OFFSET' INTEGER
OffsetClause = Suppress(Keyword('OFFSET')) + INTEGER
OffsetClause.setParseAction(lambda x: components.Slice(offset=x[0]))

# [25] LimitOffsetClauses ::= LimitClause Optional(OffsetClause) | OffsetClause Optional(LimitClause)
LimitOffsetClauses = Group ( LimitClause + Optional(OffsetClause) | OffsetClause + Optional(LimitClause) ) 

# [18] SolutionModifier ::= GroupClause? HavingClause? OrderClause? LimitOffsetClauses?
SolutionModifier = Group ( Optional(GroupClause) + Optional(HavingClause) + Optional(OrderClause) + Optional(LimitOffsetClauses) ) 


# [9] SelectClause ::= 'SELECT' ( 'DISTINCT' | 'REDUCED' )? ( ( Var | ( '(' Expression 'AS' Var ')' ) )+ | '*' )
SelectClause = Suppress(Keyword('SELECT')) + ( Keyword('DISTINCT') | Keyword('REDUCED') | Empty().setParseAction(lambda : 'NONE') ) + Group ( ( OneOrMore( Var | ( Literal('(') + Expression + Keyword('AS') + Var + ')' ) ) | '*' ) )

# [17] WhereClause ::= 'WHERE'? GroupGraphPattern
WhereClause = Group ( Suppress(Optional(Keyword('WHERE'))) + GroupGraphPattern ) 

# [8] SubSelect ::= SelectClause WhereClause SolutionModifier ValuesClause
SubSelect = Group ( SelectClause + WhereClause + SolutionModifier + ValuesClause )

# [53] GroupGraphPattern ::= '{' ( SubSelect | GroupGraphPatternSub ) '}'
GroupGraphPattern << Group( Suppress('{') + ( SubSelect | GroupGraphPatternSub ) + Suppress('}') ) 

# [7] SelectQuery ::= SelectClause DatasetClause* WhereClause SolutionModifier
SelectQuery = SelectClause + Group( ZeroOrMore(DatasetClause) ) + WhereClause + SolutionModifier
SelectQuery.setParseAction(lambda x: components.SelectQuery(*x))

# [10] ConstructQuery ::= 'CONSTRUCT' ( ConstructTemplate DatasetClause* WhereClause SolutionModifier | DatasetClause* 'WHERE' '{' TriplesTemplate? '}' SolutionModifier )
ConstructQuery = Keyword('CONSTRUCT') + ( ConstructTemplate + ZeroOrMore(DatasetClause) + WhereClause + SolutionModifier | ZeroOrMore(DatasetClause) + Keyword('WHERE') + '{' + Optional(TriplesTemplate) + '}' + SolutionModifier )

# [12] AskQuery ::= 'ASK' DatasetClause* WhereClause SolutionModifier
AskQuery = Keyword('ASK') + ZeroOrMore(DatasetClause) + WhereClause + SolutionModifier

# [11] DescribeQuery ::= 'DESCRIBE' ( VarOrIri+ | '*' ) DatasetClause* WhereClause? SolutionModifier
DescribeQuery = Keyword('DESCRIBE') + ( OneOrMore(VarOrIri) | '*' ) + ZeroOrMore(DatasetClause) + Optional(WhereClause) + SolutionModifier

# [29] Update ::= Prologue ( Update1 ( ';' Update )? )?
Update = Forward()
Update << ( Prologue + Optional( Update1 + Optional( ';' + Update ) ) ) 


# [2] Query ::= Prologue
# ( SelectQuery | ConstructQuery | DescribeQuery | AskQuery )
# ValuesClause
Query = Prologue + ( SelectQuery | ConstructQuery | DescribeQuery | AskQuery ) + ValuesClause

# [3] UpdateUnit ::= Update
UpdateUnit = Update

# [1] QueryUnit ::= Query
QueryUnit = Query

QueryUnit.ignore ( '#' + restOfLine )
UpdateUnit.ignore ( '#' + restOfLine )




expandUnicodeEscapes_re=re.compile(r'\\u([0-9a-f]{4}(?:[0-9a-f]{4})?)', flags=re.I)

def expandUnicodeEscapes(q):
    """    
    The syntax of the SPARQL Query Language is expressed over code points in Unicode [UNICODE]. The encoding is always UTF-8 [RFC3629].
    Unicode code points may also be expressed using an \uXXXX (U+0 to U+FFFF) or \UXXXXXXXX syntax (for U+10000 onwards) where X is a hexadecimal digit [0-9A-F]
    """

    def expand(m):
        try:
            return unichr(int(m.group(1), 16))
        except:
            raise Exception("Invalid unicode code point: "+m)
        
    return expandUnicodeEscapes_re.sub(expand,q)

def parseQuery(q): 
    if hasattr(q,'read'): q=q.read()
    q=expandUnicodeEscapes(q)
    return Query.parseString(q)

if __name__=='__main__':
    import sys

    print Var.parseString("?x")

    try: 
        print Query.parseString(sys.argv[1])
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err
