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

import os
import sys

from pulp.client.consumer.exception_handler import ConsumerExceptionHandler
from pulp.client import launcher


def main():
    # Default static config
    config_files = ['/etc/pulp/consumer/consumer.conf']

    # Any conf.d entries
    conf_d_dir = '/etc/pulp/consumer/conf.d'
    config_files += [os.path.join(conf_d_dir, i) for i in sorted(os.listdir(conf_d_dir))]

    # Local user overrides
    override = os.path.expanduser('~/.pulp/consumer.conf')
    if os.path.exists(override):
        config_files.append(override)

    exit_code = launcher.main(
        config_files, exception_handler_class=ConsumerExceptionHandler
    )
    sys.exit(exit_code)
