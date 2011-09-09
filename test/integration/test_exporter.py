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
import sys
from pulp.server.exporter.package import PackageExporter
from pulp.server.exporter.errata import ErrataExporter
from pulp.server.exporter.distribution import DistributionExporter

def test_exporter(repoid, target_dir='', start_date=None, end_date=None):
    for module in [PackageExporter, ErrataExporter, DistributionExporter]:
        exporter = module(repoid, target_dir=target_dir, start_date=start_date, end_date=end_date)
        exporter.export()

if __name__== '__main__':
    if len(sys.argv) != 3:
        print "USAGE: python test_exporter.py <repoid> <target_dir>"
        sys.exit(0)
    test_exporter(sys.argv[1], sys.argv[2])    