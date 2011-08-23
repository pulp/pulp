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
from pulp.server.exporter.package import PackageExporter
from pulp.server.exporter.errata import ErrataExporter
from pulp.server.exporter.distribution import DistributionExporter

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
            print "Error: save directory not specified. Please use -d or --dir"
            return
        self.repoid = self.options.repoid
        if not self.repoid:
            print "Error: repository not specified. Please use -r or --repoid"
            return
        self.start_date = self.options.start_date
        self.end_date = self.options.end_date
        self.force = self.options.force
        self.make_isos = self.options.make_iso

    def export(self):
        for module in [PackageExporter, ErrataExporter, DistributionExporter]:
            exporter = module(self.repoid, target_dir=self.target_dir, start_date=self.start_date, end_date=self.end_date)
            print "Processing %s" % exporter
            exporter.export()
        self.create_isos()

    def create_isos(self):
        if not self.make_isos:
            return
        

if __name__== '__main__':
    pe = ExporterCLI()
    pe.export()
