# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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

from pulp.client import launcher
from pulp.client.admin.exception_handler import AdminExceptionHandler
from pulp.client.admin.config import read_config


def main():
    exit_code = launcher.main(read_config(), exception_handler_class=AdminExceptionHandler)
    sys.exit(exit_code)
