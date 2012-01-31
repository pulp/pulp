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
import logging
import shutil
import pulp.server.util
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.errata import ErrataApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi
from pulp.server.exceptions import PulpException

log = logging.getLogger(__name__)

# --------- Exceptions ---------------------#

class ExportException(PulpException):
    pass

class MetadataException(ExportException):
    """
    raised when an error occurs generating metadata
    """
    pass

class TargetExistsException(ExportException):
    """
     raised when target directory already has content and overwrite is false
    """
    pass

# --------- Base exporter module --------------------#

class BaseExporter(object):
    """
     Base Exporter module with common methods
    """
    def __init__(self, repo, target_dir="./", start_date=None, end_date=None, overwrite=False, progress=None):
        """
        initialize exporter
        @param repo: repository object
        @type repo: Repo object
        @param target_dir: target directory where exported content is written
        @type target_dir: string
        @param start_date: optional start date from which the content needs to be exported
        @type start_date: date
        @param end_date: optional end date from which the content needs to be exported
        @type end_date: date
        @param overwrite: force certain operations while exporting content
        @type overwrite: boolean
        """
        self.repo = repo
        self.target_dir = target_dir
        self.start_date = start_date
        self.end_date = end_date
        self.overwrite = overwrite
        self.progress = progress

        self.old_progress = {
            'step': 'base',
            'count_total': 0,
            'count_remaining': 0,
            'num_error': 0,
            'num_success': 0,
            'errors': [],
            'status' : 'running',
            'details' : {}
        }
        self.report = ExporterReport()
        self.setup()
        
    def setup(self):
        """
         Setup pulp server initialize content apis
        """
        # initialize pulp components
        self.errata_api = ErrataApi()
        self.repo_api = RepoApi()
        self.package_api = PackageApi()
        self.distribution_api = DistributionApi()

    def set_callback(self, callback):
        self.callback = callback

    def progress_callback(self, **kwargs):
        """
        Callback called to update the pulp task's progress
        """
        if not self.callback:
            return
        for key in kwargs:
            self.progress[key] = kwargs[key]
        self.callback(self.progress)

    def export(self, progress_callback=None):
        """
         Implement the export logic in the plugin
         @rtype: dict
         @return: progress information
        """
        raise NotImplementedError()

    def get_report(self):
        raise NotImplementedError()

    def _progress_details(self, item_type, num_items):
        if not self.progress["details"].has_key(item_type):
            self.progress["details"][item_type] = {}
        self.progress['count_total'] += num_items
        self.progress['details'][item_type]["items_left"] = num_items
        self.progress['details'][item_type]["items_total"] = num_items
        self.progress['details'][item_type]["total_count"] = num_items
        self.progress['details'][item_type]["num_success"] = 0
        self.progress['details'][item_type]["num_error"] = 0



def exporter_progress_callback(progress):
    """
    This method will report exporter progress
    """
    return progress

class ExporterReport(object):
    rpm = "Exporting rpms"
    drpm = "Exporting delta rpms"
    comps = "Exporting packagegroups metadata"
    distribution = "Exporting Distribution files"
    errata = "Exporting errata "
    custom = "Exporting custom metadata files"
    start  = "Starting"
    done = "Finished"