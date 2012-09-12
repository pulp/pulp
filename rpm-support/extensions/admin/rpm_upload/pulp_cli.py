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

from gettext import gettext as _
import os

from pulp.client.commands.repo.upload import ResumeCommand, CancelCommand, ListCommand
import pulp.client.upload.manager as upload_lib

from   rpm_upload.package import CreateRpmCommand
from   rpm_upload.errata import CreateErratumCommand


def initialize(context):
    """
    :type context: pulp.client.extensions.core.ClientContext
    """
    upload_manager = _upload_manager(context)

    repo_section = context.cli.find_section('repo')
    uploads_section = repo_section.create_subsection('uploads', _('upload RPMs and create erratum, package groups, and categories'))

    uploads_section.add_command(CreateRpmCommand(context, upload_manager))
    uploads_section.add_command(CreateErratumCommand(context, upload_manager))
    uploads_section.add_command(ResumeCommand(context, upload_manager))
    uploads_section.add_command(CancelCommand(context, upload_manager))
    uploads_section.add_command(ListCommand(context, upload_manager))


def _upload_manager(context):
    """
    Instantiates and configures the upload manager. The context is used to
    access any necessary configuration.

    :return: initialized and ready to run upload manager instance
    :rtype:  UploadManager
    """
    upload_working_dir = context.config['filesystem']['upload_working_dir']
    upload_working_dir = os.path.expanduser(upload_working_dir)
    chunk_size = int(context.config['server']['upload_chunk_size'])
    upload_manager = upload_lib.UploadManager(upload_working_dir, context.server, chunk_size)
    upload_manager.initialize()
    return upload_manager
