"""Cheap clone of bits of six."""

import sys
import itertools


PY2 = sys.version_info < (3,)
PY3 = not PY2


if PY2:
    range = xrange
    zip = itertools.izip


    values = dict.itervalues
    keys = dict.iterkeys
    items = dict.iteritems

    string_types = basestring
else:
    # Yes, you need these, to copy variables from __builtin__ to this
    # module's namespace
    range = range
    zip = zip

    values = dict.values
    keys = dict.keys
    items = dict.items

    string_types = str
