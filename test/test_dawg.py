import collections
import os.path
import datetime
import isodate

from rdflib import ConjunctiveGraph, Graph, Namespace, RDF, RDFS, URIRef, BNode, Literal
from rdflib.query import Result
from rdflib.compare import isomorphic

from rdflib_sparql.algebra import pprintAlgebra, translateQuery
from rdflib_sparql.parser import parseQuery
from rdflib_sparql.processor import SPARQLProcessor
from rdflib_sparql.results.rdfresults import RDFResultParser

from nose.tools import eq_ as eq

from urlparse import urljoin

import nose

DEBUG_FAIL=True
DEBUG_FAIL=False

DEBUG_ERROR=True
DEBUG_ERROR=False

SPARQL10Tests=True
SPARQL10Tests=False

SPARQL11Tests=True
#SPARQL11Tests=False

DETAILEDASSERT=True
#DETAILEDASSERT=False

MF=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#')
QT=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-query#')
DAWG=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-dawg#')
DOAP = Namespace('http://usefulinc.com/ns/doap#')
FOAF = Namespace('http://xmlns.com/foaf/0.1/')
EARL=Namespace("http://www.w3.org/ns/earl#")

NAME=None

fails=collections.Counter()
errors=collections.Counter()

failed_tests=[]
error_tests=[]


EARL_REPORT=Graph()

rdflib_sparql=URIRef('https://github.com/gromgull/rdflib-sparql')

EARL_REPORT.add((rdflib_sparql, DOAP.homepage, rdflib_sparql))
EARL_REPORT.add((rdflib_sparql, DOAP.name, Literal("rdflib_sparql")))
EARL_REPORT.add((rdflib_sparql, RDF.type, DOAP.Project))

me=URIRef('http://gromgull.net/me')
EARL_REPORT.add((me, RDF.type, FOAF.Person))
EARL_REPORT.add((me, FOAF.homepage, URIRef("http://gromgull.net")))
EARL_REPORT.add((me, FOAF.name, Literal("Gunnar Aastrand Grimnes")))



def _fmt(f):
    if f.endswith(".rdf"): return "xml"
    return "turtle"

def bindingsCompatible(a,b):

    """

    Are two binding-sets compatible. 

    From the spec: http://www.w3.org/2009/sparql/docs/tests/#queryevaltests

    A SPARQL implementation passes a query evaluation test if the
    graph produced by evaluating the query against the RDF dataset
    (and encoding in the DAWG result set vocabulary, if necessary) is
    equivalent [RDF-CONCEPTS] to the graph named in the result (after
    encoding in the DAWG result set vocabulary, if necessary). Note
    that, solution order only is considered relevant, if the result is
    expressed in the test suite in the DAWG result set vocabulary,
    with explicit rs:index triples; otherwise solution order is
    considered irrelevant for passing. Equivalence can be tested by
    checking that the graphs are isomorphic and have identical IRI and
    literal nodes. Note that testing whether two result sets are
    isomorphic is simpler than full graph isomorphism. Iterating over
    rows in one set, finding a match with the other set, removing this
    pair, then making sure all rows are accounted for, achieves the
    same effect.
    """

    def rowCompatible(x,y):
        m={}
        y=dict(y)
        for v1,b1 in x:
            if v1 not in y: return False
            if isinstance(b1, BNode):
                if b1 in m:
                    if y[v1]!=m[b1]: return False
                else:
                    m[b1]=y[v1]
            else: 
                if y[v1]!=b1: return False
        return True

    if not a: 
        if b: 
            return False 
        return True
    
    x=iter(a).next()
    
    for y in b: 
        if rowCompatible(x,y):
            if bindingsCompatible(a-set((x,)), b-set((y,))):
                return True

    return False
    
    
            


def pp_binding(solutions): 
    """
    Pretty print a single binding - for less eye-strain when debugging
    """
    return "\n["+",\n\t".join("{" + ", ".join("%s:%s"%(x[0], x[1].n3()) for x in bindings.items()) + "}" for bindings in solutions)+"]\n"

def do_test_single(t):
    uri, name,comment,data,graphdata,query,resfile,syntax=t

    def skip(reason='(none)'): 
        print "Skipping %s from now on."%uri
        f=file("skiptests.list","a")
        f.write("%s\t%s\n"%(uri, reason))
        f.close()

    try: 
        g=ConjunctiveGraph()
        if data:
            g.default_context.load(data, format=_fmt(data))

        if graphdata:
            for x in graphdata:
                g.load(x, 
#                       publicID=URIRef('http://ba.se/'+os.path.basename(x)),
                       format=_fmt(x))


        s=SPARQLProcessor(g)

        if not resfile: 
            # no result - syntax test

            if syntax: 
                translateQuery(parseQuery(file(query[7:]).read()))
            else: 
                # negative syntax test
                try: 
                    translateQuery(parseQuery(file(query[7:]).read()))

                    assert False, 'Query should not have parsed!'
                except: 
                    pass # it's fine - the query should not parse
            return

        # eval test - carry out query
        res2=s.query(file(query[7:]).read(), base=urljoin(query,'.'))

        if resfile.endswith('ttl'):
            resg=Graph()
            resg.load(resfile, format='turtle', publicID=resfile)
            res=RDFResultParser().parse(resg)
        elif resfile.endswith('rdf'):
            resg=Graph()
            resg.load(resfile, publicID=resfile)
            res=RDFResultParser().parse(resg)            
        elif resfile.endswith('srj'):
            res=Result.parse(file(resfile[7:]), format='json')
        else:
            res=Result.parse(file(resfile[7:]),format='xml') 


        if not DETAILEDASSERT:
            eq(res.type, res2.type, 'Types do not match')
            if res.type=='SELECT':
                eq(set(res.vars),set(res2.vars), 'Vars do not match')
                assert bindingsCompatible(set(frozenset(x.iteritems()) for x in res.bindings), set(frozenset(x.iteritems()) for x in res2.bindings)), 'Bindings do not match'
            elif res.type=='ASK':
                eq(res.askAnswer, res2.askAnswer, 'Ask answer does not match')
            elif res.type in ('DESCRIBE', 'CONSTRUCT'):
                assert isomorphic(res.graph, res2.graph), 'graphs are not isomorphic!'
            else: 
                raise Exception('Unknown result type: %s'%res.type)
        else:

            eq(res.type, res2.type, 'Types do not match: %r != %r'%(res.type, res2.type))
            if res.type=='SELECT':
                eq(set(res.vars),set(res2.vars), 'Vars do not match: %r != %r'%(set(res.vars),set(res2.vars)))
                assert bindingsCompatible(set(frozenset(x.iteritems()) for x in res.bindings), set(frozenset(x.iteritems()) for x in res2.bindings)), 'Bindings do not match: %r != %r'%(pp_binding(res.bindings), pp_binding(res2.bindings))
            elif res.type=='ASK':
                eq(res.askAnswer, res2.askAnswer, "Ask answer does not match: %r != %r"%(res.askAnswer, res2.askAnswer))
            elif res.type in ('DESCRIBE', 'CONSTRUCT'):
                assert isomorphic(res.graph, res2.graph), 'graphs are no isomorphic!'
            else: 
                raise Exception('Unknown result type: %s'%res.type)

                
                


    except Exception,e:

        if isinstance(e,AssertionError):
            failed_tests.append(uri)
            fails[e.message]+=1
        else:
            # if isinstance(e, IOError): 
            #     m=e.message+" "+e.strerror 
            # else:
            #     m=e.message
            error_tests.append(uri)
            errors[str(e)]+=1

        if DEBUG_ERROR and not isinstance(e,AssertionError) or DEBUG_FAIL: # and res.type=='CONSTRUCT' or res2.type=='CONSTRUCT':
            print "======================================"
            print uri
            print name
            print comment

            if not resfile: 
                if syntax: 
                    print "Positive syntax test"
                else: 
                    print "Negative syntax test"

            if data: 
                print "----------------- DATA --------------------"
                print ">>>", data
                print file(data[7:]).read()
            if graphdata: 
                print "----------------- GRAPHDATA --------------------"
                for x in graphdata: 
                    print ">>>", x
                    print file(x[7:]).read()
                
            print "----------------- Query -------------------"            
            print ">>>", query
            print file(query[7:]).read()
            if resfile:
                print "----------------- Res -------------------"            
                print ">>>", resfile
                print file(resfile[7:]).read()

            try: 
                pq=parseQuery(file(query[7:]).read())
                print "----------------- Parsed ------------------"
                pprintAlgebra(translateQuery(pq))
            except: 
                print "(parser error)"

            #import traceback
            #traceback.print_exc()
            print e.message.decode('string-escape')
            
            import pdb
            pdb.post_mortem()
            #pdb.set_trace()
            #nose.tools.set_trace()
        raise

    

def read_manifest(f): 

    def _str(x): 
        if x is not None:
            return str(x)
        return None

    g=Graph()
    g.load(f, format='turtle')

    for m in g.subjects(RDF.type, MF.Manifest):

        for col in g.objects(m, MF.include):
            for i in g.items(col):
                for x in read_manifest(i):
                    yield x 

        for col in g.objects(m,MF.entries):
            for e in g.items(col):
                
                if not ((e,DAWG.approval,DAWG.Approved) in g or\
                            (e, DAWG.approval, DAWG.NotClassified) in g): continue
                
                t=g.value(e, RDF.type)
                if t in (MF.PositiveUpdateSyntaxTest11, MF.NegativeUpdateSyntaxTest11, MF.UpdateEvaluationTest, MF.ProtocolTest): continue # skip update tests

                name=g.value(e, MF.name)
                comment=g.value(e,RDFS.comment)
                
                if t == MF.QueryEvaluationTest:
                    a=g.value(e, MF.action)
                    query=g.value(a, QT.query)              
                    data=g.value(a, QT.data)
                    graphdata=list(g.objects(a, QT.graphData))
                    res=g.value(e, MF.result)
                    syntax=True
                elif t in (MF.NegativeSyntaxTest11, MF.PositiveSyntaxTest11):
                    query=g.value(e, MF.action)
                    if t==MF.NegativeSyntaxTest11:
                        syntax=False
                    else: 
                        syntax=True
                    data=None
                    graphdata=None
                    res=None
                else: 
                    print "I dont know DAWG Test Type %s"%t
                    continue
                
                yield e, _str(name),_str(comment),_str(data), graphdata, _str(query),_str(res), syntax
                
                        

def test_dawg():

    for t in read_manifest("test/DAWG/data-r2/manifest-evaluation.ttl"):
        yield do_test_single, t

    if SPARQL11Tests:
        for t in read_manifest("test/DAWG/data-sparql11/manifest-all.ttl"):
            yield do_test_single, t

def earl(test, res, info=None): 
    a=BNode()
    EARL_REPORT.add((a, RDF.type, EARL.Assertion))
    EARL_REPORT.add((a, EARL.assertedBy, me))
    EARL_REPORT.add((a, EARL.test, test))
    EARL_REPORT.add((a, EARL.subject, rdflib_sparql))

    r=BNode()
    EARL_REPORT.add((a, EARL.result, r))
    EARL_REPORT.add((r, RDF.type, EARL.TestResult))

    EARL_REPORT.add((r, EARL.outcome, EARL[res]))
    if info: 
        EARL_REPORT.add((r, EARL.info, Literal(info)))


if __name__=='__main__':

    import sys, time
    start=time.time()
    if len(sys.argv)>1: 
        NAME=sys.argv[1]
        DEBUG_FAIL=True
    i=0
    success=0

    try:
        skiptests=dict([(URIRef(x.strip().split("\t")[0]), x.strip().split("\t")[1]) for x in file("skiptests.list")])
    except IOError:
        skiptests=set()

    skip=0
    for f, t in test_dawg():
        if NAME and not str(t[0]).startswith(NAME): continue
        i+=1
        if t[0] in skiptests:
            earl(t[0], "untested",skiptests[t[0]])
            print "skipping %s - %s"%(t[0],skiptests[t[0]])
            skip+=1
            continue
        try: 
            f(t)
            earl(t[0], "passed")
            success+=1
        except KeyboardInterrupt: 
            raise
        except AssertionError:
            earl(t[0], "failed")
        except: 
            earl(t[0], "failed", "error")
            import traceback
            traceback.print_exc()
            sys.stderr.write("%s\n"%t[0])


    print "\n----------------------------------------------------\n"
    print "Failed tests:"
    for f in failed_tests: 
        print f

    print "\n----------------------------------------------------\n"
    print "Error tests:"
    for f in error_tests:
        print f

    print "\n----------------------------------------------------\n"

    print "Most common fails:"
    for e in fails.most_common(10):
        e=str(e)
        print e[:450]+(e[450:] and "...")

    print "\n----------------------------------------------------\n"

    if errors: 

        print "Most common errors:"
        for e in errors.most_common(10):
            print e
    else: 
        print "(no errors!)"

    f=sum(fails.values())
    e=sum(errors.values())

    if success+f+e+skip!=i: 
        print "(Something is wrong, %d!=%d)"%(success+f+e+skip, i)
    
    print "\n%d tests, %d passed, %d failed, %d errors, %d skipped (%.2f%% success)"%(i, success, f,e, skip, 100.*success/i)
    print "Took %.2fs"%(time.time()-start)



    if not NAME: 

        now=isodate.datetime_isoformat(datetime.datetime.utcnow())

        tf=file("testruns.txt","a")
        tf.write("%s\n%d tests, %d passed, %d failed, %d errors, %d skipped (%.2f%% success)\n\n"%(now, i, success, f,e, skip, 100.*success/i))
        tf.close()
             
        earl_report='test_reports/earl_%s.ttl'%now

        EARL_REPORT.serialize(earl_report, format='n3')
        EARL_REPORT.serialize('test_reports/earl_latest.ttl', format='n3')
        print "Wrote EARL-report to '%s'"%earl_report
