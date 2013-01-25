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

from gettext import gettext as _
from pulp.plugins.importer import Importer
from pulp.citrus.importer.strategies import Mirror
from pulp.citrus.http.transport import HttpTransport
from logging import getLogger


_LOG = getLogger(__name__)


class CitrusHttpImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_http_importer',
            'display_name':'Pulp Citrus HTTP Importer',
            'types':['repository',]
        }

    def __init__(self):
        """
        :ivar cancelled: The cancelled indicator.
        :type cancelled: bool
        """
        Importer.__init__(self)
        self.cancelled = False

    def validate_config(self, repo, config, related_repos):
        msg = _('Missing required configuration property: %(p)s')
        for key in ('manifest_url',):
            value = config.get(key)
            if not value:
                return (False, msg % dict(p=key))
        return (True, None)

    def sync_repo(self, repo, conduit, config):
        try:
            transport = HttpTransport()
            strategy = Mirror(conduit, config, transport)
            report = strategy.synchronize(repo.id)
            details = dict(report=report.dict())
        except Exception, e:
            msg = str(e)
            details = dict(exception=msg)
        report = conduit.build_success_report({}, details)
        return report
