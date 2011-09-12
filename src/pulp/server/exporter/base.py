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
import sys
import logging
import shutil
import string
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.errata import ErrataApi
from pulp.server.api.package import PackageApi
from pulp.server.db import connection
from pulp.server.api.repo import RepoApi
from pulp.server.pexceptions import PulpException

log = logging.getLogger(__name__)

# --------- Exceptions ---------------------#

class ExportException(PulpException):
    pass

class MetadataException(ExportException):
    """
    raised when an error occurs generating metadata
    """
    pass

class WriteException(ExportException):
    """
    raised when exported content fails to write to the target location
    """
    pass

# --------- Base exporter module --------------------#

class BaseExporter(object):
    """
     Base Exporter module with common methods
    """
    def __init__(self, repoid, target_dir="./", start_date=None, end_date=None, force=False):
        """
        initialize exporter
        @param repoid: repository Id
        @type repoid: string
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        @param force: force certain operations while exporting content
        @type force: boolean
        """
        self.repoid = repoid
        self.target_dir = target_dir
        self.start_date = start_date
        self.end_date = end_date
        self.force = force
        self.progress = {
            'step': 'base',
            'count_total': 0,
            'count_remaining': 0,
            'num_error': 0,
            'num_success': 0,
            'errors': [],
        }
        self.init_pulp()
        
    def init_pulp(self):
        """
         Setup pulp server and DB connection and initialize content apis
        """
        # initialize DB
        connection.initialize()
        # initialize pulp components
        self.errata_api = ErrataApi()
        self.repo_api = RepoApi()
        self.package_api = PackageApi()
        self.distribution_api = DistributionApi()

    def get_repository(self):
        """
        Lookup repository id and get the repo object from pulp
        @rtype: object
        @return: Repository object
        """
        repo = self.repo_api.repository(self.repoid)
        if not repo:
            raise Exception("Repository id %s not found" % self.repoid)
        if repo['sync_in_progress']:
            raise Exception("Repository [%s] sync is in progress; cannot perform export" % self.repoid)
        return repo
    
    def export(self):
        """
         Implement the export logic in the plugin
         @rtype: dict
         @return: progress information
        """
        raise NotImplementedError()

    def validate_target_path(self):
        """
        Validate target directory path:
          * If path doesn't exists, create one
          * If path exists and not empty; if forced remove and create a fresh one.
        """
        if not os.path.exists(self.target_dir):
            log.info("Path %s does not exists; creating" % self.target_dir)
            os.mkdir(self.target_dir)
        if os.listdir(self.target_dir) and self.force:
            log.info("Target directory has content and force is set; cleaning up the directory for new export.")
            shutil.rmtree(self.target_dir)
            os.mkdir(self.target_dir)

    def get_report(self):
        raise NotImplementedError()