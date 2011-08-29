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
import sys
from optparse import Option, OptionParser
from pulp.server.exporter.base import BaseExporter

_TOP_LEVEL_PLUGINS_PACKAGE = 'pulp.server.exporter'
_EXPORTER_PLUGINS_PATH = os.path.join(os.path.dirname(__file__), 'plugins')
_EXPORTER_PLUGINS_PACKAGE = '.'.join((_TOP_LEVEL_PLUGINS_PACKAGE, 'plugins'))

class ExporterCLI(object):
    """
     Pulp Exporter Commandline wrapper class
    """
    def __init__(self):
        self.processOptions()

    def processOptions(self):
        """
         Setup for commandline parser options
        """
        optionsTable = [
            Option('-d','--dir',      action='store',
                help="directory path to store the exported content"),
            Option('-r','--repoid',         action='store',
                help='export content from this repository'),
            Option(     '--start-date',         action='store',
                help='content start date from which the export begins'),
            Option(     '--end-date',         action='store',
                help='content end date to conclude the export'),
            Option(     '--make-iso',         action='store_true',
                help='generate isos for exported content'),
            Option('-f','--force',           action='store_true',
                help="force to overwrite existing content in target directory"),
                ]
        optionParser = OptionParser(option_list=optionsTable)
        self.options, self.args = optionParser.parse_args()
        if not self.options.dir and not self.options.repoid:
            system_exit(os.EX_USAGE, optionParser.print_help())
        self.validate_options()

    def validate_options(self):
        """
         Validate command line inputs and exit with relevant errors.
         * If target dir doesn't exists, create one
         * If target dir exists and not empty; if forced remove and create a fresh one, else exit
         * dir, repoid are required
        """
        self.target_dir = self.options.dir
        if not self.target_dir:
            system_exit(os.EX_USAGE, "Error: save directory not specified. Please use -d or --dir")
        if not os.path.exists(self.target_dir):
            os.mkdir(self.target_dir)
        if os.listdir(self.target_dir):
            if self.options.force:
                shutil.rmtree(self.target_dir)
                os.mkdir(self.target_dir)
            else:
                system_exit(os.EX_DATAERR, "Error: Target directory already has content; must use --force to overwrite.")
        self.repoid = self.options.repoid
        if not self.repoid:
           system_exit(os.EX_USAGE, "Error: repository not specified. Please use -r or --repoid")
        self.start_date = self.options.start_date
        self.end_date = self.options.end_date
        self.force = self.options.force
        self.make_isos = self.options.make_iso

    def _load_exporter_plugins(self):
        """
        Discover and load available plugins from the exporter plugins directory
        @rtype: list
        @return: return list of exporter plugin modules that are subclasses of BaseExporter
        """
        plugins = []
        for plugin in glob.glob(os.path.join(_EXPORTER_PLUGINS_PATH, '*.py')):
            # import the module 
            module = __import__(_EXPORTER_PLUGINS_PACKAGE + '.' + \
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

    def create_isos(self):
        if not self.make_isos:
            return

    def main(self):
        """
        Execute the exporter
        """
        plugins = self._load_exporter_plugins()
        plugins.sort(reverse=1)
        progress = []
        print("Export Operation on repository [%s] in progress.." % self.repoid)
        for module in plugins:
            exporter = module(self.repoid, target_dir=self.target_dir, start_date=self.start_date,
                              end_date=self.end_date)
            progress.append(exporter.export())
        self.create_isos()
        self.print_report(progress)

    def print_report(self, progress):
        # Output result
        print '\n'
        print "+-------------------------------------------+"
        print ('Exporter Report for repository [%s]' % self.repoid)
        print "+-------------------------------------------+"
        for report in progress:
            if not report:
                continue
            print('%s/%s %s' %
                  (report['num_success'], report['count_total'], report['step']))

    def print_errors(self, progress):
        pass


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
    pe.main()
