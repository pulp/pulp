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
import pulp.server.util
from pulp.server import comps_util
from pulp.server.exporter.base import BaseExporter
from logging import getLogger

log = getLogger(__name__)

class CompsExporter(BaseExporter):
    """
     Package group and category exporter plugin to export repository comps groups from pulp to target directory
    """

    __priority__ = 2

    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, progress=None):
        """
        initialize package group exporter
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
        self.progress = progress
        
    def export(self, progress_callback=None):
        """
        Export package group/category associated with a repository object.
        Packages groups/categories are looked up and comps.xml is generated
        and metadata is updated with new comps file.
        
        @rtype: dict
        @return: progress information for the plugin
        """
        self.progress['step'] = self.report.comps
        if not (len(self.repo['packagegroups']) or len(self.repo['packagegroupcategories'])):
            # no comps xml data found
            msg = "No comps groups found in repo %s" % self.repo['id']
            log.info(msg)
            return self.progress
        pg_count = len(self.repo['packagegroups']) + len(self.repo['packagegroupcategories'])
        self._progress_details('packagegroup', pg_count)
        xml = comps_util.form_comps_xml(self.repo['packagegroupcategories'],
                self.repo['packagegroups'])
        comps_file_path = "%s/%s" % (self.target_dir, "comps.xml")
        try:
            f = open(comps_file_path, 'w')
            f.write(xml.encode("utf-8"))
            f.close()
        except Exception,e:
            msg = "Error occurred while storing the comps data %s" % str(e)
            self.progress['errors'].append(msg)
            self.progress['num_error'] += self.progress['count_total']
            log.error(msg)

        try:
            msg = "Modifying repo to add Package Groups/Categories"
            log.debug(msg)
            if progress_callback is not None:
                self.progress["step"] = msg
                progress_callback(self.progress)
            pulp.server.util.modify_repo(os.path.join(self.target_dir, "repodata"),
                    comps_file_path)
            # either all pass or all error in this case
            self.progress['num_success'] += self.progress['count_total']
            self.progress['details']['packagegroup']['num_success'] = pg_count
            self.progress['details']['packagegroup']['items_left'] -= pg_count
        except pulp.server.util.CreateRepoError, cre:
            msg = "Unable to modify metadata with exported package groups/categories; Error: %s" % str(cre)
            self.progress['errors'].append(msg)
            self.progress['num_error'] += self.progress['count_total']
            self.progress['details']['packagegroup']['items_left'] = 0
            log.error(msg)
        return self.progress


if __name__== '__main__':
    pe = CompsExporter("testdep", target_dir="/tmp/myexport")
    pe.export()
