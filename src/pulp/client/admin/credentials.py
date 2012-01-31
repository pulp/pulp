# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Module containing classes to manage client credentials.
"""

import os
from pulp.common.bundle import Bundle
from logging import getLogger

log = getLogger(__name__)

class Login(Bundle):
    """
    The bundle for logged in user.
    """

    ROOT = '~/.pulp'
    CRT = 'user-cert.pem'

    def __init__(self):
        path = os.path.join(self.ROOT, self.CRT)
        Bundle.__init__(self, path)
