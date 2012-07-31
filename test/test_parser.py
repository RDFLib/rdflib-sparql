import os, os.path

from rdflib_sparql import parser
from pyparsing import ParseException 

DAWG_ROOT='test/DAWG/data-r2/'

def files_dir(folder):
    for f in sorted(os.listdir(folder)):
        yield os.path.join(folder, f)
        
 
def files(): 
    for f in files_dir(DAWG_ROOT+'syntax-sparql1'):
        yield f

def parse_file(f): 
    try: 
        parser.QueryUnit.parseFile(f)
    except ParseException, err:
        print err.line
        print " "*(err.column-1) + "^"
        print err
        raise


def test_syntax(): 

    for f in files(): 
        yield parse_file,f

if __name__=='__main__':
    
    for fn,x in test_syntax():
        fn(x)
