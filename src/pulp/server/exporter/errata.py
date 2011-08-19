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
import os
import shutil
import logging
from pulp.server import updateinfo
from pulp.server.compat import chain
import pulp.server.util as util
from pulp.server.exporter.base import BaseExporter

log = logging.getLogger(__name__)

class ErrataExporter(BaseExporter):
    """
     Errata exporter plugin to export repository errata from pulp to target directory
    """
    def __init__(self, repoid, target_dir="./", start_date=None, end_date=None, make_isos=False):
        """
        initialize errata exporter
        @param repoid: repository Id
        @type repoid: string
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        @param make_isos: flag to indicate iso generation
        @type make_isos: boolean
        """
        BaseExporter.__init__(self, repoid, target_dir, start_date, end_date, make_isos)
        self.export_count = 0
        self.errataids = None

    def export(self):
        self.validate_target_path()
        repo = self.get_repository()
        self.errataids = list(chain.from_iterable(repo['errata'].values()))
        log.info("generating updateinfo.xml file for exported errata")
        updateinfo_path = updateinfo.updateinfo(self.errataids, self.target_dir)
        if updateinfo_path:
            log.debug("Modifying repo for updateinfo")
            util.modify_repo(os.path.join(self.target_dir, "repodata"),
                updateinfo_path)

if __name__== '__main__':
    pe = ErrataExporter("testrepo", target_dir="/tmp/myexport")
    pe.export()