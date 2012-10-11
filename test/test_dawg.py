import collections
import os.path

from rdflib import ConjunctiveGraph, Graph, Namespace, RDF, RDFS, URIRef
from rdflib.query import Result

from rdflib_sparql.parser import parseQuery
from rdflib_sparql.processor import SPARQLProcessor
from rdflib_sparql.results.rdfresults import RDFResultParser

from nose.tools import eq_ as eq
import nose

DEBUG_FAIL=True
DEBUG_FAIL=False

DEBUG_ERROR=True
#DEBUG_ERROR=False


DETAILEDASSERT=True
#DETAILEDASSERT=False

MF=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#')
QT=Namespace('http://www.w3.org/2001/sw/DataAccess/tests/test-query#')

NAME=None

fails=collections.Counter()
errors=collections.Counter()

def do_test_single(t):
    name,comment,data,query,resfile=t

    if NAME and name!=NAME: return

    try: 
        g=ConjunctiveGraph()
        if data:
            g.load(data, 
                   publicID=URIRef(os.path.basename(data)), 
                   format='turtle')

        s=SPARQLProcessor(g)

        res2=s.query(file(query[7:]).read())

        if not resfile: 
            return # done - nothing to check

        if resfile.endswith('ttl'):
            resg=Graph()
            resg.load(resfile, format='turtle')
            res=RDFResultParser().parse(resg)
        elif resfile.endswith('rdf'):
            resg=Graph()
            resg.load(resfile)
            res=RDFResultParser().parse(resg)            
        else:
            res=Result.parse(file(resfile[7:]),format='xml') # relies on rdfextras


        if not DETAILEDASSERT:
            eq(res.type, res2.type, 'Types do not match')
            if res.type=='SELECT':
                eq(set(res.vars),set(res2.vars), 'Vars do not match')
                eq(set(frozenset(x.iteritems()) for x in res.bindings), set(frozenset(x.iteritems()) for x in res2.bindings), 'Bindings do not match')
            elif res.type=='ASK':
                eq(res.askAnswer, res2.askAnswer, 'Ask answer does not match')
        else:

            eq(res.type, res2.type, 'Types do not match: %r != %r'%(res.type, res2.type))
            if res.type=='SELECT':
                eq(set(res.vars),set(res2.vars), 'Vars do not match: %r != %r'%(set(res.vars),set(res2.vars)))
                eq(set(frozenset(x.iteritems()) for x in res.bindings), set(frozenset(x.iteritems()) for x in res2.bindings), 'Bindings do not match: %r != %r'%(res.bindings, res2.bindings))
            elif res.type=='ASK':
                eq(res.askAnswer, res2.askAnswer, "Ask answer does not match: %r != %r"%(res.askAnswer, res2.askAnswer))
                


    except Exception,e:

        if isinstance(e,AssertionError):
            fails[e.message]+=1
        else:
            # if isinstance(e, IOError): 
            #     m=e.message+" "+e.strerror 
            # else:
            #     m=e.message
            errors[e]+=1

        if DEBUG_ERROR and not isinstance(e,AssertionError) or DEBUG_FAIL: # and res.type=='CONSTRUCT' or res2.type=='CONSTRUCT':
            print name
            print comment
            if data: 
                print "----------------- DATA --------------------"
                print ">>>", data
                print file(data[7:]).read()
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
                print pq
            except: 
                print "(parser error)"

            import traceback
            traceback.print_exc()
            import pdb
            pdb.post_mortem()
            #pdb.set_trace()
            nose.tools.set_trace()
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
                
                a=g.value(e, MF.action)
                query=g.value(a, QT.query)
                data=g.value(a, QT.data)
                res=g.value(e, MF.result)
                name=g.value(e, MF.name)
                comment=g.value(e,RDFS.comment)
                
                yield _str(name),_str(comment),_str(data),_str(query),_str(res)
                
                        

def test_dawg():

    for t in read_manifest("test/DAWG/data-r2/manifest-evaluation.ttl"):
        yield do_test_single, t
        
    #for t in read_manifest("test/DAWG/data-sparql11/manifest-all.ttl"):
    #    yield do_test_single, t


if __name__=='__main__':

    import sys, time
    start=time.time()
    if len(sys.argv)>1: NAME=sys.argv[1]
    i=0
    success=0
    for f, t in test_dawg():
        i+=1
        try: 
            f(t)
            success+=1
        except KeyboardInterrupt: 
            raise
        except AssertionError:
            pass
        except: 
            import traceback
            traceback.print_exc()

    print "\n----------------------------------------------------\n"

    print "Most common fails:"
    for e in fails.most_common(10):
        print e

    print "\n----------------------------------------------------\n"

    if errors: 

        print "Most common errors:"
        for e in errors.most_common(10):
            print e
    else: 
        print "(no errors!)"

    f=sum(fails.values())
    e=sum(errors.values())
    print "\n%d tests, %d passed, %d failed, %d errors, (%d)"%(i, success, f,e, success+f+e)
    print "Took %.2fs"%(time.time()-start)

