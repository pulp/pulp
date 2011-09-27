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
from pulp.server.exporter.base import BaseExporter
import logging
log = logging.getLogger(__name__)

class PackageExporter(BaseExporter):
    """
     Package exporter plugin to export repository packages from pulp to target directory
    """
    __priority__ = 1

    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, progress=None):
        """
        initialize package exporter
        @param repo: repository object
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


    def export(self, progress_callback=None):
        """
        Export packages associated with a repository object.
        Packages are copied to the target dir if not alreay exists
        and new metadata is generated.
        
        @rtype: dict
        @return: progress information for the plugin
        """
        self.progress['step'] = self.report.rpm
        hashtype = self.repo['checksum_type']
        package_count = len(self.repo['packages'])
        self._progress_details('rpm', package_count)
        for count, pkg in enumerate(self.repo['packages']):
            package_obj = self.package_api.package(pkg)
            if not package_obj:
                continue
            pkg_path = pulp.server.util.get_shared_package_path(package_obj['name'], package_obj['version'], package_obj['release'],
                                                    package_obj['arch'], package_obj['filename'], package_obj['checksum'])
            if not os.path.exists(pkg_path):
                # package not found on filesystem, continue
                msg = "Package %s does not exists; skipping" % pkg
                log.error(msg)
                self.progress['errors'].append(msg)
                self.progress['details']['rpm']['items_left'] -= 1
                self.progress['details']['rpm']['num_error'] += 1
                continue
            src_file_checksum = pulp.server.util.get_file_checksum(hashtype=hashtype, filename=pkg_path)
            dst_file_path = os.path.join(self.target_dir, os.path.basename(pkg_path))
            if not pulp.server.util.check_package_exists(dst_file_path, src_file_checksum):
                try:
                    shutil.copy(pkg_path, dst_file_path)
                    self.export_count += 1
                    log.info("copied package %s @ location %s" % (os.path.basename(pkg_path), dst_file_path))
                except IOError, io:
                    msg = "Failed to export package %s; Error: %s" % (pkg, str(io))
                    self.progress['errors'].append(msg)
                    self.progress['num_error'] += 1
                    self.progress['details']['rpm']['num_error'] += 1
                    self.progress['details']['rpm']['items_left'] -= 1
                    log.error(msg)
                    continue
            else:
                self.export_count += 1
                log.info("file %s already exists with same checksum. skip export" % os.path.basename(pkg_path))
            self.progress['num_success'] = self.export_count
            self.progress['details']['rpm']['num_success'] = self.export_count
            self.progress['details']['rpm']['items_left'] -= 1
            msg = "Step: Exporting %s (%s/%s)" % (self.progress['step'], count, package_count)
            log.debug(msg)
            if progress_callback is not None:
#                self.progress["step"] = msg
                progress_callback(self.progress)

        # generate metadata
        try:
            if progress_callback is not None:
                self.progress["step"] = "Running Createrepo at target location %s" % self.target_dir
                progress_callback(self.progress)
            pulp.server.util.create_repo(self.target_dir)
            log.info("metadata generation complete at target location %s" % self.target_dir)
        except pulp.server.util.CreateRepoError, cre:
            msg = "Unable to generate metadata for exported packages in target directory %s; Error: %s" % (self.target_dir, str(cre))
            self.progress['errors'].append(msg)
            log.error(msg)
        return self.progress

if __name__== '__main__':
    pe = PackageExporter("testdep", target_dir="/tmp/myexport")
    pe.export()
    print "Number of packages exported %s" % pe.export_count
