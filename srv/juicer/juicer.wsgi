#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

import ConfigParser
import os

from juicer import runtime

# added potential paths to configuration files here
config_file_paths = [
    '/etc/juicer.ini',
    '/etc/pulp.ini',
]

parser = ConfigParser.SafeConfigParser()
parser.read(f for f in config_file_paths if os.access(f, os.F_OK|os.R_OK))
runtime.CONFIG = parser

from juicer.application import wsgi_application

application = wsgi_application()