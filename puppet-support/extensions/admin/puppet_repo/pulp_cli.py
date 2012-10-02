# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from pulp.client.commands.repo import cudl, sync_publish, upload
from pulp.client.upload.manager import UploadManager

from pulp_puppet.extension.admin import (copy, modules, repo, structure, status,
                                         sync_schedules)
from pulp_puppet.extension.admin import upload as puppet_upload


def initialize(context):
    structure.ensure_repo_structure(context.cli)

    repo_section = structure.repo_section(context.cli)
    repo_section.add_command(repo.CreatePuppetRepositoryCommand(context))
    repo_section.add_command(repo.UpdatePuppetRepositoryCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(repo.ListPuppetRepositoriesCommand(context))
    repo_section.add_command(repo.SearchPuppetRepositoriesCommand(context))

    repo_section.add_command(modules.ModulesCommand(context))
    repo_section.add_command(copy.PuppetModuleCopyCommand(context))

    sync_section = structure.repo_sync_section(context.cli)
    renderer = status.PuppetStatusRenderer(context)
    sync_section.add_command(sync_publish.RunSyncRepositoryCommand(context, renderer))
    sync_section.add_command(sync_publish.SyncStatusCommand(context, renderer))

    sync_schedules_section = structure.repo_sync_schedules_section(context.cli)
    sync_schedules_section.add_command(sync_schedules.PuppetCreateScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.PuppetUpdateScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.PuppetDeleteScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.PuppetListScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.PuppetNextRunCommand(context))

    upload_manager = _upload_manager(context)
    uploads_section = structure.repo_uploads_section(context.cli)
    uploads_section.add_command(puppet_upload.UploadModuleCommand(context, upload_manager))
    uploads_section.add_command(upload.ListCommand(context, upload_manager))
    uploads_section.add_command(upload.CancelCommand(context, upload_manager))
    uploads_section.add_command(upload.ResumeCommand(context, upload_manager))


def _upload_manager(context):
    """
    Instantiates and configures the upload manager. The context is used to
    access any necessary configuration.

    :return: initialized and ready to run upload manager instance
    :rtype:  pulp.client.upload.manager.UploadManager
    """
    upload_working_dir = context.config['puppet']['upload_working_dir']
    upload_working_dir = os.path.expanduser(upload_working_dir)
    chunk_size = int(context.config['puppet']['upload_chunk_size'])
    upload_manager = UploadManager(upload_working_dir, context.server, chunk_size)
    upload_manager.initialize()
    return upload_manager
