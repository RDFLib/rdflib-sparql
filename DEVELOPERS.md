

Files
-----

* sparql.py - utility classes, exceptions, etc. 

* processor.py - glue code for RDFLib

* parser.py - the pyparsing based parser, invoked as a module it will print the parse-tree of a query from commandline

* parserutils.py - utilities for building up a parse-tree from pyparsing output

* algebra.py - converting the parsetree to a SPARQL algebra expression

* evaluate.py - evaluate a SPARQL algebra expression :) 

* evalutils.py - utility functions for evaluation, split off to avoid circular dependencies

* operators.py - implementations of SPARQL built-in functions

* aggregates.py - implementations of SPARQL aggregate functions

* rdflib_sparql/results* has parsers/serializers for xml/rdf/json/csv/tsv result formats


Update test-cases
-----------------

The DAWG test-cases are still changed. Download them again with: 

wget -m -np http://www.w3.org/2009/sparql/docs/tests/data-sparql11/

Last time I did this a handful of files had MacOS9 line-endings (wat?) : 

data-sparql11/entailment/plainLit.ttl / lang.ttl / simple.ttl 

I fixed with: 

perl -pi -e 's/\r/\n/g' <file>

Custom SPARQL Algebra Evaluation 
--------------------------------

SPARQL Algebra evaluation can be overridden by a setuptools entry_point

The entry_point group is ''rdf.plugins.sparqleval'' 

A function must be provided which takes paramters ``ctx and part``. 

The function may raise ```NotImplementedError``` if it does not wish
to handle a certain part.

See ''rdflib_sparql/evaluate.py'' for details (in particular evalPart)

Most interesting is probably overriding evalBGP.

See '''examples/customEval.py'''

