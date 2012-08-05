import os, os.path
import time

from rdflib_sparql import parser
from pyparsing import ParseException 

DAWG_ROOT='test/DAWG/'

SKIP=[ 
    "qname-escape-01.rq", # this seems broken, also doesn't parse with jena \: is not a valid escape
    "syn-bad-26.rq", # this is probably impossible with pyparsing, since tokenizing is not a separate step
    # these all deal with bnode labels used across graph patterns
    # this is not really a SYNTAX error, the parser wont barf
       "syn-blabel-cross-graph-bad.rq", 
    "syn-blabel-cross-optional-bad.rq", 
    "syn-blabel-cross-union-bad.rq",
    "syn-bad-34.rq",
    "syn-bad-35.rq",
    "syn-bad-36.rq",
    "syn-bad-37.rq",
    "syn-bad-38.rq",
    "syn-bad-GRAPH-breaks-BGP.rq",
    "syn-bad-OPT-breaks-BGP.rq",
    "syn-bad-UNION-breaks-BGP.rq",    
    # not syntax error
    "syn-bad-01.rq",
    ]

def files_dir(folder):
    for f in sorted(os.listdir(folder)):
        if f.endswith('.rq') and f not in SKIP and "bad" not in f:
            yield os.path.join(folder, f)
        
 
def files(): 
    for n in range(1,6):
        for f in files_dir(DAWG_ROOT+'data-r2/syntax-sparql%d'%n):
            yield f

    for f in files_dir(DAWG_ROOT+'data-sparql11/syntax-query'):
        yield f


def parse_file(f): 
    print "Parsing",f
    if "bad" in f:
        try: 
            parser.parseQuery(file(f))
            raise Exception("File should not parse!")
        except ParseException: 
            pass # this should fail!
    else:
        try: 
            parser.parseQuery(file(f))
        except ParseException, err:
            print err.line
            print " "*(err.column-1) + "^"
            print err
            raise


def test_syntax(): 

    for f in files(): 
        yield parse_file,f

if __name__=='__main__':

    start=time.time()
    for fn,x in test_syntax():
        fn(x)

    print "Took %.2fs"%(time.time()-start)
