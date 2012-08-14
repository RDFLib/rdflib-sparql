

import rdflib_sparql.parser as p 
from rdflib_sparql.sparql import QueryContext, SPARQLError

from rdflib import Variable, Literal

from nose.tools import eq_ as eq

def testRegex():
    
    assert p.Expression.parseString('REGEX("zxcabczxc","abc")')[0].eval()

    assert not p.Expression.parseString('REGEX("zxczxc","abc")')[0].eval()
    
    assert p.Expression.parseString('REGEX("bbbaaaaabbb","ba*b")')[0].eval()
    

def test_arithmetic():

    eq(p.Expression.parseString('2+3')[0].eval(),5)
    eq(p.Expression.parseString('3-2')[0].eval(),1)

    eq(p.Expression.parseString('2*3')[0].eval(),6)
    eq(p.Expression.parseString('4/2')[0].eval(),2)

    eq(p.Expression.parseString('2+2+2')[0].eval(),6)
    eq(p.Expression.parseString('2-2+2')[0].eval(),2)
    eq(p.Expression.parseString('(2-2)+2')[0].eval(),2)
    eq(p.Expression.parseString('2-(2+2)')[0].eval(),-2)

    eq(p.Expression.parseString('2*2*2')[0].eval(),8)
    eq(p.Expression.parseString('4/2*2')[0].eval(),4)
    eq(p.Expression.parseString('8/4*2')[0].eval(),4)
    eq(p.Expression.parseString('8/(4*2)')[0].eval(),1)
    eq(p.Expression.parseString('(2/2)*2')[0].eval(),2)
    eq(p.Expression.parseString('4/(2*2)')[0].eval(),1)
    

    eq(p.Expression.parseString('2+3*2')[0].eval(),8)
    eq(p.Expression.parseString('(2+3)*2')[0].eval(),10)
    eq(p.Expression.parseString('2+4/2')[0].eval(),4)
    eq(p.Expression.parseString('(2+4)/2')[0].eval(),3)

def test_arithmetic_var(): 
    ctx=QueryContext()
    ctx[Variable('x')]=Literal(2)
    
    eq(p.Expression.parseString('2+?x')[0].eval(ctx),4)

    eq(p.Expression.parseString('?x+3')[0].eval(ctx),5)
    eq(p.Expression.parseString('3-?x')[0].eval(ctx),1)

    eq(p.Expression.parseString('?x*3')[0].eval(ctx),6)
    eq(p.Expression.parseString('4/?x')[0].eval(ctx),2)

    eq(p.Expression.parseString('?x+?x+?x')[0].eval(ctx),6)
    eq(p.Expression.parseString('?x-?x+?x')[0].eval(ctx),2)
    eq(p.Expression.parseString('(?x-?x)+?x')[0].eval(ctx),2)
    eq(p.Expression.parseString('?x-(?x+?x)')[0].eval(ctx),-2)

    eq(p.Expression.parseString('?x*?x*?x')[0].eval(ctx),8)
    eq(p.Expression.parseString('4/?x*?x')[0].eval(ctx),4)
    eq(p.Expression.parseString('8/4*?x')[0].eval(ctx),4)
    eq(p.Expression.parseString('8/(4*?x)')[0].eval(ctx),1)
    eq(p.Expression.parseString('(?x/?x)*?x')[0].eval(ctx),2)
    eq(p.Expression.parseString('4/(?x*?x)')[0].eval(ctx),1)


def test_comparisons(): 

    eq(p.Expression.parseString('2<3')[0].eval(),True)
    eq(p.Expression.parseString('2<3.0')[0].eval(),True)
    eq(p.Expression.parseString('2<3e0')[0].eval(),True)

    eq(p.Expression.parseString('4<3')[0].eval(),False)
    eq(p.Expression.parseString('4<3.0')[0].eval(),False)
    eq(p.Expression.parseString('4<3e0')[0].eval(),False)

    eq(p.Expression.parseString('2<2.1')[0].eval(),True)
    eq(p.Expression.parseString('2<21e-1')[0].eval(),True)

    eq(p.Expression.parseString('2=2.0')[0].eval(),True)
    eq(p.Expression.parseString('2=2e0')[0].eval(),True)

    eq(p.Expression.parseString('2="cake"')[0].eval(),False)

def test_comparisons_var(): 

    ctx=QueryContext()
    ctx[Variable('x')]=Literal(2)

    eq(p.Expression.parseString('?x<3')[0].eval(ctx),True)
    eq(p.Expression.parseString('?x<3.0')[0].eval(ctx),True)
    eq(p.Expression.parseString('?x<3e0')[0].eval(ctx),True)

    eq(p.Expression.parseString('?x<2.1')[0].eval(ctx),True)
    eq(p.Expression.parseString('?x<21e-1')[0].eval(ctx),True)

    eq(p.Expression.parseString('?x=2.0')[0].eval(ctx),True)
    eq(p.Expression.parseString('?x=2e0')[0].eval(ctx),True)

    eq(p.Expression.parseString('?x="cake"')[0].eval(ctx),False)

    ctx[Variable('x')]=Literal(4)

    eq(p.Expression.parseString('?x<3')[0].eval(ctx),False)
    eq(p.Expression.parseString('?x<3.0')[0].eval(ctx),False)
    eq(p.Expression.parseString('?x<3e0')[0].eval(ctx),False)


    
def test_and_or():
    
    eq(p.Expression.parseString('3>2 && 3>1')[0].eval(),True)
    eq(p.Expression.parseString('3>2 && 3>4 || 2>1')[0].eval(),True)
    eq(p.Expression.parseString('2>1 || 3>2 && 3>4')[0].eval(),True)
    eq(p.Expression.parseString('(2>1 || 3>2) && 3>4')[0].eval(),False)


if __name__=='__main__':
    import nose, sys
    nose.main(defaultTest=sys.argv[0])
