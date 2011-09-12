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
import glob
import os
import shutil
from logging import getLogger
from pulp.server.exporter.base import BaseExporter, ExportException

log = getLogger(__name__)
# --------------- constants ---------------------------#

_TOP_LEVEL_PACKAGE = 'pulp.server.exporter'
_EXPORTER_MODULES_PATH = os.path.dirname(__file__)

class ExportController(object):
    """
     Pulp Exporter controller class
    """
    def __init__(self, repo_object, target_directory, generate_iso=False, overwrite=False, progress_callback=None):
        self.repo = repo_object
        self.target_dir = target_directory
        self.overwrite = overwrite
        self.generate_iso = generate_iso
        self.progress_callback = progress_callback

    def validate_options(self):
        """
         Validate
         * If target dir doesn't exists, create one
         * If target dir exists and not empty; if forced remove and create a fresh one, else exit
         * dir, repoid are required
        """
        if not self.target_dir:
            raise ExportException("Error: target directory not specified")
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        if os.listdir(self.target_dir):
            if self.overwrite:
                shutil.rmtree(self.target_dir)
                os.mkdir(self.target_dir)
            else:
                raise ExportException("Error: Target directory already has content; must use force to overwrite.")

    def _load_exporter_plugins(self):
        """
        Discover and load available plugins from the exporter plugins directory
        @rtype: list
        @return: return list of exporter plugin modules that are subclasses of BaseExporter
        """
        plugins = []
        for plugin in glob.glob(os.path.join(_EXPORTER_MODULES_PATH, '*.py')):
            # import the module 
            module = __import__(_TOP_LEVEL_PACKAGE + '.' + \
                                os.path.basename(plugin).split('.')[0], fromlist = ["*"])
            for name, attr in module.__dict__.items():
                try:
                    if issubclass(attr, BaseExporter):
                        if attr == BaseExporter:
                            # BaseExporter can be a subclass of itself
                            continue
                        plugins.append(attr)
                except TypeError:
                    continue

        return plugins

    def perform_export(self):
        """
        Execute the exporter
        """
        self.validate_options()
        modules = sorted(self._load_exporter_plugins(), key=lambda mod: mod.__priority__)
        for module in modules:
            try:
                exporter = module(self.repo, target_dir=self.target_dir)
                exporter.export(progress_callback=self.progress_callback)
            except Exception,e:
                log.error("Error occured processing module %s; Error:%s" % (module, str(e)))
                continue
        self.create_isos()

    def create_isos(self):
        """
         calculate the maximum size and wrap the exported content into iso files.
         supported types: CD, DVD, Blu-ray.
        """
        if not self.generate_iso:
            return
