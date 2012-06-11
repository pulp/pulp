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
import logging
import os
import shutil
from pulp.server.api.repo import RepoApi
from pulp.server.async import find_async, run_async
from pulp.server.exporter.controller import ExportController
from pulp.server.exporter.base import exporter_progress_callback, ExportException, TargetExistsException
from pulp.server.exceptions import PulpException
from pulp.server.tasking.exception import ConflictingOperationException
from gettext import gettext as _
log = logging.getLogger(__name__)

repo_api = RepoApi()

def export(repoid, target_directory, generate_isos=False, overwrite=False):
    """
    Run a repo export asynchronously.
    @param repoid: repository id
    @type repoid: string
    @param target_directory: target directory where the content is exported
    @type target_directory: string
    @param generate_isos: flag to enable iso generation on exported content
    @type generate_isos: boolean
    @param overwrite: flag to enable content overwrite at the target directory
    @type generate_isos: boolean
    @rtype pulp.server.tasking.task or None
    @return on success a task object is returned
            on failure None is returned
    """
    repo = repo_api._get_existing_repo(repoid)
    # validate target directory
    validate_target_path(target_directory, overwrite=overwrite)
    if list_exports(repoid):
        # exporter task already pending; task not created
        return None
    task = run_async(_export,
                        [repoid, target_directory],
                        {'generate_isos': generate_isos,
                         'overwrite':overwrite},)
    if not task:
        log.error("Unable to create repo._export task for [%s]" % repoid)
        return task
    task.set_progress('progress_callback', exporter_progress_callback)
    return task
    
def _export(repoid, target_directory, generate_isos=False, overwrite=False, progress_callback=None):
    """
    Run a repo export asynchronously.
    """
    repo = repo_api._get_existing_repo(repoid)
    if repo.has_key("sync_in_progress") and repo["sync_in_progress"]:
        raise ConflictingOperationException(_('Sync for repo [%s] in progress; Cannot schedule an export ') % repo['id'])
    export_obj = ExportController(repo, target_directory, generate_isos,
                                  overwrite=overwrite, progress_callback=progress_callback)
    export_obj.perform_export()

def list_exports(id):
    """
    List all the exports for a given repository.
    """
    return [task
            for task in find_async(method='_export')
            if id in task.args]

def validate_target_path(target_dir, overwrite=False):
    """
    Validate
         * If target dir doesn't exists, create one
         * If target dir exists and not empty; if forced remove and create a fresh one, else exit
    """
    if not target_dir:
        raise ExportException("Error: target directory not specified")
    try:
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        if os.listdir(target_dir):
            if overwrite:
                shutil.rmtree(target_dir)
                os.mkdir(target_dir)
            else:
                raise TargetExistsException("Error: Target directory already has content; must use force to overwrite.")
    except ExportException, ee:
        log.error(ee)
        raise ee
    except Exception, e:
        log.error(e)
        raise e
