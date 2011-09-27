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
from logging import getLogger

log = getLogger(__name__)

class DistributionExporter(BaseExporter):
    """
     Distributor exporter plugin to export repository distribution from pulp to target directory
    """
    __priority__ = 4
    
    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, progress=None):
        """
        initialize distribution exporter
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
        self.errataids = None
        self.progress = progress

    def export(self, progress_callback=None):
        """
         Export distribution files associated to a repository.
         Distribution image files are looked up and copied over to
         the target dir along with .treeinfo files.
         
         @rtype: dict
         @return: progress information for the plugin
        """
        self.progress['step'] = self.report.distribution
        distributions = self.repo['distributionid']
        tree_info_path = "%s/%s/" % (pulp.server.util.top_repos_location(), self.repo['relative_path'])
        src_tree_file = dst_tree_file = None
        for tree_info_name in ['treeinfo', '.treeinfo']:
            src_tree_file = tree_info_path + tree_info_name
            if os.path.exists(src_tree_file):
                dst_tree_file = "%s/%s" % (self.target_dir, tree_info_name)
                break
        if not os.path.exists(src_tree_file):
            # no distributions found
            log.info("Could not find a treeinfo file @ %s; No distributions found" % src_tree_file)
            return self.progress
        else:
            shutil.copy(src_tree_file, dst_tree_file)
            log.info("Exported treeinfo file")
        image_dir = "%s/%s/" % (self.target_dir, 'images')
        if not os.path.exists(image_dir):
            os.mkdir(image_dir)
        for distroid in distributions:
            distro = self.distribution_api.distribution(distroid)
            if not distro:
                continue
            #self.progress['details']['distribution']['count_total'] = len(distro['files'])
            self._progress_details('distribution', len(distro['files']))
            for count, src_dist_file in enumerate(distro['files']):
                if count % 500:
                    msg = "Step: Exporting %s" % self.progress['step']
                    log.debug(msg)
                dst_file_path = "%s/%s" % (image_dir, os.path.basename(src_dist_file) )
                if os.path.exists(dst_file_path):
                    dst_file_checksum = pulp.server.util.get_file_checksum(filename=dst_file_path)
                    src_file_checksum = pulp.server.util.get_file_checksum(filename=src_dist_file)
                    if src_file_checksum == dst_file_checksum:
                        log.info("file %s already exists with same checksum. skip import" % os.path.basename(src_dist_file))
                        self.progress['details']['distribution']['num_success'] += 1
                        self.progress['details']['distribution']['items_left'] -= 1
                        continue
                try:
                    file_dir = os.path.dirname(dst_file_path)
                    if not os.path.exists(file_dir):
                        os.makedirs(file_dir)
                    shutil.copy(src_dist_file, dst_file_path)
                    log.info("exported %s" % src_dist_file)
                    self.progress['details']['distribution']['num_success'] += 1
                    self.progress['details']['distribution']['items_left'] -= 1
                except IOError,io:
                    msg = "Failed to export distribution file %s; Error: %s" % (src_dist_file, str(io))
                    self.progress['errors'].append(msg)
                    self.progress['details']['distribution']['num_error'] += 1
                    self.progress['details']['distribution']['items_left'] -= 1
                    log.error(msg)
            if progress_callback is not None:
                progress_callback(self.progress)
        return self.progress

if __name__== '__main__':
    pe = DistributionExporter("testfedora", target_dir="/tmp/myexport")
    pe.export()
