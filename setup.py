from setuptools import setup, find_packages
setup(
    name = "rdflib-sparql",
    version = "0.1-dev",
    packages = find_packages(),
    install_requires = [ 'pyparsing', 'rdflib>3.2' ],
    tests_require = [ 'nose' ],
    entry_points = {
        'rdf.plugins.queryresult': [
            'sparql = rdflib_sparql.processor:SPARQLResult',
        ],
        'rdf.plugins.queryprocessor': [
            'sparql = rdflib_sparql.processor:SPARQLProcessor',
        ],

        'rdf.plugins.resultserializer': [
            'xml = rdflib_sparql.results.xmlresults:XMLResultSerializer',
            'json = rdflib_sparql.results.jsonresults:JSONResultSerializer',
            'csv = rdflib_sparql.results.csvresults:CSVResultSerializer',


        ],
        'rdf.plugins.resultparser': [
            'xml = rdflib_sparql.results.xmlresults:XMLResultParser',
            'json = rdflib_sparql.results.jsonresults:JSONResultParser',
            'csv = rdflib_sparql.results.csvresults:CSVResultParser',
            'tsv = rdflib_sparql.results.tsvresults:TSVResultParser',

        ],
        }

)
