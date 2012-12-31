from functools import partial

import rdflib_sparql.parser as p
from rdflib_sparql.sparql import QueryContext, SPARQLError, Prologue
from rdflib_sparql.algebra import traverse, translatePName
from rdflib_sparql.operators import simplify

from rdflib import Variable, Literal

from nose.tools import eq_ as eq


def _eval(e, ctx=None):
    if not ctx:
        ctx = QueryContext()
    try:
        r = e.eval(ctx)
        if isinstance(r, SPARQLError):
            print r
            return False
        return r
    except SPARQLError:
        return False


def _translate(e):
    return simplify(traverse(
        e, visitPost=partial(translatePName, prologue=Prologue())))


def testRegex():

    assert _eval(
        _translate((p.Expression.parseString('REGEX("zxcabczxc","abc")')[0])))

    eq(_eval(_translate(
        (p.Expression.parseString('REGEX("zxczxc","abc")')[0]))), False)

    assert _eval(_translate(
        (p.Expression.parseString('REGEX("bbbaaaaabbb","ba*b")')[0])))


def test_arithmetic():

    eq(_eval(_translate((p.Expression.parseString('2+3')[0]))), 5)
    eq(_eval(_translate((p.Expression.parseString('3-2')[0]))), 1)

    eq(_eval(_translate((p.Expression.parseString('2*3')[0]))), 6)
    eq(_eval(_translate((p.Expression.parseString('4/2')[0]))), 2)

    eq(_eval(_translate((p.Expression.parseString('2+2+2')[0]))), 6)
    eq(_eval(_translate((p.Expression.parseString('2-2+2')[0]))), 2)
    eq(_eval(_translate((p.Expression.parseString('(2-2)+2')[0]))), 2)
    eq(_eval(_translate((p.Expression.parseString('2-(2+2)')[0]))), -2)

    eq(_eval(_translate((p.Expression.parseString('2*2*2')[0]))), 8)
    eq(_eval(_translate((p.Expression.parseString('4/2*2')[0]))), 4)
    eq(_eval(_translate((p.Expression.parseString('8/4*2')[0]))), 4)
    eq(_eval(_translate((p.Expression.parseString('8/(4*2)')[0]))), 1)
    eq(_eval(_translate((p.Expression.parseString('(2/2)*2')[0]))), 2)
    eq(_eval(_translate((p.Expression.parseString('4/(2*2)')[0]))), 1)

    eq(_eval(_translate((p.Expression.parseString('2+3*2')[0]))), 8)
    eq(_eval(_translate((p.Expression.parseString('(2+3)*2')[0]))), 10)
    eq(_eval(_translate((p.Expression.parseString('2+4/2')[0]))), 4)
    eq(_eval(_translate((p.Expression.parseString('(2+4)/2')[0]))), 3)


def test_arithmetic_var():
    ctx = QueryContext()
    ctx[Variable('x')] = Literal(2)

    eq(_eval(_translate((p.Expression.parseString('2+?x')[0])), ctx), 4)

    eq(_eval(_translate((p.Expression.parseString('?x+3')[0])), ctx), 5)
    eq(_eval(_translate((p.Expression.parseString('3-?x')[0])), ctx), 1)

    eq(_eval(_translate((p.Expression.parseString('?x*3')[0])), ctx), 6)
    eq(_eval(_translate((p.Expression.parseString('4/?x')[0])), ctx), 2)

    eq(_eval(_translate((p.Expression.parseString('?x+?x+?x')[0])), ctx), 6)
    eq(_eval(_translate((p.Expression.parseString('?x-?x+?x')[0])), ctx), 2)
    eq(_eval(_translate((p.Expression.parseString('(?x-?x)+?x')[0])), ctx), 2)
    eq(_eval(_translate((p.Expression.parseString('?x-(?x+?x)')[0])), ctx), -2)

    eq(_eval(_translate((p.Expression.parseString('?x*?x*?x')[0])), ctx), 8)
    eq(_eval(_translate((p.Expression.parseString('4/?x*?x')[0])), ctx), 4)
    eq(_eval(_translate((p.Expression.parseString('8/4*?x')[0])), ctx), 4)
    eq(_eval(_translate((p.Expression.parseString('8/(4*?x)')[0])), ctx), 1)
    eq(_eval(_translate((p.Expression.parseString('(?x/?x)*?x')[0])), ctx), 2)
    eq(_eval(_translate((p.Expression.parseString('4/(?x*?x)')[0])), ctx), 1)


def test_comparisons():

    eq(_eval(_translate((p.Expression.parseString('2<3')[0]))), True)
    eq(_eval(_translate((p.Expression.parseString('2<3.0')[0]))), True)
    eq(_eval(_translate((p.Expression.parseString('2<3e0')[0]))), True)

    eq(_eval(_translate((p.Expression.parseString('4<3')[0]))), False)
    eq(_eval(_translate((p.Expression.parseString('4<3.0')[0]))), False)
    eq(_eval(_translate((p.Expression.parseString('4<3e0')[0]))), False)

    eq(_eval(_translate((p.Expression.parseString('2<2.1')[0]))), True)
    eq(_eval(_translate((p.Expression.parseString('2<21e-1')[0]))), True)

    eq(_eval(_translate((p.Expression.parseString('2=2.0')[0]))), True)
    eq(_eval(_translate((p.Expression.parseString('2=2e0')[0]))), True)

    eq(_eval(_translate((p.Expression.parseString('2="cake"')[0]))), False)


def test_comparisons_var():

    ctx = QueryContext()
    ctx[Variable('x')] = Literal(2)

    eq(_eval(_translate((p.Expression.parseString('?x<3')[0])), ctx), True)
    eq(_eval(_translate((p.Expression.parseString('?x<3.0')[0])), ctx), True)
    eq(_eval(_translate((p.Expression.parseString('?x<3e0')[0])), ctx), True)

    eq(_eval(_translate((p.Expression.parseString('?x<2.1')[0])), ctx), True)
    eq(_eval(_translate((p.Expression.parseString('?x<21e-1')[0])), ctx), True)

    eq(_eval(_translate((p.Expression.parseString('?x=2.0')[0])), ctx), True)
    eq(_eval(_translate((p.Expression.parseString('?x=2e0')[0])), ctx), True)

    eq(_eval(
        _translate((p.Expression.parseString('?x="cake"')[0])), ctx), False)

    ctx = QueryContext()
    ctx[Variable('x')] = Literal(4)

    eq(_eval(_translate((p.Expression.parseString('?x<3')[0])), ctx), False)
    eq(_eval(_translate((p.Expression.parseString('?x<3.0')[0])), ctx), False)
    eq(_eval(_translate((p.Expression.parseString('?x<3e0')[0])), ctx), False)


def test_and_or():
    eq(_eval(_translate((p.Expression.parseString('3>2 && 3>1')[0]))), True)
    eq(_eval(
        _translate((p.Expression.parseString('3>2 && 3>4 || 2>1')[0]))), True)
    eq(_eval(
        _translate((p.Expression.parseString('2>1 || 3>2 && 3>4')[0]))), True)
    eq(_eval(_translate(
        (p.Expression.parseString('(2>1 || 3>2) && 3>4')[0]))), False)


if __name__ == '__main__':
    import nose
    import sys
    nose.main(defaultTest=sys.argv[0])
