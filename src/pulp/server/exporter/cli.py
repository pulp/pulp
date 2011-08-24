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
from optparse import Option, OptionParser
from pulp.server.exporter.base import BaseExporter

class ExporterCLI:
    def __init__(self):
        self.processOptions()

    def processOptions(self):
        optionsTable = [
            Option('-d','--dir',      action='store',
                help="directory for saving data"),
            Option('-r','--repoid',         action='store',
                help='process content for this repository'),
            Option(     '--start-date',         action='store',
                help='start date to export content'),
            Option(     '--end-date',         action='store',
                help='end date to export content'),
            Option(     '--make-iso',         action='store_true',
                help='generate isos for exported content'),
            Option('-f','--force',           action='store_true',
                help="force the overwrite of contents"),
                ]
        optionParser = OptionParser(option_list=optionsTable)
        self.options, self.args = optionParser.parse_args()
        self.validate_options()

    def validate_options(self):
        self.target_dir = self.options.dir
        if not self.target_dir:
            system_exit(os.EX_USAGE, "Error: save directory not specified. Please use -d or --dir")
        self.repoid = self.options.repoid
        if not self.repoid:
           system_exit(os.EX_USAGE, "Error: repository not specified. Please use -r or --repoid")
        self.start_date = self.options.start_date
        self.end_date = self.options.end_date
        self.force = self.options.force
        self.make_isos = self.options.make_iso

    def export(self):
        for module in self._load_exporter_plugins():
            exporter = module(self.repoid, target_dir=self.target_dir, start_date=self.start_date, end_date=self.end_date)
            exporter.export()
            exporter.get_progress()
        self.create_isos()

    def _load_exporter_plugins(self):
        plugin_dir = "plugins"
        lst = os.listdir(plugin_dir)
        # load the modules
        plugins = []
        for mod in lst:
            if mod.endswith('pyc'):
                continue
            module = __import__(plugin_dir + '.' + mod.split('.')[0], fromlist = ["*"])
            for name, attr in module.__dict__.items():
                try:
                    if issubclass(attr, BaseExporter):
                        if attr == BaseExporter:
                            continue
                        plugins.append(attr)
                except TypeError:
                    continue
        return plugins

    def create_isos(self):
        if not self.make_isos:
            return

def system_exit(code, msgs=None):
    """
    Exit with a code and optional message(s). Saves a few lines of code.
    @type code: int
    @param code: code to return
    @type msgs: str or list or tuple of str's
    @param msgs: messages to display
    """
    if msgs:
        if type(msgs) not in [type([]), type(())]:
            msgs = (msgs, )
        for msg in msgs:
            sys.stderr.write(str(msg)+'\n')
    sys.exit(code)


if __name__== '__main__':
    pe = ExporterCLI()
    pe.export()
