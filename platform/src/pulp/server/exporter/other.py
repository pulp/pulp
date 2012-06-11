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

class OtherExporter(BaseExporter):
    """
     other exporter plugin to export repository's custom metadata from pulp to target directory
    """
    __priority__ = 5

    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, progress=None):
        """
        initialize other metadata exporter
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
        Export cutom metadata associated to the repository
        and metadata is updated with new custom file.

        @rtype: dict
        @return: progress information for the plugin
        """
        self.progress['step'] = self.report.custom
        repo_path = "%s/%s/" % (pulp.server.util.top_repos_location(), self.repo['relative_path'])
        src_repodata_file = os.path.join(repo_path, "repodata/repomd.xml")
        src_repodata_dir  = os.path.dirname(src_repodata_file)
        tgt_repodata_dir  = os.path.join(self.target_dir, 'repodata')
        ftypes = pulp.server.util.get_repomd_filetypes(src_repodata_file)
        base_ftypes = ['primary', 'primary_db', 'filelists_db', 'filelists', 'other', 'other_db',
                       'updateinfo', 'group_gz', 'group', 'presto']
        process_ftypes = []
        for ftype in ftypes:
            if ftype not in base_ftypes:
                # no need to process these again
                process_ftypes.append(ftype)
        #self.progress['details']['custom']['count_total'] = len(process_ftypes)
        if not len(process_ftypes):
            log.info("No custom metadata found ")
            return self.progress
        self._progress_details('custom', len(process_ftypes))
        for ftype in process_ftypes:
            filetype_path = os.path.join(src_repodata_dir, os.path.basename(pulp.server.util.get_repomd_filetype_path(src_repodata_file, ftype)))
            # modifyrepo uses filename as mdtype, rename to type.<ext>
            renamed_filetype_path = os.path.join(tgt_repodata_dir,
                                         ftype + '.' + '.'.join(os.path.basename(filetype_path).split('.')[1:]))
            try:
                shutil.copy(filetype_path,  renamed_filetype_path)
                if os.path.isfile(renamed_filetype_path):
                    msg = "Modifying repo for %s metadata" % ftype
                    log.info(msg)
                    if progress_callback is not None:
                        self.progress["step"] = msg
                        progress_callback(self.progress)
                    pulp.server.util.modify_repo(tgt_repodata_dir, renamed_filetype_path)
                self.progress['details']['custom']['num_success'] += 1
                self.progress['details']['custom']['items_left'] -= 1
            except IOError, io:
                self.progress['details']['custom']['num_error'] += 1
                msg = "Unable to copy the custom metadata file to target directory %s; Error: %s" % (renamed_filetype_path, str(io))
                self.progress['errors'].append(msg)
                log.error(msg)
            except pulp.server.util.CreateRepoError, cre:
                self.progress['details']['custom']['num_error'] += 1
                msg = "Unable to modify repo metadata with custom file %s; Error: %s " % (renamed_filetype_path, str(cre))
                self.progress['errors'].append(msg)
                log.error(msg)
        return self.progress

if __name__== '__main__':
    pe = OtherExporter("testfedora", target_dir="/tmp/myexport")
    pe.export()      
