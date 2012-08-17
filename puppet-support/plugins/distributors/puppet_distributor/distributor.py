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

from gettext import gettext as _

from pulp.plugins.distributor import Distributor

from pulp_puppet.common import constants
from pulp_puppet.distributor import configuration

# -- plugins ------------------------------------------------------------------

class PuppetModuleDistributor(Distributor):
    def __init__(self):
        super(PuppetModuleDistributor, self).__init__()
        self.publish_cancelled = False

    @classmethod
    def metadata(cls):
        return {
            'id' : constants.IMPORTER_ID_PUPPET,
            'display_name' : _('Puppet Distributor'),
            'types' : [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config, related_repos):
        config.default_config = configuration.DEFAULT_CONFIG
        return configuration.validate(config)
