# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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
from pprint import pformat

from pulp.server.exceptions import (
    ConflictingOperation, PulpExecutionException, PulpDataException,
    SuperfluousData)

# call exceptions --------------------------------------------------------------

class CallRuntimeError(PulpExecutionException):
    pass

class MissingControlHook(CallRuntimeError):
    pass

class MissingCancelControlHook(MissingControlHook):
    pass

class CallValidationError(PulpDataException):
    pass

class InvalidCallKeywordArgument(CallValidationError):
    pass

class MissingProgressCallbackKeywordArgument(InvalidCallKeywordArgument):
    pass

class MissingSuccessCallbackKeywordArgument(InvalidCallKeywordArgument):
    pass

class MissingFailureCallbackKeywordArgument(InvalidCallKeywordArgument):
    pass

class SynchronousCallTimeoutError(CallRuntimeError):
    pass

class AsynchronousExecutionError(CallRuntimeError):
    pass

class UnrecognizedSearchCriteria(SuperfluousData):
    pass

# call rejected exception ------------------------------------------------------

class CallRejectedException(ConflictingOperation):

    def __init__(self, serialized_call_report):
        ConflictingOperation.__init__(self, serialized_call_report)
        self.serialized_call_report = serialized_call_report

    def __str__(self):
        msg = _('Call rejected due to conflicting operations')
        return msg.encode('utf-8')

    def data_dict(self):
        return {'call_report': self.serialized_call_report}
