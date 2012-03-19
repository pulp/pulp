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
import pulp.server.util
from pulp.server import updateinfo
from pulp.server.compat import chain
from pulp.server.exporter.base import BaseExporter
from logging import getLogger

log = getLogger(__name__)

class ErrataExporter(BaseExporter):
    """
     Errata exporter plugin to export repository errata from pulp to target directory
    """
    __priority__ = 3

    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, progress=None):
        """
        initialize errata exporter
        @param repo: repository Object
        @type repo: Repo object
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        """
        BaseExporter.__init__(self, repo, target_dir, start_date, end_date, progress)
        self.export_count = 0
        self.progress = progress
        self.errataids = None

    def export(self, progress_callback=None):
        """
        Export errata associated with a repository object.
        Errata is looked up in pulp db and updateinfo.xml is generated,
        packages associated with each errata are also processed and
        and metadata is updated with new updateinfo xml.

        @rtype: dict
        @return: progress information for the plugin
        """
        self.progress['step'] = self.report.errata
        self.errataids = list(chain.from_iterable(self.repo['errata'].values()))
        #self.progress['details']['errata']['count_total'] = len(self.errataids)
        if not len(self.errataids):
            log.info("No errata found in repository to export")
            return self.progress
        self._progress_details('errata', len(self.errataids))
        log.info("%s errata found in repository for export" % len(self.errataids))
        self.__process_errata_packages()
        log.info("generating updateinfo.xml file for exported errata")
        try:
            updateinfo_path = updateinfo.updateinfo(self.errataids, self.target_dir)
            if updateinfo_path:
                msg = "Running modifyrepo to add updateinfo information"
                log.debug(msg)
                if progress_callback is not None:
                    self.progress["step"] = msg
                    progress_callback(self.progress)
                pulp.server.util.modify_repo(os.path.join(self.target_dir, "repodata"),
                    updateinfo_path)
            # either all pass or all error in this case
            self.progress['details']['errata']['num_success'] = len(self.errataids)
            self.progress['details']['errata']['items_left'] -= len(self.errataids)
        except pulp.server.util.CreateRepoError, cre:
            self.progress['details']['errata']['num_error'] = len(self.errataids)
            msg = "Unable to modify metadata with exported errata; Error: %s " % str(cre)
            self.progress['errors'].append(msg)
            log.error(msg)
        return self.progress

    def __process_errata_packages(self):
        """
        Lookup packages associated with errata and export to target directory
        """
        errata_pkg_count = 0
        for eid in self.errataids:
            eobj = self.errata_api.erratum(eid)
            if not eobj:
                continue
            for pkgobj in eobj['pkglist']:
                for pkg in pkgobj['packages']:
                    checksum_type, checksum = pkg['sum']
                    name, version, release, arch = pkg['name'], pkg['version'], pkg['release'], pkg['arch']
                    src_pkg_path = "%s/%s/%s/%s/%s/%s/%s" % (pulp.server.util.top_package_location(), name, version,
                                                             release, arch, checksum, pkg['filename'])
                    if not os.path.exists(src_pkg_path):
                        # pkg not found
                        log.info("errata package %s missing on pulp server" % src_pkg_path)
                        continue
                    dst_pkg_path = os.path.join(self.target_dir, os.path.basename(src_pkg_path))
                    if not pulp.server.util.check_package_exists(dst_pkg_path, checksum):
                        try:
                            shutil.copy(src_pkg_path, dst_pkg_path)
                            errata_pkg_count += 1
                        except IOError, io:
                            msg = "Unable to export errata package %s to target directory; Error: %s" % (pkg['filename'], str(io))
                            log.error(msg)
                            self.progress['errors'].append(msg)
                    else:
                        log.info("Package %s already exists with same checksum. skip export" % os.path.basename(src_pkg_path))
        if not errata_pkg_count:
            # no need to trigger metadata generation
            return
        # generate metadata
        try:
            pulp.server.util.create_repo(self.target_dir)
            log.info("metadata generation complete at target location %s" % self.target_dir)
        except pulp.server.util.CreateRepoError, cre:
            msg = "Unable to generate metadata for exported errata packages in target directory %s; Error: %s" % (self.target_dir, str(cre))
            log.error(msg)
            self.progress['errors'].append(msg)

                    
if __name__== '__main__':
    pe = ErrataExporter("testrepo", target_dir="/tmp/myexport")
    pe.export()
