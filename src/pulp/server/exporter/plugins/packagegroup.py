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
from pulp.server.exporter.logutil import getLogger

log = getLogger(__name__)

class CompsExporter(BaseExporter):
    """
     Package group and category exporter plugin to export repository comps groups from pulp to target directory
    """

    __priority__ = 2

    def __init__(self, repoid, target_dir="./", start_date=None, end_date=None):
        """
        initialize package group exporter
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
        self.progress['step'] = 'Package Group/Category '
        
    def export(self):
        """
        Export package group/category associated with a repository object.
        Packages groups/categories are looked up and comps.xml is generated
        and metadata is updated with new comps file.
        """
        self.validate_target_path()
        repo = self.get_repository()
        xml = comps_util.form_comps_xml(repo['packagegroupcategories'],
                repo['packagegroups'])
        self.progress['count_total'] = len(repo['packagegroups']) + len(repo['packagegroupcategories'])
        if not xml:
            # no comps xml data found
            log.info("No comps data found in repo %s" % repo['id'])
            return
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
            log.debug("Modifying repo for comps groups")
            self.write("Step: Modifying repo to add Package Groups/Categories")
            pulp.server.util.modify_repo(os.path.join(self.target_dir, "repodata"),
                    comps_file_path)
            # either all pass or all error in this case
            self.progress['num_success'] = self.progress['count_total']
        except pulp.server.util.CreateRepoError:
            msg = "Unable to modify metadata with exported package groups/categories"
            self.progress['errors'].append(msg)
            self.progress['num_error'] += self.progress['count_total']
            log.error(msg)
        return self.progress


if __name__== '__main__':
    pe = CompsExporter("testdep", target_dir="/tmp/myexport")
    pe.export()
    print "Comps exporter"