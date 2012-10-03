# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Eases importing json regardless of the version of python. To use simply import:

from pulp.common.json_compat import json

Then use json as you normally would:

json.dumps(doc)
"""
import __builtin__

try:
    import json
except ImportError:
    import simplejson as json


def check_builtin(f):
    """
    This decorator tries to return a builtin function of the same name as f, and
    falls back to just returning f. This is useful for backporting builtin
    functions that don't exist on early versions of python.

    :param f:   function being decorated
    :type  f:   function
    :return:    builtin function if found, else f
    """
    return getattr(__builtin__, f.__name__, f)


@check_builtin
def any(iterable):
    """
    This should behave like the builtin function "any()", which is not present
    in python 2.4
    """
    for x in iterable:
        if x:
            return True
    return False
