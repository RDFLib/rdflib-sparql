

import rdflib_sparql.parser as p 
from rdflib_sparql.processor import QueryContext

ctx=QueryContext()

def testRegex():
    
    assert p.RegexExpression.parseString('REGEX("zxcabczxc","abc")')[0].eval(ctx)

    assert not p.RegexExpression.parseString('REGEX("zxczxc","abc")')[0].eval(ctx)
    
    assert p.RegexExpression.parseString('REGEX("bbbaaaaabbb","ba*b")')[0].eval(ctx)
    


if __name__=='__main__':
    import nose, sys
    nose.main(defaultTest=sys.argv[0])
