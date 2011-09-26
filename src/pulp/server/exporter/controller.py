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
import pulp.server.util
from logging import getLogger
from pulp.server.exporter.base import BaseExporter, ExporterReport
from pulp.server.exporter.generate_iso import GenerateIsos

log = getLogger(__name__)
# --------------- constants ---------------------------#

_TOP_LEVEL_PACKAGE = 'pulp.server.exporter'
_EXPORTER_MODULES_PATH = os.path.dirname(__file__)

class ExportController(object):
    """
     Pulp Exporter controller class
    """
    def __init__(self, repo_object, target_directory, generate_iso=False,
                 overwrite=False, progress_callback=None):
        self.repo = repo_object
        self.target_dir = target_directory
        self.overwrite = overwrite
        self.generate_iso = generate_iso
        self.progress_callback = progress_callback
        self.progress = {
            'status': 'running',
            'item_name': None,
            'item_type': None,
            'count_total': 0,
            'count_remaining': 0,
            'num_error': 0,
            'num_success': 0,
            'details':{},
            'errors':[],
            'step': "STARTING",
        }

    def _load_exporter(self):
        """
        Discover and load available types of content to export
        @rtype: list
        @return: return list of exporter type modules that are subclasses of BaseExporter
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
        classes = sorted(self._load_exporter(), key=lambda mod: mod.__priority__)
        for cls in classes:
            try:
                exporter = cls(self.repo, target_dir=self.target_dir, progress=self.progress)
                self.progress = exporter.export(progress_callback=self.progress_callback)
            except Exception,e:
                log.error("Error occured processing module %s; Error:%s" % (cls, str(e)))
                continue
        self.progress = self.create_isos()

        self.progress['step'] = ExporterReport.done
        self.progress_callback(self.progress)

    def create_isos(self):
        """
         calculate the maximum size and wrap the exported content into iso files.
         supported types: CD, DVD, Blu-ray.
        """
        if not self.generate_iso:
            return
        save_iso_directory = os.path.join(self.target_dir, 'isos')
        try:
            gen_isos = GenerateIsos(self.target_dir, output_directory=save_iso_directory,
                                    prefix='pulp-%s' % self.repo['id'], progress=self.progress)
            return gen_isos.run(progress_callback=self.progress_callback)
        except Exception, e:
            log.error(str(e))