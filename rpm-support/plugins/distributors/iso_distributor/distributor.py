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
import time

from pulp.plugins.distributor import Distributor

_LOG = logging.getLogger(__name__)
_ = gettext.gettext

ISO_DISTRIBUTOR_TYPE_ID="iso_distributor"
DISTRO_TYPE_ID="distribution"
DRPM_TYPE_ID="drpm"
ERRATA_TYPE_ID="erratum"
PKG_GROUP_TYPE_ID="package_group"
PKG_CATEGORY_TYPE_ID="package_category"
RPM_TYPE_ID="rpm"
SRPM_TYPE_ID="srpm"

REQUIRED_CONFIG_KEYS = ["relative_url", "http", "https"]
OPTIONAL_CONFIG_KEYS = ["protected", "auth_cert", "auth_ca",
                        "https_ca", "https_publish_dir", "http_publish_dir"]

HTTP_PUBLISH_DIR="/var/lib/pulp/published/http/isos"
HTTPS_PUBLISH_DIR="/var/lib/pulp/published/https/isos"
CONFIG_REPO_AUTH="/etc/pulp/repo_auth.conf"

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
# https_publish_dir     - Optional parameter to override the HTTPS_PUBLISH_DIR, mainly used for unit tests
# http_publish_dir      - Optional parameter to override the HTTP_PUBLISH_DIR, mainly used for unit tests

# -- plugins ------------------------------------------------------------------

class ISODistributor(Distributor):

    def __init__(self):
        super(ISODistributor, self).__init__()

    @classmethod
    def metadata(cls):
        return {
            'id'           : ISO_DISTRIBUTOR_TYPE_ID,
            'display_name' : 'Iso Distributor',
            'types'        : [RPM_TYPE_ID, SRPM_TYPE_ID, DRPM_TYPE_ID, ERRATA_TYPE_ID, DISTRO_TYPE_ID, PKG_CATEGORY_TYPE_ID, PKG_GROUP_TYPE_ID]
        }

    def validate_config(self, repo, config, related_repos):
        pass

    def publish_repo(self, repo, publish_conduit, config):
        pass