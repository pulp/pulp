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
import shutil

from base import BaseDownloader
from exceptions import FileNotFoundException
from pulp_puppet.common import constants


class LocalDownloader(BaseDownloader):
    """
    Used when the source for puppet modules is a directory local to the Pulp
    server.
    """

    def retrieve_metadata(self, progress_report):
        source_dir = self.config.get(constants.CONFIG_FEED)[len('file://'):]
        metadata_filename = os.path.join(source_dir, constants.REPO_METADATA_FILENAME)

        # Only do one query for this implementation
        progress_report.metadata_query_finished_count = 0
        progress_report.metadata_query_total_count = 1
        progress_report.metadata_current_query = metadata_filename
        progress_report.update_progress()

        if not os.path.exists(metadata_filename):
            # The caller will take care of stuffing this error into the
            # progress report
            raise FileNotFoundException(metadata_filename)

        f = open(metadata_filename, 'r')
        contents = f.read()
        f.close()

        progress_report.metadata_query_finished_count += 1
        progress_report.update_progress()

        return [contents]

    def retrieve_module(self, progress_report, module):

        # Determine the full path to the existing module on disk. This assumes
        # a structure where the modules are located in the same directory as
        # specified in the feed.

        source_dir = self.config.get(constants.CONFIG_FEED)[len('file://'):]
        module_filename = module.filename()
        full_filename = os.path.join(source_dir, module_filename)

        if not os.path.exists(full_filename):
            raise FileNotFoundException(full_filename)

        return full_filename

    def cleanup_module(self, module):
        # We don't want to delete the original location on disk, so do
        # nothing here.
        pass

