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

from pulp.server.pexceptions import PulpException


class ConflictingPluginError(PulpException):
    """
    Raised when two or more plugins try to handle the same content or
    distribution type(s).
    """
    pass


class MalformedPluginError(PulpException):
    """
    Raised when a plugin does not provide required information or pass a sanity
    check.
    """
    pass


class PluginNotFoundError(PulpException):
    """
    Raised when no plugin is found for a content or distribution type.
    """
    pass
