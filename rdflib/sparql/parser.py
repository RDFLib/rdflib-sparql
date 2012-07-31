
import re

from pyparsing import Literal, Regex, Optional, OneOrMore, ZeroOrMore, \
    Word, nums, Forward, ParseException, Suppress, Combine
from pyparsing import CaselessKeyword as Keyword # watch out :) 
from pyparsing import Keyword as CaseSensitiveKeyword 

import rdflib

DEBUG=False

class ProjectionMismatchException(Exception):
    pass

def refer_component(component, initial_args=None, projection=None, **kwargs):
    '''
    Create a function to forward parsing results to the appropriate
    constructor.

    The pyparsing library allows us to modify the token stream that is
    returned by a particular expression with the `setParseAction()` method.
    This method sets a handler function that should take a single
    `ParseResults` instance as an argument, and then return a new token or
    list of tokens.  Mainly, we want to pass lower level tokens to SPARQL
    parse tree objects; the constructors for these objects take a number of
    positional arguments, so this function builds a new function that will
    forward the pyparsing results to the positional arguments of the
    appropriate constructor.

    This function provides a bit more functionality with its additional
    arguments:

     - `initial_args`: static list of initial arguments to add to the
     	 beginning of the arguments list before additional processing
     - `projection`: list of integers that reorders the initial arguments
     	 based on the indices that it contains.

    Finally, any additional keyword arguments passed to this function are
    passed along to the handler that is constructed.

    Note that we always convert pyparsing results to a list with the
    `asList()` method before using those results; this works, but we may
    only need this for testing.  To be safe, we include it here, but we
    might want to investigate further whether or not it could be moved only
    to testing code.  Also, we might want to investigate whether a list-only
    parsing mode could be added to pyparsing.
    '''

    if initial_args is None and projection is None:
        def __apply1(results):
            if DEBUG:
                log.debug(component)
                log.debug(results)
            return component(*results.asList(), **kwargs)
        apply = __apply1
    else:
        def __apply2(results):
            if DEBUG:
                log.debug(component)
                debug(results)
            if initial_args is not None:
                results = initial_args + results.asList()
            if projection is not None:
                if len(results) < len(projection):
                    raise ProjectionMismatchException(
                      'Expected at least %d results to make %s, got %d.' %
                      (len(projection), str(component), len(results)))
                projected = []
                for index in projection:
                    projected.append(results[index])
            else:
                projected = results
            return component(*projected, **kwargs)
        apply = __apply2
    return apply

# SPARQL Grammar: copied from http://www.w3.org/TR/sparql11-query/#grammar


# ------ TERMINALS --------------
 
# [139] IRIREF ::= '<' ([^<>"{}|^`\]-[#x00-#x20])* '>'
IRIREF = Combine(Literal('<') + Regex(r'[^<>"{}|^`\\%s]*' % ''.join('\\x%02X' % i for i in range(33))) + Literal('>'))

# [164] PN_CHARS_BASE ::= [A-Z] | [a-z] | [#x00C0-#x00D6] | [#x00D8-#x00F6] | [#x00F8-#x02FF] | [#x0370-#x037D] | [#x037F-#x1FFF] | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]
PN_CHARS_BASE = Regex(u'[A-Z]|[a-z]|[\u00C0-\u00D6]|[\u00D8-\u00F6]|[\u00F8-\u02FF]|[\u0370-\u037D]|[\u037F-\u1FFF]|[\u200C-\u200D]|[\u2070-\u218F]|[\u2C00-\u2FEF]|[\u3001-\uD7FF]|[\uF900-\uFDCF]|[\uFDF0-\uFFFD]|[\u10000-\uEFFFF]', flags=re.U)

# [165] PN_CHARS_U ::= PN_CHARS_BASE | '_'
PN_CHARS_U = PN_CHARS_BASE | '_'


# [167] PN_CHARS ::= PN_CHARS_U | '-' | [0-9] | #x00B7 | [#x0300-#x036F] | [#x203F-#x2040]
PN_CHARS = PN_CHARS_U | Regex(u"[-0-9]|\u00B7|[\u0300-\u036F]|[\u203F-\u2040]", flags=re.U)

# [168] PN_PREFIX ::= PN_CHARS_BASE ((PN_CHARS|'.')* PN_CHARS)?
PN_PREFIX = Combine(PN_CHARS_BASE + Optional( OneOrMore(PN_CHARS|'.') + PN_CHARS))

# [140] PNAME_NS ::= PN_PREFIX? ':'
PNAME_NS = Combine(Optional(PN_PREFIX) + ':')

# [173] PN_LOCAL_ESC ::= '\' ( '_' | '~' | '.' | '-' | '!' | '$' | '&' | "'" | '(' | ')' | '*' | '+' | ',' | ';' | '=' | '/' | '?' | '#' | '@' | '%' )
PN_LOCAL_ESC = Combine(Literal('\'') + ( Literal('_') | '~' | '.' | '-' | '!' | '$' | '&' | "'" | '(' | ')' | '*' | '+' | ',' | ';' | '=' | '/' | '?' | '#' | '@' | '%' ))

# [172] HEX ::= [0-9] | [A-F] | [a-f]
HEX = Regex('[0-9A-Fa-f]')

# [171] PERCENT ::= '%' HEX HEX
PERCENT = Combine('%' + HEX + HEX)

# [170] PLX ::= PERCENT | PN_LOCAL_ESC
PLX = PERCENT | PN_LOCAL_ESC

# [169] PN_LOCAL ::= (PN_CHARS_U | ':' | [0-9] | PLX ) ((PN_CHARS | '.' | ':' | PLX)* (PN_CHARS | ':' | PLX) )?
PN_LOCAL = Combine((PN_CHARS_U | ':' | Regex('[0-9]') | PLX ) + ZeroOrMore((PN_CHARS | '.' | ':' | PLX) + Optional(PN_CHARS | ':' | PLX) ))

# [141] PNAME_LN ::= PNAME_NS PN_LOCAL
PNAME_LN = Combine(PNAME_NS + PN_LOCAL)

# [142] BLANK_NODE_LABEL ::= '_:' ( PN_CHARS_U | [0-9] ) ((PN_CHARS|'.')* PN_CHARS)?
BLANK_NODE_LABEL = Combine(Literal('_:') + ( PN_CHARS_U | Regex('[0-9]') ) + Optional(ZeroOrMore(PN_CHARS|'.') + PN_CHARS))

# [166] VARNAME ::= ( PN_CHARS_U | [0-9] ) ( PN_CHARS_U | [0-9] | #x00B7 | [#x0300-#x036F] | [#x203F-#x2040] )*
VARNAME = Combine(( PN_CHARS_U | Regex('[0-9]') ) + ZeroOrMore( PN_CHARS_U | Regex(u"[0-9]|\u00B7|[\u0300-\u036F]|[\u203F-\u2040]", flags=re.U) ))

# [143] VAR1 ::= '?' VARNAME
VAR1 = Combine(Suppress('?') + VARNAME)

# [144] VAR2 ::= '$' VARNAME
VAR2 = Combine(Suppress('$') + VARNAME)

# [145] LANGTAG ::= '@' [a-zA-Z]+ ('-' [a-zA-Z0-9]+)*
LANGTAG = Combine(Regex("@[a-zA-Z]+") + ZeroOrMore(Literal("-") + Regex('[a-zA-Z0-9]+')))

# [146] INTEGER ::= [0-9]+
INTEGER = Word(nums)

# [147] DECIMAL ::= [0-9]* '.' [0-9]+
DECIMAL = Regex(r'[0-9]*\.[0-9]+')

# [155] EXPONENT ::= [eE] [+-]? [0-9]+
EXPONENT = Regex('[eE][+-]?[0-9]+')


# [148] DOUBLE ::= [0-9]+ '.' [0-9]* EXPONENT | '.' ([0-9])+ EXPONENT | ([0-9])+ EXPONENT
DOUBLE = Combine(Regex(r'[0-9]+\.[0-9]*') + EXPONENT | Regex(r'\.([0-9])+') + EXPONENT | Regex('[0-9]+') + EXPONENT)

# [149] INTEGER_POSITIVE ::= '+' INTEGER
INTEGER_POSITIVE = Combine(Literal('+') + INTEGER)

# [150] DECIMAL_POSITIVE ::= '+' DECIMAL
DECIMAL_POSITIVE = Combine(Literal('+') + DECIMAL)

# [151] DOUBLE_POSITIVE ::= '+' DOUBLE
DOUBLE_POSITIVE = Combine(Literal('+') + DOUBLE)

# [152] INTEGER_NEGATIVE ::= '-' INTEGER
INTEGER_NEGATIVE = Combine(Literal('-') + INTEGER)

# [153] DECIMAL_NEGATIVE ::= '-' DECIMAL
DECIMAL_NEGATIVE = Combine(Literal('-') + DECIMAL)

# [154] DOUBLE_NEGATIVE ::= '-' DOUBLE
DOUBLE_NEGATIVE = Combine(Literal('-') + DOUBLE)

# [160] ECHAR ::= '\' [tbnrf\"']
ECHAR = Regex(r'\\[tbnrf"\']')

# [156] STRING_LITERAL1 ::= "'" ( ([^#x27#x5C#xA#xD]) | ECHAR )* "'"
STRING_LITERAL1 = Literal("'") + ZeroOrMore( Regex(u'[^\u0027\u005C\u000A\u000D]',flags=re.U) | ECHAR ) + "'"

# [157] STRING_LITERAL2 ::= '"' ( ([^#x22#x5C#xA#xD]) | ECHAR )* '"'
STRING_LITERAL2 = Literal('"') + ZeroOrMore ( Regex(u'[^\u0022\u005C\u000A\u000D]',flags=re.U) | ECHAR ) + '"'

# [158] STRING_LITERAL_LONG1 ::= "'''" ( ( "'" | "''" )? ( [^'\] | ECHAR ) )* "'''"
STRING_LITERAL_LONG1 = Literal("'''") + ( Optional( Literal("'") | "''" ) + ZeroOrMore( ~ Literal("'\\") | ECHAR ) ) + "'''"

# [159] STRING_LITERAL_LONG2 ::= '"""' ( ( '"' | '""' )? ( [^"\] | ECHAR ) )* '"""'
STRING_LITERAL_LONG2 = Literal('"""') + ( Optional( Literal('"') | '""' ) + ZeroOrMore( ~ Literal('"\\') | ECHAR ) ) +  '"""'

# [161] NIL ::= '(' WS* ')'
NIL = Literal('(') + ')'
# [162] WS ::= #x20 | #x9 | #xD | #xA
# Not needed?
# WS = #x20 | #x9 | #xD | #xA
# [163] ANON ::= '[' WS* ']'
ANON = Literal('[') + ']'

#A = CaseSensitiveKeyword('a')
A = Literal('a')



# ------ NON-TERMINALS --------------

# [5] BaseDecl ::= 'BASE' IRIREF
BaseDecl = Literal('BASE') + IRIREF

# [6] PrefixDecl ::= 'PREFIX' PNAME_NS IRIREF
PrefixDecl = Literal('PREFIX') + PNAME_NS + IRIREF

# [4] Prologue ::= ( BaseDecl | PrefixDecl )*
Prologue = ZeroOrMore( BaseDecl | PrefixDecl )

# [108] Var ::= VAR1 | VAR2
Var = VAR1 | VAR2

# [137] PrefixedName ::= PNAME_LN | PNAME_NS
PrefixedName = PNAME_LN | PNAME_NS

# [136] iri ::= IRIREF | PrefixedName
iri = IRIREF | PrefixedName

# [135] String ::= STRING_LITERAL1 | STRING_LITERAL2 | STRING_LITERAL_LONG1 | STRING_LITERAL_LONG2
String = STRING_LITERAL1 | STRING_LITERAL2 | STRING_LITERAL_LONG1 | STRING_LITERAL_LONG2

# [129] RDFLiteral ::= String ( LANGTAG | ( '^^' iri ) )?
RDFLiteral = String + Optional( LANGTAG | ( '^^' + iri ) )

# [132] NumericLiteralPositive ::= INTEGER_POSITIVE | DECIMAL_POSITIVE | DOUBLE_POSITIVE
NumericLiteralPositive = INTEGER_POSITIVE | DECIMAL_POSITIVE | DOUBLE_POSITIVE

# [133] NumericLiteralNegative ::= INTEGER_NEGATIVE | DECIMAL_NEGATIVE | DOUBLE_NEGATIVE
NumericLiteralNegative = INTEGER_NEGATIVE | DECIMAL_NEGATIVE | DOUBLE_NEGATIVE

# [131] NumericLiteralUnsigned ::= INTEGER | DECIMAL | DOUBLE
NumericLiteralUnsigned = INTEGER | DECIMAL | DOUBLE

# [130] NumericLiteral ::= NumericLiteralUnsigned | NumericLiteralPositive | NumericLiteralNegative
NumericLiteral = NumericLiteralUnsigned | NumericLiteralPositive | NumericLiteralNegative

# [134] BooleanLiteral ::= 'true' | 'false'
BooleanLiteral = Keyword('true') | Keyword('false')

# [138] BlankNode ::= BLANK_NODE_LABEL | ANON
BlankNode = BLANK_NODE_LABEL | ANON

# [109] GraphTerm ::= iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | NIL
GraphTerm = iri | RDFLiteral | NumericLiteral | BooleanLiteral | BlankNode | NIL

# [106] VarOrTerm ::= Var | GraphTerm
VarOrTerm = Var | GraphTerm

# [107] VarOrIri ::= Var | iri
VarOrIri = Var | iri

# [46] GraphRef ::= 'GRAPH' iri
GraphRef = 'GRAPH' + iri

# [47] GraphRefAll ::= GraphRef | 'DEFAULT' | 'NAMED' | 'ALL'
GraphRefAll = GraphRef | 'DEFAULT' | 'NAMED' | 'ALL'

# [45] GraphOrDefault ::= 'DEFAULT' | 'GRAPH'? iri
GraphOrDefault = 'DEFAULT' | Optional('GRAPH') + iri

# [65] DataBlockValue ::= iri | RDFLiteral | NumericLiteral | BooleanLiteral | 'UNDEF'
DataBlockValue = iri | RDFLiteral | NumericLiteral | BooleanLiteral | 'UNDEF'

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
Path << PathAlternative

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
Collection = '(' + OneOrMore(GraphNode) + ')'

# [103] CollectionPath ::= '(' OneOrMore(GraphNodePath) ')'
CollectionPath = '(' + OneOrMore(GraphNodePath) + ')'

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
BlankNodePropertyList = '[' + PropertyListNotEmpty + ']'

# [101] BlankNodePropertyListPath ::= '[' PropertyListPathNotEmpty ']'
BlankNodePropertyListPath = '[' + PropertyListPathNotEmpty + ']'

# [98] TriplesNode ::= Collection | BlankNodePropertyList
TriplesNode << ( Collection | BlankNodePropertyList )

# [100] TriplesNodePath ::= CollectionPath | BlankNodePropertyListPath
TriplesNodePath << ( CollectionPath | BlankNodePropertyListPath )

# [75] TriplesSameSubject ::= VarOrTerm PropertyListNotEmpty | TriplesNode PropertyList
TriplesSameSubject = VarOrTerm + PropertyListNotEmpty | TriplesNode + PropertyList

# [52] TriplesTemplate ::= TriplesSameSubject ( '.' Optional(TriplesTemplate) )?
TriplesTemplate = Forward()
TriplesTemplate << ( TriplesSameSubject + Optional( '.' + Optional(TriplesTemplate) ) )

# [51] QuadsNotTriples ::= 'GRAPH' VarOrIri '{' Optional(TriplesTemplate) '}'
QuadsNotTriples = Keyword('GRAPH') + VarOrIri + '{' + Optional(TriplesTemplate) + '}'

# [50] Quads ::= Optional(TriplesTemplate) ( QuadsNotTriples '.'? Optional(TriplesTemplate) )*
Quads = Optional(TriplesTemplate) + ZeroOrMore( QuadsNotTriples + Optional('.') + Optional(TriplesTemplate) )

# [48] QuadPattern ::= '{' Quads '}'
QuadPattern = '{' + Quads + '}'

# [49] QuadData ::= '{' Quads '}'
QuadData = '{' + Quads + '}'

# [81] TriplesSameSubjectPath ::= VarOrTerm PropertyListPathNotEmpty | TriplesNodePath PropertyListPath
TriplesSameSubjectPath = VarOrTerm + PropertyListPathNotEmpty | TriplesNodePath + PropertyListPath

# [55] TriplesBlock ::= TriplesSameSubjectPath ( '.' Optional(TriplesBlock) )?
TriplesBlock = Forward()
TriplesBlock << ( TriplesSameSubjectPath + Optional( '.' + Optional(TriplesBlock) ) )


# [66] MinusGraphPattern ::= 'MINUS' GroupGraphPattern
MinusGraphPattern = 'MINUS' + GroupGraphPattern

# [67] GroupOrUnionGraphPattern ::= GroupGraphPattern ( 'UNION' GroupGraphPattern )*
GroupOrUnionGraphPattern = GroupGraphPattern + ZeroOrMore( 'UNION' + GroupGraphPattern )





# [122] RegexExpression ::= 'REGEX' '(' Expression ',' Expression ( ',' Expression )? ')'
RegexExpression = Keyword('REGEX') + '(' + Expression + ',' + Expression + Optional( ',' + Expression ) + ')'

# [123] SubstringExpression ::= 'SUBSTR' '(' Expression ',' Expression ( ',' Expression )? ')'
SubstringExpression = Keyword('SUBSTR') + '(' + Expression + ',' + Expression + Optional( ',' + Expression ) + ')'

# [124] StrReplaceExpression ::= 'REPLACE' '(' Expression ',' Expression ',' Expression ( ',' Expression )? ')'
StrReplaceExpression = Keyword('REPLACE') + '(' + Expression + ',' + Expression + ',' + Expression + Optional( ',' + Expression ) + ')'

# [125] ExistsFunc ::= 'EXISTS' GroupGraphPattern
ExistsFunc = 'EXISTS' + GroupGraphPattern

# [126] NotExistsFunc ::= 'NOT' 'EXISTS' GroupGraphPattern
NotExistsFunc = Keyword('NOT') + 'EXISTS' + GroupGraphPattern


# [127] Aggregate ::= 'COUNT' '(' 'DISTINCT'? ( '*' | Expression ) ')'
# | 'SUM' '(' Optional('DISTINCT') Expression ')'
# | 'MIN' '(' Optional('DISTINCT') Expression ')'
# | 'MAX' '(' Optional('DISTINCT') Expression ')'
# | 'AVG' '(' Optional('DISTINCT') Expression ')'
# | 'SAMPLE' '(' Optional('DISTINCT') Expression ')'
# | 'GROUP_CONCAT' '(' Optional('DISTINCT') Expression ( ';' 'SEPARATOR' '=' String )? ')'
Aggregate = Keyword('COUNT') + '(' + Optional('DISTINCT') + ( '*' | Expression ) + ')' \
    | 'SUM' + '(' + Optional('DISTINCT') + Expression + ')' \
    | 'MIN' + '(' + Optional('DISTINCT') + Expression + ')' \
    | 'MAX' + '(' + Optional('DISTINCT') + Expression + ')' \
    | 'AVG' + '(' + Optional('DISTINCT') + Expression + ')' \
    | 'SAMPLE' + '(' + Optional('DISTINCT') + Expression + ')' \
    | 'GROUP_CONCAT' + '(' + Optional('DISTINCT') + Expression + Optional( ';' + 'SEPARATOR' + '=' + String ) + ')'

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
    | 'STR' + '(' + Expression + ')' \
    | 'LANG' + '(' + Expression + ')' \
    | 'LANGMATCHES' + '(' + Expression + ',' + Expression + ')' \
    | 'DATATYPE' + '(' + Expression + ')' \
    | 'BOUND' + '(' + Var + ')' \
    | 'IRI' + '(' + Expression + ')' \
    | 'URI' + '(' + Expression + ')' \
    | 'BNODE' + ( '(' + Expression + ')' | NIL ) \
    | 'RAND' + NIL \
    | 'ABS' + '(' + Expression + ')' \
    | 'CEIL' + '(' + Expression + ')' \
    | 'FLOOR' + '(' + Expression + ')' \
    | 'ROUND' + '(' + Expression + ')' \
    | 'CONCAT' + ExpressionList \
    | SubstringExpression \
    | 'STRLEN' + '(' + Expression + ')' \
    | StrReplaceExpression \
    | 'UCASE' + '(' + Expression + ')' \
    | 'LCASE' + '(' + Expression + ')' \
    | 'ENCODE_FOR_URI' + '(' + Expression + ')' \
    | 'CONTAINS' + '(' + Expression + ',' + Expression + ')' \
    | 'STRSTARTS' + '(' + Expression + ',' + Expression + ')' \
    | 'STRENDS' + '(' + Expression + ',' + Expression + ')' \
    | 'STRBEFORE' + '(' + Expression + ',' + Expression + ')' \
    | 'STRAFTER' + '(' + Expression + ',' + Expression + ')' \
    | 'YEAR' + '(' + Expression + ')' \
    | 'MONTH' + '(' + Expression + ')' \
    | 'DAY' + '(' + Expression + ')' \
    | 'HOURS' + '(' + Expression + ')' \
    | 'MINUTES' + '(' + Expression + ')' \
    | 'SECONDS' + '(' + Expression + ')' \
    | 'TIMEZONE' + '(' + Expression + ')' \
    | 'TZ' + '(' + Expression + ')' \
    | 'NOW' + NIL \
    | 'UUID' + NIL \
    | 'STRUUID' + NIL \
    | 'MD5' + '(' + Expression + ')' \
    | 'SHA1' + '(' + Expression + ')' \
    | 'SHA256' + '(' + Expression + ')' \
    | 'SHA384' + '(' + Expression + ')' \
    | 'SHA512' + '(' + Expression + ')' \
    | 'COALESCE' + ExpressionList \
    | 'IF' + '(' + Expression + ',' + Expression + ',' + Expression + ')' \
    | 'STRLANG' + '(' + Expression + ',' + Expression + ')' \
    | 'STRDT' + '(' + Expression + ',' + Expression + ')' \
    | 'sameTerm' + '(' + Expression + ',' + Expression + ')' \
    | 'isIRI' + '(' + Expression + ')' \
    | 'isURI' + '(' + Expression + ')' \
    | 'isBLANK' + '(' + Expression + ')' \
    | 'isLITERAL' + '(' + Expression + ')' \
    | 'isNUMERIC' + '(' + Expression + ')' \
    | RegexExpression \
    | ExistsFunc \
    | NotExistsFunc


# [71] ArgList ::= NIL | '(' 'DISTINCT'? Expression ( ',' Expression )* ')'
ArgList = NIL | '(' + Optional('DISTINCT') + Expression + ZeroOrMore( ',' + Expression ) + ')'

# [128] iriOrFunction ::= iri Optional(ArgList)
iriOrFunction = iri + Optional(ArgList)

# [70] FunctionCall ::= iri ArgList
FunctionCall = iri + ArgList



# [16] SourceSelector ::= iri
SourceSelector = iri

# [14] DefaultGraphClause ::= SourceSelector
DefaultGraphClause = SourceSelector

# [15] NamedGraphClause ::= 'NAMED' SourceSelector
NamedGraphClause = 'NAMED' + SourceSelector

# [13] DatasetClause ::= 'FROM' ( DefaultGraphClause | NamedGraphClause )
DatasetClause = 'FROM' + ( DefaultGraphClause | NamedGraphClause )

# [20] GroupCondition ::= BuiltInCall | FunctionCall | '(' Expression ( 'AS' Var )? ')' | Var
GroupCondition = BuiltInCall | FunctionCall | '(' + Expression + Optional( 'AS' + Var ) + ')' | Var

# [19] GroupClause ::= 'GROUP' 'BY' GroupCondition+
GroupClause = 'GROUP' + Literal('BY') + OneOrMore(GroupCondition)





# [31] Load ::= 'LOAD' 'SILENT'? iri ( 'INTO' GraphRef )?
Load = 'LOAD' + Optional('SILENT') + iri + Optional( 'INTO' + GraphRef )

# [32] Clear ::= 'CLEAR' 'SILENT'? GraphRefAll
Clear = 'CLEAR' + Optional('SILENT') + GraphRefAll

# [33] Drop ::= 'DROP' Optional('SILENT') GraphRefAll
Drop = 'DROP' + Optional('SILENT') + GraphRefAll

# [34] Create ::= 'CREATE' Optional('SILENT') GraphRef
Create = 'CREATE' + Optional('SILENT') + GraphRef

# [35] Add ::= 'ADD' Optional('SILENT') GraphOrDefault 'TO' GraphOrDefault
Add = 'ADD' + Optional('SILENT') + GraphOrDefault + 'TO' + GraphOrDefault

# [36] Move ::= 'MOVE' Optional('SILENT') GraphOrDefault 'TO' GraphOrDefault
Move = 'MOVE' + Optional('SILENT') + GraphOrDefault + 'TO' + GraphOrDefault

# [37] Copy ::= 'COPY' Optional('SILENT') GraphOrDefault 'TO' GraphOrDefault
Copy = 'COPY' + Optional('SILENT') + GraphOrDefault + 'TO' + GraphOrDefault

# [38] InsertData ::= 'INSERT DATA' QuadData
InsertData = 'INSERT DATA' + QuadData

# [39] DeleteData ::= 'DELETE DATA' QuadData
DeleteData = 'DELETE DATA' + QuadData

# [40] DeleteWhere ::= 'DELETE WHERE' QuadPattern
DeleteWhere = 'DELETE WHERE' + QuadPattern

# [42] DeleteClause ::= 'DELETE' QuadPattern
DeleteClause = 'DELETE' + QuadPattern

# [43] InsertClause ::= 'INSERT' QuadPattern
InsertClause = 'INSERT' + QuadPattern

# [44] UsingClause ::= 'USING' ( iri | 'NAMED' iri )
UsingClause = 'USING' + ( iri | 'NAMED' + iri )

# [41] Modify ::= ( 'WITH' iri )? ( DeleteClause Optional(InsertClause) | InsertClause ) ZeroOrMore(UsingClause) 'WHERE' GroupGraphPattern
Modify = Optional( 'WITH' + iri ) + ( DeleteClause + Optional(InsertClause) | InsertClause ) + ZeroOrMore(UsingClause) + 'WHERE' + GroupGraphPattern


# [30] Update1 ::= Load | Clear | Drop | Add | Move | Copy | Create | InsertData | DeleteData | DeleteWhere | Modify
Update1 = Load | Clear | Drop | Add | Move | Copy | Create | InsertData | DeleteData | DeleteWhere | Modify





# [63] InlineDataOneVar ::= Var '{' ZeroOrMore(DataBlockValue) '}'
InlineDataOneVar = Var + '{' + ZeroOrMore(DataBlockValue) + '}'

# [64] InlineDataFull ::= ( NIL | '(' ZeroOrMore(Var) ')' ) '{' ( '(' ZeroOrMore(DataBlockValue) ')' | NIL )* '}'
InlineDataFull = ( NIL | '(' + ZeroOrMore(Var) + ')' ) + '{' + ZeroOrMore( '(' + ZeroOrMore(DataBlockValue) + ')' | NIL ) + '}'

# [62] DataBlock ::= InlineDataOneVar | InlineDataFull
DataBlock = InlineDataOneVar | InlineDataFull


# [28] ValuesClause ::= ( 'VALUES' DataBlock )?
ValuesClause = Optional( 'VALUES' + DataBlock )






# [74] ConstructTriples ::= TriplesSameSubject ( '.' Optional(ConstructTriples) )?
ConstructTriples = Forward()
ConstructTriples << ( TriplesSameSubject + Optional( '.' + Optional(ConstructTriples) ) )

# [73] ConstructTemplate ::= '{' Optional(ConstructTriples) '}'
ConstructTemplate = '{' + Optional(ConstructTriples) + '}'




# [120] BrackettedExpression ::= '(' Expression ')'
BrackettedExpression = '(' + Expression + ')'

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
RelationalExpression = NumericExpression + Optional( '=' + NumericExpression | '!=' + NumericExpression | '<' + NumericExpression | '>' + NumericExpression | '<=' + NumericExpression | '>=' + NumericExpression | 'IN' + ExpressionList | 'NOT' + 'IN' + ExpressionList )

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
Filter = 'FILTER' + Constraint





# [57] OptionalGraphPattern ::= 'OPTIONAL' GroupGraphPattern
OptionalGraphPattern = 'OPTIONAL' + GroupGraphPattern

# [58] GraphGraphPattern ::= 'GRAPH' VarOrIri GroupGraphPattern
GraphGraphPattern = 'GRAPH' + VarOrIri + GroupGraphPattern

# [59] ServiceGraphPattern ::= 'SERVICE' Optional('SILENT') VarOrIri GroupGraphPattern
ServiceGraphPattern = 'SERVICE' + Optional('SILENT') + VarOrIri + GroupGraphPattern

# [60] Bind ::= 'BIND' '(' Expression 'AS' Var ')'
Bind = 'BIND' + '(' + Expression + 'AS' + Var + ')'

# [61] InlineData ::= 'VALUES' DataBlock
InlineData = 'VALUES' + DataBlock

# [56] GraphPatternNotTriples ::= GroupOrUnionGraphPattern | OptionalGraphPattern | MinusGraphPattern | GraphGraphPattern | ServiceGraphPattern | Filter | Bind | InlineData
GraphPatternNotTriples = GroupOrUnionGraphPattern | OptionalGraphPattern | MinusGraphPattern | GraphGraphPattern | ServiceGraphPattern | Filter | Bind | InlineData

# [54] GroupGraphPatternSub ::= Optional(TriplesBlock) ( GraphPatternNotTriples '.'? Optional(TriplesBlock) )*
GroupGraphPatternSub = Optional(TriplesBlock) + ZeroOrMore( GraphPatternNotTriples + Optional('.') + Optional(TriplesBlock) )
















# ----------------

# [22] HavingCondition ::= Constraint
HavingCondition = Constraint

# [21] HavingClause ::= 'HAVING' HavingCondition+
HavingClause = 'HAVING' + OneOrMore(HavingCondition)

# [24] OrderCondition ::= ( ( 'ASC' | 'DESC' ) BrackettedExpression )
# | ( Constraint | Var )
OrderCondition = ( ( Literal('ASC') | 'DESC' ) + BrackettedExpression ) | ( Constraint | Var )

# [23] OrderClause ::= 'ORDER' 'BY' OneOrMore(OrderCondition)
OrderClause = 'ORDER' + Literal('BY') + OneOrMore(OrderCondition)

# [26] LimitClause ::= 'LIMIT' INTEGER
LimitClause = 'LIMIT' + INTEGER

# [27] OffsetClause ::= 'OFFSET' INTEGER
OffsetClause = 'OFFSET' + INTEGER

# [25] LimitOffsetClauses ::= LimitClause Optional(OffsetClause) | OffsetClause Optional(LimitClause)
LimitOffsetClauses = LimitClause + Optional(OffsetClause) | OffsetClause + Optional(LimitClause)

# [18] SolutionModifier ::= GroupClause? HavingClause? OrderClause? LimitOffsetClauses?
SolutionModifier = Optional(GroupClause) + Optional(HavingClause) + Optional(OrderClause) + Optional(LimitOffsetClauses)


# [9] SelectClause ::= 'SELECT' ( 'DISTINCT' | 'REDUCED' )? ( ( Var | ( '(' Expression 'AS' Var ')' ) )+ | '*' )
SelectClause = Literal('SELECT') + Optional( Keyword('DISTINCT') | 'REDUCED' ) + ( OneOrMore( Var | ( Literal('(') + Expression + 'AS' + Var + ')' ) ) | '*' )

# [17] WhereClause ::= 'WHERE'? GroupGraphPattern
WhereClause = Optional('WHERE') + GroupGraphPattern

# [8] SubSelect ::= SelectClause WhereClause SolutionModifier ValuesClause
SubSelect = SelectClause + WhereClause + SolutionModifier + ValuesClause

# [53] GroupGraphPattern ::= '{' ( SubSelect | GroupGraphPatternSub ) '}'
GroupGraphPattern << ( '{' + ( SubSelect | GroupGraphPatternSub ) + '}' ) 

# [7] SelectQuery ::= SelectClause DatasetClause* WhereClause SolutionModifier
SelectQuery = SelectClause + ZeroOrMore(DatasetClause) + WhereClause + SolutionModifier

# [10] ConstructQuery ::= 'CONSTRUCT' ( ConstructTemplate DatasetClause* WhereClause SolutionModifier | DatasetClause* 'WHERE' '{' TriplesTemplate? '}' SolutionModifier )
ConstructQuery = 'CONSTRUCT' + ( ConstructTemplate + ZeroOrMore(DatasetClause) + WhereClause + SolutionModifier | ZeroOrMore(DatasetClause) + 'WHERE' + '{' + Optional(TriplesTemplate) + '}' + SolutionModifier )

# [12] AskQuery ::= 'ASK' DatasetClause* WhereClause SolutionModifier
AskQuery = 'ASK' + ZeroOrMore(DatasetClause) + WhereClause + SolutionModifier

# [11] DescribeQuery ::= 'DESCRIBE' ( VarOrIri+ | '*' ) DatasetClause* WhereClause? SolutionModifier
DescribeQuery = 'DESCRIBE' + ( OneOrMore(VarOrIri) | '*' ) + ZeroOrMore(DatasetClause) + Optional(WhereClause) + SolutionModifier

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


# ---------------- ACTIONS 

A.setParseAction(lambda x: rdflib.RDF.type)
Var.setParseAction(refer_component(rdflib.term.Variable))

if __name__=='__main__':
    import sys

    print Var.parseString("?x")

    try: 
        print Query.parseString(sys.argv[1])
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err
