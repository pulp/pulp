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
from pulp_puppet.distributor import configuration, publish

# -- plugins ------------------------------------------------------------------

class PuppetModuleDistributor(Distributor):
    def __init__(self):
        super(PuppetModuleDistributor, self).__init__()
        self.publish_cancelled = False

    @classmethod
    def metadata(cls):
        return {
            'id' : constants.DISTRIBUTOR_TYPE_ID,
            'display_name' : _('Puppet Distributor'),
            'types' : [constants.TYPE_PUPPET_MODULE]
        }

    def validate_config(self, repo, config, related_repos):
        config.default_config = configuration.DEFAULT_CONFIG
        return configuration.validate(config)

    def distributor_removed(self, repo, config):
        config.default_config = configuration.DEFAULT_CONFIG
        publish.unpublish_repo(repo, config)

    def publish_repo(self, repo, publish_conduit, config):
        self.publish_cancelled = False
        config.default_config = configuration.DEFAULT_CONFIG
        publish_runner = publish.PuppetModulePublishRun(repo, publish_conduit, config, self.is_publish_cancelled)
        report = publish_runner.perform_publish()
        return report

    def cancel_publish_repo(self, call_request, call_report):
        self.publish_cancelled = True

    def is_publish_cancelled(self):
        """
        Hook back into this plugin to check if a cancel request has been issued
        for a publish operation.

        :return: true if the sync should stop running; false otherwise
        :rtype: bool
        """
        return self.publish_cancelled
