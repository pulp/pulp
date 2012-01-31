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

from pulp.server.exceptions import PulpException


class ContentManagerException(PulpException):
    """
    Base exception class thrown by content managers.
    """
    pass


class ContentUnitNotFound(ContentManagerException):
    """
    Exception raised when an individual content unit cannot be located.
    """
    pass


class ContentTypeNotFound(ContentManagerException):
    """
    Exception raise when an unsupported content type is used.
    """
    pass
