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
from pulp.citrus.importer import Importer as ImporterImpl
from logging import getLogger


_LOG = getLogger(__name__)


class CitrusImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_importer',
            'display_name':'Pulp Citrus Importer',
            'types':['rpm',]
        }

    def __init__(self):
        """
        @ivar cancelled: The flag indicating that the
            current operation has been cancelled.
        @type cancelled: bool
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
        report = {
            'units_added':[],
            'units_removed':[],
            'error':None,
        }

        try:
            transport = HttpTransport()
            importer = ImporterImpl(conduit, config, transport)
            added, removed = importer.synchronize(repo.id)
            report['added'] = [u.unit_key for u in added]
            report['removed'] = [u.unit_key for u in removed]
        except Exception, e:
            report['error'] = str(e)

        summary = {}
        return conduit.build_success_report(summary, report)




# --- hacking in the transport -----------------------------------------------------------

import os
import urllib

class HttpTransport:

    def download(self, requests):
        downloaded = []
        for request in requests:
          try:
              self._download(request)
              request.succeeded()
              downloaded.append(request.local_unit)
          except Exception, e:
              request.failed(e)
        return downloaded

    def _download(self, request):
        url = request.details()['url']
        fp_in = urllib.urlopen(url)
        try:
            storage_path = request.local_unit.storage_path
            self._mkdir(storage_path)
            fp_out = open(storage_path, 'w+')
            try:
                while True:
                    bfr = fp_in.read(0x100000)
                    if bfr:
                        fp_out.write(bfr)
                    else:
                        break
            finally:
                fp_out.close()
        finally:
            fp_in.close()

    def _mkdir(self, file_path):
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)