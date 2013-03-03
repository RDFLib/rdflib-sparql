import sys
import re
from setuptools import setup, find_packages

# Find version. We have to do this because we can't import it in Python 3 until
# its been automatically converted in the setup process.


def find_version(filename):
    _version_re = re.compile(r'__version__ = "(.*)"')
    for line in open(filename):
        version_match = _version_re.match(line)
        if version_match:
            return version_match.group(1)

version = find_version('rdflib_sparql/__init__.py')


def setup_python3():
    # Taken from "distribute" setup.py
    from distutils.filelist import FileList
    from distutils import dir_util, file_util, util, log
    from os.path import join, exists

    tmp_src = join("build", "src")
    if exists(tmp_src):
        dir_util.remove_tree(tmp_src)
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


requires = ['rdflib>3.2']

kwargs = {}

if sys.version_info[:2] < (2, 6): 
    requires.append("simplejson")

if sys.version_info[:2] < (2, 7):
    requires.append("ordereddict")

if sys.version_info[0] >= 3:
    kwargs['use_2to3'] = True
    kwargs['src_root'] = setup_python3()
    requires.append("pyparsing")
else:
    requires.append("pyparsing<=1.5.7")

setup(
    name="rdflib-sparql",
    author="Gunnar Aastrand Grimnes",
    author_email="gromgull@gmail.com",
    url="http://github.com/RDFLib/rdflib-sparql",
    version=version,
    packages=find_packages(),
    install_requires=requires,
    tests_require=['nose'],
    entry_points={
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
