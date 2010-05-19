#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune, John Matthews
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

import xmlrpclib

class RhnApi(xmlrpclib.ServerProxy): 

    def __init__(self, uri, transport=None, encoding=None, verbose=0,
                 allow_none=0, use_datetime=0):
        xmlrpclib.ServerProxy.__init__(self, uri, transport, 
            encoding, verbose, allow_none)

def getRhnApi(uri, transport=None, encoding=None, verbose=0,
             allow_none=0, use_datetime=0):
        return RhnApi(uri, transport, encoding, verbose, 
            allow_none, use_datetime)
