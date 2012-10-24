import sys
from setuptools import setup, find_packages

def setup_python3():
    # Taken from "distribute" setup.py
    from distutils.filelist import FileList
    from distutils import dir_util, file_util, util, log
    from os.path import join
  
    tmp_src = join("build", "src")
    log.set_verbosity(1)
    fl = FileList()
    for line in open("MANIFEST.in"):
        if not line.strip():
            continue
        fl.process_template_line(line)
    dir_util.create_tree(tmp_src, fl.files)
    outfiles_2to3 = []
    for f in fl.files:
        outf, copied = file_util.copy_file(f, join(tmp_src, f), update=1)
        if copied and outf.endswith(".py"):
            outfiles_2to3.append(outf)
  
    util.run_2to3(outfiles_2to3)
  
    # arrange setup to use the copy
    sys.path.insert(0, tmp_src)
  
    return tmp_src


requires = [ 'pyparsing', 'rdflib>3.2' ]

kwargs={}

if sys.version_info[:2]<(2,7): 
    requires.append("ordereddict")

if sys.version_info[0] >= 3:
    kwargs['use_2to3'] = True
    kwargs['src_root'] = setup_python3()


setup(
    name = "rdflib-sparql",
    version = "0.1-dev",
    packages = find_packages(),
    install_requires = requires,
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
        },
    **kwargs
)
