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
import traceback
import sys
import pulp.server.util
from pulp.server.exporter.base import BaseExporter
import logging
log = logging.getLogger(__name__)

class DeltaRPMExporter(BaseExporter):
    """
     Deltarpm  exporter plugin to export repository presto metadata and drpms to target directory
    """
    __priority__ = 6

    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, progress=None):
        """
        initialize delta rpm exporter
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
        Export drpms associated with a repository object.
        drpms are copied to the target dir if not alreay exists
        and new metadata is generated.

        @rtype: dict
        @return: progress information for the plugin
        """
        self.progress['step'] = self.report.drpm
        drpm_src_directory = "%s/%s/%s/" % (pulp.server.util.top_repos_location(), self.repo['relative_path'], "drpms")
        dpkglist = pulp.server.util.listdir(drpm_src_directory)
        drpm_count = len(dpkglist)
        self._progress_details('drpm', drpm_count)
        repo_path = "%s/%s/" % (pulp.server.util.top_repos_location(), self.repo['relative_path'])
        src_repodata_file = os.path.join(repo_path, "repodata/repomd.xml")
        src_repodata_dir  = os.path.dirname(src_repodata_file)
        tgt_repodata_dir  = os.path.join(self.target_dir, 'repodata')
        ftypes = pulp.server.util.get_repomd_filetypes(src_repodata_file)
        if "prestodelta" not in ftypes:
            log.info("No presto metadata found in this repository [%s] to export" % self.repo['id'])
            return self.progress
        filetype_path = os.path.join(src_repodata_dir, os.path.basename(pulp.server.util.get_repomd_filetype_path(src_repodata_file, "prestodelta")))
        # modifyrepo uses filename as mdtype, rename to type.<ext>
        renamed_filetype_path = os.path.join(tgt_repodata_dir,
                                     "prestodelta" + '.' + '.'.join(os.path.basename(filetype_path).split('.')[1:]))
        try:
            shutil.copy(filetype_path,  renamed_filetype_path)
            if os.path.isfile(renamed_filetype_path):
                msg = "Modifying repo for prestodelta metadata"
                log.info(msg)
                if progress_callback is not None:
                    self.progress["step"] = msg
                    progress_callback(self.progress)
                pulp.server.util.modify_repo(tgt_repodata_dir, renamed_filetype_path)
            # now export the drpms 
            self._exporting_drpms(progress_callback)
        except pulp.server.util.CreateRepoError, cre:
            msg = "Unable to modify repo metadata with presto metadata %s; Error: %s " % (renamed_filetype_path, str(cre))
            self.progress['errors'].append(msg)
            log.error(msg)
        except Exception, e:
            msg = "Error occurred while exporting delta rpms to target directory ; Error: %s" % (renamed_filetype_path, str(e))
            self.progress['errors'].append(msg)
            log.error(msg)
        return self.progress

    def _exporting_drpms(self, progress_callback):
        
        log.info("Preparing to export delta rpm files")
        msg = "Exporting drpms"
        log.info(msg)
        if progress_callback is not None:
            self.progress["step"] = msg
            progress_callback(self.progress)
        drpm_src_directory = "%s/%s/%s/" % (pulp.server.util.top_repos_location(), self.repo['relative_path'], "drpms")
        dpkglist = pulp.server.util.listdir(drpm_src_directory)
        dpkglist = filter(lambda x: x.endswith(".drpm"), dpkglist)
        log.info("Found %s delta rpm packages in %s" % (len(dpkglist), drpm_src_directory))
        dst_drpms_dir = os.path.join(self.target_dir, "drpms")
        if not os.path.exists(dst_drpms_dir):
            os.makedirs(dst_drpms_dir)
        for count, pkg in enumerate(dpkglist):
            log.debug("Processing drpm %s" % pkg)
            if count % 500 == 0:
                log.info("Working on %s/%s" % (count, len(dpkglist)))
            try:
                src_drpm_checksum = pulp.server.util.get_file_checksum(filename=pkg)
                dst_drpm_path = os.path.join(dst_drpms_dir, os.path.basename(pkg))
                if not pulp.server.util.check_package_exists(dst_drpm_path, src_drpm_checksum):
                    shutil.copy(pkg, dst_drpm_path)
                else:
                    log.info("delta rpm %s already exists with same checksum. skip import" % os.path.basename(pkg))
                log.debug("Imported delta rpm %s " % dst_drpm_path)
                self.progress['details']["drpm"]["num_success"] += 1
                self.progress["num_success"] += 1
            except IOError, io:
                msg = "Failed to export package %s; Error: %s" % (pkg, str(io))
                self.progress['errors'].append(msg)
                self.progress['num_error'] += 1
                self.progress['details']['drpm']['num_error'] += 1
                self.progress['details']['drpm']['items_left'] -= 1
                log.error(msg)
                continue
            #self.progress['num_success'] += 1
            #self.progress['details']['drpm']['num_success'] += 1
            #self.progress['details']['drpm']['items_left'] -= 1
            msg = "Step: Exporting %s (%s/%s)" % (self.progress['step'], count, len(dpkglist))
            log.debug(msg)
            if progress_callback is not None:
                progress_callback(self.progress)

if __name__== '__main__':
    from pulp.server.api.repo import RepoApi
    from pulp.server.db import connection
    connection.initialize()
    r = RepoApi()
    ro = r.repository('f15-updates')
    pe = DeltaRPMExporter(ro, target_dir="/tmp/myexport")
    pe.export()
