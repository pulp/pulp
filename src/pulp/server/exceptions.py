# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

# base exception class ---------------------------------------------------------

class PulpException(Exception):
    """
    Base exception class for Pulp.
    """
    def __unicode__(self):
        # NOTE this is the method that derived classes should override in order
        # to create custom messages
        class_name = unicode(self.__class__.__name__)
        return u'%s: %s' % (class_name, u', '.join(unicode(a) for a in self.args))

    def __str__(self):
        u = unicode(self)
        return u.encode('utf-8')


# execution exceptions ---------------------------------------------------------

class PulpExecutionException(PulpException):
    """
    Base class of exceptions raised during the execution of Pulp.

    This should include things like bad configuration values, operation
    failures (due to networking or tasking issues), or failure to find resources
    based on the input given
    """
    pass


class InvalidConfiguration(PulpExecutionException):
    pass


class MissingResource(PulpExecutionException):
    pass


class ConflictingOperation(PulpExecutionException):
    pass


class OperationFailed(PulpExecutionException):
    pass

# data exceptions --------------------------------------------------------------

class PulpDataException(PulpException):
    """
    Base class of exceptions raised due to data validation errors.

    This should include things like invalid, missing or superfluous data.
    """
    pass


class InvalidType(PulpDataException):
    pass


class InvalidValue(PulpDataException):
    pass


class MissingData(PulpDataException):
    pass


class SuperfluousData(PulpDataException):
    pass


class DuplicateResource(PulpDataException):
    pass
