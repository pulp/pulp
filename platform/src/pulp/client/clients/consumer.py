# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _
import os
import sys

import pulp.client.launcher
from pulp.client.extensions.exceptions import ExceptionHandler, CODE_PERMISSIONS_EXCEPTION


# -- consumer client overrides ------------------------------------------------

class ConsumerExceptionHandler(ExceptionHandler):

    def handle_permission(self, e):
        """
        For this script, the register command is used and requires a valid user
        on the server to authenticate against. This override is used to tailor
        the displayed error message to that behavior.
        """

        self._log_client_exception(e)

        msg = _('Authentication Failed')

        desc = _('A valid Pulp user is required to register a new consumer. '
                 'Please double check the username and password and attempt the '
                 'request again.')

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)

        return CODE_PERMISSIONS_EXCEPTION

# -- script execution ---------------------------------------------------------

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

    exit_code = pulp.client.launcher.main(
        config_files, exception_handler_class=ConsumerExceptionHandler
    )
    sys.exit(exit_code)
