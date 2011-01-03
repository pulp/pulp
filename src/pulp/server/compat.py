# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
"""
This module provides workable substitutions for improvements made to python's 
standard library since version 2.4, while allowing pulp to run in a 2.4 
interpreter.
"""

# functools wraps decorator ---------------------------------------------------

try:
    import xfunctools
    wraps = functools.wraps

except ImportError:
    def _update_wrapper(orig, wrapper):
        for attr in ('__module__', '__name__', '__doc__'):
            setattr(wrapper, attr, getattr(orig, attr))
        for attr in ('__dict__',):
            getattr(wrapper, attr).update(getattr(orig, attr, {}))
        return wrapper

    def wraps(orig):
        def _wraps(decorator):
            def _decorator(*args,**kwargs):
                return decorator(*args,**kwargs)
            return _update_wrapper(decorator, _decorator)
        return _wraps

# stdlib json serialization ---------------------------------------------------

try:
    import xjson

except ImportError:
    import simplejson as json
