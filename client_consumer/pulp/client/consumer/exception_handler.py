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

import logging
from gettext import gettext as _

from pulp.client.extensions.exceptions import ExceptionHandler, CODE_PERMISSIONS_EXCEPTION


_logger = logging.getLogger(__name__)


class ConsumerExceptionHandler(ExceptionHandler):

    def handle_permission(self, e):
        """
        For this script, the register command is used and requires a valid user
        on the server to authenticate against. This override is used to tailor
        the displayed error message to that behavior.
        """

        msg = _('Authentication Failed')

        desc = _('A valid Pulp user is required to register a new consumer. '
                 'Please double check the username and password and attempt the '
                 'request again.')

        _logger.error("%(msg)s - %(desc)s" % {'msg': msg, 'desc': desc})

        self.prompt.render_failure_message(msg)
        self.prompt.render_paragraph(desc)

        return CODE_PERMISSIONS_EXCEPTION
