from setuptools import setup, find_packages
setup(
    name = "rdflib-sparql",
    version = "0.1",
    packages = find_packages(),
    install_requires = [ 'pyparsing', 'rdflib>3.2' ],
    tests_require = [ 'nose' ],
    entry_points = {
        'rdf.plugins.queryresult': [
            'sparql = rdflib_sparql.query:SPARQLQueryResult',
        ],
        'rdf.plugins.resultserializer': [
            'xml = rdflib_sparql.results.xmlresults:XMLResultSerializer',
            'json = rdflib_sparql.results.jsonresults:JSONResultSerializer',
        ],
        'rdf.plugins.resultparser': [
            'xml = rdflib_sparql.results.xmlresults:XMLResultParser',
            'json = rdflib_sparql.results.jsonresults:JSONResultParser',
        ],
        }

)
