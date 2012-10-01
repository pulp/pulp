#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import sys
import traceback as tb

from logging import getLogger


log = getLogger(__name__)


class Report(object):
    """
    The base report.
    @ivar status: The overall status (succeeded|failed).
    @type status: bool
    @ivar details: operation details.
    @type details: dict
    @ivar chgcnt: The number of changes made during the operation.
        The granularity is up to the discretion of the handler.
    @type chgcnt: int
    """

    def __init__(self):
        self.status = True
        self.details = {}
        self.chgcnt = 0

    def dict(self):
        """
        Dictionary representation.
        @return: A dict.
        @rtype: dict
        """
        return self.__dict__

    def __str__(self):
        return str(self.dict())

    def __len__(self):
        return self.chgcnt


class HandlerReport(Report):
    """
    Generic handler report.
    """

    def succeeded(self, details=None, chgcnt=0):
        """
        Called (by handler) on operation succeeded.
        @param typeid: The content type ID.
        @type typeid: str
        @param details: The details of the operation.
        @type details: dict
        @param chgcnt: The number of changes made during the operation.
            The granularity is up to the discretion of the handler.
        @type chgcnt: int
        """
        self.status = True
        self.details = (details or {})
        self.chgcnt = chgcnt

    def failed(self, details=None):
        """
        Called (by handler) on operation failed.
        @param typeid: The content type ID.
        @type typeid: str
        @param details: The details of the operation.
        @type details: dict
        """
        self.status = False
        self.details = (details or {})


class ContentReport(HandlerReport):
    """
    The content report is returned by handler methods
    implementing content unit operations.
    """
    pass


class ProfileReport(HandlerReport):
    """
    The profile report is returned by handler methods
    implementing content profile reporting operations.
    """
    pass


class BindReport(HandlerReport):
    """
    The profile report is returned by handler methods
    implementing repository bind operations.
    """
    pass

class CleanReport(HandlerReport):
    """
    The profile report is returned by handler methods
    implementing clean operations.
    """
    pass


class RebootReport(HandlerReport):
    """
    The profile report is returned by handler methods
    implementing reboot operations.  A chgcnt > 0 indicates
    the report was scheduled.
    """
    pass


class LastExceptionDetails(dict):
    """
    Last raised exception details.
    Intended to be passed to HandlerReport failed() as the I{details} parameter.
    This provides a structured way to consistently report exceptions raised
    in the handler call.
    """

    def __init__(self):
        info = sys.exc_info()
        inst = info[1]
        trace = '\n'.join(tb.format_exception(*info))
        self['message'] = str(inst)
        self['trace'] = trace


class DispatchReport(Report):
    """
    The (internal) dispatch report is returned for all handler methods
    dispatched to handlers.  It represents an aggregation of handler reports.
    The handler (class) reports are collated by type_id (content, distributor, system).
    The overall status is True (succeeded) only if all of the handler reports have
    a status of True (succeeded).
    Succeeded Example:
      { status : True,
        chgcnt : 10,
        details : {
          'type_A' : { 'status' : True, 'details' : {} },
          'type_B' : { 'status' : True, 'details' : {} },
          'type_C' : { 'status' : True, 'details' : {} },
        }
      }
    Failed Example:
      { status : False,
        chgcnt : 6,
        details : {
          'type_A' : { 'status' : True, 'details' : {} },
          'type_B' : { 'status' : True, 'details' : {} },
          'type_C' : { 'status' : False,
                       'details' : { 'message' : <message>, 'trace'=<trace> } },
        }
      }
    @ivar status: The overall status (succeeded|failed).
    @type status: bool
    @ivar details: operation details keyed by type_id.
      Each value is:
        { 'status' : True, details : {} }
    @type details: dict
    @ivar chgcnt: The number of changes made during the operation.
        The granularity is up to the discretion of the handlers.
    @type chgcnt: int
    """

    def __init__(self):
        Report.__init__(self)
        self.reboot = dict(scheduled=False, details={})

    def update(self, report):
        """
        Update using the specified handler report.
        @param report: A handler report.
        @type report: L{Report}
        @return: self
        @rtype: L{DispatchReport}
        """
        if isinstance(report, Report):
            if report.status:
                self.chgcnt += report.chgcnt
            else:
                self.status = False
        # continue updating
        if isinstance(report, RebootReport):
            scheduled = (report.chgcnt > 0)
            self.reboot = dict(scheduled=scheduled, details=report.details)
            return
        if isinstance(report, HandlerReport):
            self.details[report.typeid] = \
                dict(status=report.status, details=report.details)
            return
        log.info('report: %s, ignored' % report)
        return self
