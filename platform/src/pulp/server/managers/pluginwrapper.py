#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
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
Contains plugin wrapper.
"""

import sys
from pulp.server.exceptions import PulpExecutionException


class PluginWrapper:
    """
    Plugin wrapper.
    Used to consistently wrap plugin method calls in a
    PulpExecutionException.
    """

    class Method:
        """
        Method wrapper.
        Used to consistently wrap plugin method calls in a
        PulpExecutionException.
        """

        def __init__(self, method):
            """
            @param method: method to be wrapped.
            @type method: instancemethod
            """
            self.__method = method

        def __call__(self, *args, **kwargs):
            try:
                return self.__method(*args, **kwargs)
            except Exception, e:
                msg = str(e)
                tb = sys.exc_info()[2]
                raise PulpExecutionException(msg), None, tb

    def __init__(self, plugin):
        """
        @param plugin: The plugin to be wrapped.
        @type plugin: Plugin
        """
        self.__plugin = plugin

    def __getattr__(self, name):
        attr = getattr(self.__plugin, name)
        if callable(attr):
            return self.Method(attr)
        else:
            return attr
