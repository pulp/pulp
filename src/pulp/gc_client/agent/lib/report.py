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
    Content install/update/uninstall report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool
    @ivar details: operation details.
    @type details: dict
    @ivar chgcnt: The change count.
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
    Content install/update/uninstall report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool
    @ivar details: operation details.
    @type details: dict
    """

    def succeeded(self, details=None, chgcnt=0):
        """
        Called (by handler) on operation succeeded.
        @param typeid: The content type ID.
        @type typeid: str
        @param details: The details of the operation.
        @type details: dict
        @param chgcnt: The change count.
        @type chgcnt: int
        """
        self.status = True
        self.details = dict(status=True, details=(details or {}))
        self.chgcnt += chgcnt

    def failed(self, details):
        """
        Called (by handler) on operation failed.
        @param typeid: The content type ID.
        @type typeid: str
        @param details: The details of the operation.
        @type details: dict
        """
        self.status = False
        self.details = dict(status=False, details=details)


class RebootReport(Report):
    """
    Reboot report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool
    @ivar scheduled: Indicates whether a reboot has been scheduled.
    @type scheduled: bool
    @ivar details: reboot details.
    @type details: dict
    """

    def __init__(self):
        Report.__init__(self)
        self.scheduled = False

    def succeeded(self, scheduled=True, details=None):
        """
        Reboot requested and succeeded.
        @param scheduled: Indicates whether a reboot has been scheduled.
        @type scheduled: bool
        @param details: Scheduling details.
        @type details: dict
        """
        self.scheduled = scheduled
        self.details = (details or {})

    def failed(self, details={}):
        """
        Reboot requested and failed.
        @param details: Exception details.
        @type details: dict
        """
        self.status = False
        self.scheduled = False
        self.details = details


class ProfileReport(HandlerReport):
    """
    Profile report.
    """
    pass


class BindReport(HandlerReport):
    """
    A Bind Report
    """
    pass

class CleanReport(HandlerReport):
    """
    A Clean Report
    """
    pass


class DispatchReport(Report):
    """
    Content install/update/uninstall report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool
    @ivar reboot: Reboot status & details.
    @type reboot: dict
    @ivar details: operation details keyed by typeid.
    @type details: dict
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
        if isinstance(report, HandlerReport):
            self.details[report.typeid] = report.details
            return
        if isinstance(report, RebootReport):
            self.reboot = dict(
                scheduled=report.scheduled,
                details=report.details)
            return
        log.info('report: %s, ignored' % report)
        return self


class ExceptionReport(dict):
    """
    Exception Report
    """

    def __init__(self):
        info = sys.exc_info()
        inst = info[1]
        trace = '\n'.join(tb.format_exception(*info))
        self['message'] = str(inst)
        self['trace']=trace
