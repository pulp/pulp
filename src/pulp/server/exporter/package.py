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
from pulp.server.exporter.logutil import getLogger

log = getLogger(__name__)

class PackageExporter(BaseExporter):
    """
     Package exporter plugin to export repository packages from pulp to target directory
    """
    def __init__(self, repoid, target_dir="./", start_date=None, end_date=None):
        """
        initialize package exporter
        @param repoid: repository Id
        @type repoid: string
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        """
        BaseExporter.__init__(self, repoid, target_dir, start_date, end_date)
        self.export_count = 0

    def export(self):
        self.validate_target_path()
        repo = self.get_repository()
        hashtype = repo['checksum_type']
        for pkg in repo['packages']:
            package_obj = self.package_api.package(pkg)
            pkg_path = pulp.server.util.get_shared_package_path(package_obj['name'], package_obj['version'], package_obj['release'],
                                                    package_obj['arch'], package_obj['filename'], package_obj['checksum'])
            if not os.path.exists(pkg_path):
                # package not found on filesystem, continue
                continue
            src_file_checksum = pulp.server.util.get_file_checksum(hashtype=hashtype, filename=pkg_path)
            dst_file_path = os.path.join(self.target_dir, os.path.basename(pkg_path))
            if not pulp.server.util.check_package_exists(dst_file_path, src_file_checksum):
                shutil.copy(pkg_path, dst_file_path)
                self.export_count += 1
                log.info("copied package %s @ location %s" % (os.path.basename(pkg_path), dst_file_path))
            else:
                log.info("file %s already exists with same checksum. skip export" % os.path.basename(pkg_path))
        # generate metadata
        try:
            pulp.server.util.create_repo(self.target_dir)
            log.info("metadata generation complete at target location %s" % self.target_dir)
        except:
            log.error("Unable to generate metadata for exported packages in target directory %s" % self.target_dir)
        
if __name__== '__main__':
    pe = PackageExporter("testdep", target_dir="/tmp/myexport")
    pe.export()
    print "Number of packages exported %s" % pe.export_count
