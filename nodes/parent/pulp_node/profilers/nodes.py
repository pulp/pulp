# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.plugins.profiler import Profiler
from pulp.server.config import config as pulp_conf

from pulp_node import constants
from pulp_node.config import read_config


# --- plugin loading ---------------------------------------------------------

def entry_point():
    """
    Entry point that pulp platform uses to load the profiler.
    :return: profiler class and its configuration.
    :rtype:  Profiler, dict
    """
    return NodeProfiler, {}


# --- plugins ----------------------------------------------------------------

class NodeProfiler(Profiler):

    @classmethod
    def metadata(cls):
        return {
            'id': constants.PROFILER_ID,
            'display_name': _('Nodes Profiler'),
            'types': [constants.NODE_SCOPE, constants.REPOSITORY_SCOPE]
        }

    def update_units(self, consumer, units, options, config, conduit):
        self._inject_parent_settings(options)
        return units

    def _inject_parent_settings(self, options):
        """
        Inject the parent settings into the options.
        Add the pulp server host and port information to the options.
        Used by the agent handler to make REST calls back to the parent.
        :param options: An options dictionary.
        :type options: dict
        """
        port = 443
        host = pulp_conf.get('server', 'server_name')
        node_conf = read_config()
        path = node_conf.main.node_certificate
        with open(path) as fp:
            node_certificate = fp.read()
        settings = {
            constants.HOST: host,
            constants.PORT: port,
            constants.NODE_CERTIFICATE: node_certificate,
        }
        options[constants.PARENT_SETTINGS] = settings
