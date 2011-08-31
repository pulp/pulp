# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class Distributor(object):
    """
    Base class for distributor plugin development.
    """

    @classmethod
    def metadata(cls):
        return {}

    def publish(self, publish_hook, config=None, options=None):
        """
        Publish a repository.
        @param publish_hook: api instance that provides limited pulp functionality
        @type publish_hook: L{PluginAPI} instance
        @param config: configuration for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()

    def unpublish(self, unpublish_hook, config=None, options=None):
        """
        Unpublish a repository.
        @param unpublish_hook: api instance that provides limited pulp functionality
        @type unpublish_hook: L{ContentPluginHook} instance
        @param config: configuration for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()
