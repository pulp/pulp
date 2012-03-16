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

import gettext
import logging
import os

from pulp.server.content.plugins.distributor import Distributor
from pulp.server.content.plugins.model import PublishReport

# -- constants ----------------------------------------------------------------
_LOG = logging.getLogger(__name__)
_ = gettext.gettext

YUM_DISTRIBUTOR_TYPE_ID="yum_distributor"
RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"
REQUIRED_CONFIG_KEYS = ["relative_url", "http", "https"]
OPTIONAL_CONFIG_KEYS = ["protected", "auth_cert", "auth_ca", 
                        "https_ca", "gpgkey",
                        "generate_metadata", "checksum_type"]
###
# Config Options Explained
###
# relative_url          - Relative URL to publish
#                         example: relative_url="rhel_6.2" may translate to publishing at
#                         http://localhost/pulp/repos/rhel_6.2
# http                  - True/False:  Publish through http
# https                 - True/False:  Publish through https
# protected             - True/False: Protect this repo with repo authentication
# auth_cert             - Certificate to use if repo authentication is required
# auth_ca               - CA to use if repo authentication is required
# https_ca              - CA to verify https communication
# gpgkey                - GPG Key associated with the packages in this repo
# generate_metadata     - True will run createrepo
#                         False will not run and uses existing metadata from sync
# checksum_type         - Checksum type to use for metadata generation
#
# TODO:  Need to think some more about a 'mirror' option, how do we want to handle
# mirroring a remote url and not allowing any changes, what we were calling 'preserve_metadata' in v1.
#
# -- plugins ------------------------------------------------------------------

class YumDistributor(Distributor):

    @classmethod
    def metadata(cls):
        return {
            'id'           : YUM_DISTRIBUTOR_TYPE_ID,
            'display_name' : 'Yum Distributor',
            'types'        : [RPM_TYPE_ID, SRPM_TYPE_ID]
        }

    def validate_config(self, repo, config):
        _LOG.info("validate_config invoked, config values are: %s" % (config.repo_plugin_config))
        for key in REQUIRED_CONFIG_KEYS:
            if key not in config.repo_plugin_config:
                msg = _("Missing required configuration key: %(key)s" % {"key":key})
                _LOG.error(msg)
                return False, msg
        for key in config.repo_plugin_config:
            if key not in REQUIRED_CONFIG_KEYS and key not in OPTIONAL_CONFIG_KEYS:
                msg = _("Configuration key '%(key)s' is not supported" % {"key":key})
                _LOG.error(msg)
                return False, msg
        return True, None

    def publish_repo(self, repo, publish_conduit, config):
        summary = {}
        details = {}
        return publish_conduit.build_success_report(summary, details)
