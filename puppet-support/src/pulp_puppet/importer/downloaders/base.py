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


class BaseDownloader(object):
    """
    Base class all downloaders should extend. The factory will pass the
    necessary data to the constructor; any subclass should support the
    same signature to ensure the factory can create it.
    """

    def __init__(self, repo, conduit, config, is_cancelled_call):
        self.repo = repo
        self.conduit = conduit
        self.config = config
        self.is_cancelled_call = is_cancelled_call

    def retrieve_metadata(self, progress_report):
        """
        Retrieves all metadata documents needed to fulfill the configuration
        set for the repository. The progress report will be updated as the
        downloads take place.

        :param progress_report: used to communicate the progress of this operation
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :return: list of JSON documents describing all modules to import
        :rtype:  list
        """
        raise NotImplementedError()

    def retrieve_module(self, progress_report, module):
        """
        Retrieves the given module and returns where on disk it can be
        found. It is the caller's job to copy this file to where Pulp
        wants it to live as its final resting place. This downloader will
        then be allowed to clean up the downloaded file in the
        cleanup_module call.

        :param progress_report: used if any updates need to be made as the
               download runs
        :type  progress_report: pulp_puppet.importer.sync_progress.ProgressReport

        :param module: module to download
        :type  module: pulp_puppet.common.model.Module

        :return: full path to the temporary location where the module file is
        :rtype:  str
        """
        raise NotImplementedError()

    def cleanup_module(self, module):
        """
        Called once the unit has been copied into Pulp's storage location to
        let the downloader do any post-processing it needs (for instance,
        deleting any temporary copies of the file).

        :param module: module to clean up
        :type  module: pulp_puppet.common.model.Module
        """
        raise NotImplementedError()
