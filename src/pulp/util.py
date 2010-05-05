#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#
import rpm
import os


def getRPMInformation(rpmPath):
    """
    Get metadata about an RPM from the path passed in
    """
    
    long_variable_name = rpm.ts();
    file_descriptor_number = os.open(rpmPath, os.O_RDONLY)
    rpmInfo = long_variable_name.hdrFromFdno(file_descriptor_number);
    os.close(file_descriptor_number)
    return rpmInfo


