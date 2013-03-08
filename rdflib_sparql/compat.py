"""
Function/methods to help supporting 2.5-2.7
"""

try:
    from collections import Mapping, MutableMapping  # was added in 2.6

except:
    from UserDict import DictMixin as MutableMapping  # hmm
    from UserDict import DictMixin as Mapping  # this wont be readonly


try:
    from collections import OrderedDict  # was added in 2.7
except ImportError:
    from ordereddict import OrderedDict  # extra module
