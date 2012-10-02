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

from gettext import gettext as _

from pulp_rpm.common import ids

from pulp.client.commands.repo import cudl, sync_publish, upload
from pulp.client.upload import manager as upload_lib

from pulp_rpm.extension.admin import (contents, copy, export, remove, repo,
                                      status, structure, sync_schedules)
from pulp_rpm.extension.admin.upload import (category, errata, package)
from pulp_rpm.extension.admin.upload import group as package_group

# -- constants -----------------------------------------------------------------

DESC_EXPORT_STATUS = _('displays the status of a running ISO export of a repository')

# ------------------------------------------------------------------------------

def initialize(context):
    structure.ensure_repo_structure(context.cli)
    upload_manager = _upload_manager(context)

    repo_section = structure.repo_section(context.cli)
    repo_section.add_command(repo.RpmRepoCreateCommand(context))
    repo_section.add_command(repo.RpmRepoUpdateCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(repo.RpmRepoListCommand(context))
    repo_section.add_command(repo.RpmRepoSearchCommand(context))

    copy_section = structure.repo_copy_section(context.cli)
    copy_section.add_command(copy.RpmCopyCommand(context))
    copy_section.add_command(copy.SrpmCopyCommand(context))
    copy_section.add_command(copy.DrpmCopyCommand(context))

    remove_section = structure.repo_remove_section(context.cli)
    remove_section.add_command(remove.RpmRemoveCommand(context))
    remove_section.add_command(remove.SrpmRemoveCommand(context))
    remove_section.add_command(remove.DrpmRemoveCommand(context))
    remove_section.add_command(remove.ErrataRemoveCommand(context))
    remove_section.add_command(remove.PackageGroupRemoveCommand(context))
    remove_section.add_command(remove.PackageCategoryRemoveCommand(context))

    contents_section = structure.repo_contents_section(context.cli)
    contents_section.add_command(contents.SearchRpmsCommand(context))
    contents_section.add_command(contents.SearchDrpmsCommand(context))
    contents_section.add_command(contents.SearchSrpmsCommand(context))
    contents_section.add_command(contents.SearchPackageGroupsCommand(context))
    contents_section.add_command(contents.SearchPackageCategoriesCommand(context))
    contents_section.add_command(contents.SearchDistributionsCommand(context))
    contents_section.add_command(contents.SearchErrataCommand(context))

    uploads_section = structure.repo_uploads_section(context.cli)
    uploads_section.add_command(package.CreateRpmCommand(context, upload_manager))
    uploads_section.add_command(errata.CreateErratumCommand(context, upload_manager))
    uploads_section.add_command(package_group.CreatePackageGroupCommand(context, upload_manager))
    uploads_section.add_command(category.CreatePackageCategoryCommand(context, upload_manager))
    uploads_section.add_command(upload.ResumeCommand(context, upload_manager))
    uploads_section.add_command(upload.CancelCommand(context, upload_manager))
    uploads_section.add_command(upload.ListCommand(context, upload_manager))

    sync_section = structure.repo_sync_section(context.cli)
    renderer = status.RpmStatusRenderer(context)
    sync_section.add_command(sync_publish.RunSyncRepositoryCommand(context, renderer))
    sync_section.add_command(sync_publish.SyncStatusCommand(context, renderer))

    publish_section = structure.repo_publish_section(context.cli)
    renderer = status.RpmStatusRenderer(context)
    distributor_id = ids.TYPE_ID_DISTRIBUTOR_YUM
    publish_section.add_command(sync_publish.RunPublishRepositoryCommand(context, renderer, distributor_id))
    publish_section.add_command(sync_publish.PublishStatusCommand(context, renderer))

    export_section = structure.repo_export_section(context.cli)
    renderer = status.RpmIsoStatusRenderer(context)
    export_section.add_command(export.RpmIsoExportCommand(context))
    export_section.add_command(sync_publish.PublishStatusCommand(context, renderer, description=DESC_EXPORT_STATUS))

    sync_schedules_section = structure.repo_sync_schedules_section(context.cli)
    sync_schedules_section.add_command(sync_schedules.RpmCreateScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.RpmUpdateScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.RpmDeleteScheduleCommand(context))
    sync_schedules_section.add_command(sync_schedules.RpmListScheduleCommand(context))

    sync_schedules_section.add_command(sync_schedules.RpmNextRunCommand(context))


def _upload_manager(context):
    """
    Instantiates and configures the upload manager. The context is used to
    access any necessary configuration.

    :return: initialized and ready to run upload manager instance
    :rtype: UploadManager
    """
    upload_working_dir = context.config['filesystem']['upload_working_dir']
    upload_working_dir = os.path.expanduser(upload_working_dir)
    chunk_size = int(context.config['server']['upload_chunk_size'])
    upload_manager = upload_lib.UploadManager(upload_working_dir, context.server, chunk_size)
    upload_manager.initialize()
    return upload_manager
