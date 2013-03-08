"""
utilities for easing py3 transition for rdflib_sparql
"""

from rdflib import py3compat


def decodeStringEscape(s):
    if not py3compat.PY3:
        return s.decode('string-escape')
    else:
        # I love py3, isn't this marvellously convenient?
        return bytes(s, "utf-8").decode("unicode_escape")
