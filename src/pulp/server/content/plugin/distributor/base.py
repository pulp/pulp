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

from pulp.server.content.plugin.base import ContentPlugin, allow_config_override


class Distributor(ContentPlugin):
    """
    Base class for distributor plugin development.
    """

    def __init__(self, config):
        super(Distributor, self).__init__(config)

    @allow_config_override
    def publish(self, publish_api, config=None, options=None):
        """
        Publish a repository.
        @param publish_api: api instance that provides limited pulp functionality
        @type publish_api: L{PluginAPI} instance
        @param config: configuration override for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()

    @allow_config_override
    def unpublish(self, unpublish_api, config=None, options=None):
        """
        Unpublish a repository.
        @param unpublish_api: api instance that provides limited pulp functionality
        @type unpublish_api: L{PluginAPI} instance
        @param config: configuration override for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()
