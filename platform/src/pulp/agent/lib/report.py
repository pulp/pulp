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
    @ivar succeeded: Indicates whether or not a handler operation succeeded.
    @type succeeded: bool
    @ivar details: Operation result details.
    @type details: dict
    @ivar num_changes: The number of changes made during the operation.
        The granularity is up to the discretion of the handler.
    @type num_changes: int
    """

    def __init__(self):
        self.succeeded = True
        self.details = {}
        self.num_changes = 0

    def dict(self):
        """
        Dictionary representation of the report.
        @return: A dict representation of self.
        @rtype: dict
        """
        return self.__dict__

    def __str__(self):
        return str(self.dict())

    def __len__(self):
        return self.num_changes


class HandlerReport(Report):
    """
    The base handler report.
    @ivar aggregation_key: The key used to aggregate details when
        updating another report.
    @type aggregation_key: str
    """

    def __init__(self):
        Report.__init__(self)
        self.aggregation_key = None

    def set_succeeded(self, details=None, num_changes=0):
        """
        Called to indicate an operation succeeded.
        @param details: The details of the operation result.
        @type details: dict
        @param num_changes: The number of changes made during the operation.
            The granularity is up to the discretion of the handler.
        @type num_changes: int
        """
        self.succeeded = True
        self.details = (details or {})
        self.num_changes = num_changes

    def set_failed(self, details=None):
        """
        Called to indicate an operation failed.
        @param details: The details of the failure.
        @type details: dict
        """
        self.succeeded = False
        self.details = (details or {})

    def update(self, report):
        """
        Update the specified report.
        @param report: An aggregation report.
        @type report: DispatchReport
        """
        self._update_succeeded(report)
        self._update_num_changes(report)
        self._update_details(report)

    def _update_succeeded(self, report):
        """
        Update the succeeded flag in the specified report.
        @param report: An aggregation report.
        @type report: DispatchReport
        """
        if not self.succeeded:
            report.succeeded = self.succeeded

    def _update_num_changes(self, report):
        """
        Update the num_changes in the specified report.
        @param report: An aggregation report.
        @type report: DispatchReport
        """
        if self.succeeded:
            report.num_changes += self.num_changes

    def _update_details(self, report):
        """
        Update the details in the specified report.
        The details are aggregated in the specified report using
        the aggregation key.
        @param report: An aggregation report.
        @type report: DispatchReport
        """
        report.details[self.aggregation_key] = \
            dict(succeeded=self.succeeded, details=self.details)


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
    The bind report is returned by handler methods
    implementing repository bind/unbind operations.
    @ivar repo_id: A repository ID.
    @type repo_id: str
    """

    def __init__(self, repo_id):
        """
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        self.repo_id = repo_id

    def _update_details(self, report):
        """
        Update the (details) in the specified report.
        Details are keyed by repo_id.
        @param report: An aggregation report.
        @type report: Report
        """
        bind_details = report.details.setdefault(self.aggregation_key, [])
        bind_details.append(dict(repo_id=self.repo_id, succeeded=self.succeeded, details=self.details))


class CleanReport(HandlerReport):
    """
    The clean report is returned by handler methods
    implementing clean operations.
    """
    pass


class RebootReport(HandlerReport):
    """
    The reboot report is returned by handler methods
    implementing reboot operations.
    """

    def __init__(self):
        HandlerReport.__init__(self)
        self.reboot_scheduled = False

    def set_succeeded(self, details=None, num_changes=0):
        """
        @param details: The details of the reboot.
        @type details: dict
        """
        HandlerReport.set_succeeded(self, details, num_changes)
        self.reboot_scheduled = True

    def _update_details(self, report):
        report.reboot = dict(scheduled=self.reboot_scheduled, details=self.details)


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
    The overall succeeded is True (succeeded) only if all of the handler reports have
    a succeeded of True (succeeded).
    Succeeded Example:
      { 'succeeded' : True,
        'num_changes' : 10,
        'reboot' : { 'scheduled' : False, details : {} },
        'details' : {
          'type_A' : { 'succeeded' : True, 'details' : {} },
          'type_B' : { 'succeeded' : True, 'details' : {} },
          'type_C' : { 'succeeded' : True, 'details' : {} },
        }
      }
    Failed Example:
      { 'succeeded' : False,
        'num_changes' : 6,
        'reboot' : { 'scheduled' : False, details : {} },
        'details' : {
          'type_A' : { 'succeeded' : True, 'details' : {} },
          'type_B' : { 'succeeded' : True, 'details' : {} },
          'type_C' : { 'succeeded' : False,
                       'details' : { 'message' : <message>, 'trace'=<trace> } },
        }
      }
    @ivar succeeded: The overall succeeded (succeeded|failed).
    @type succeeded: bool
    @ivar details: operation details keyed by aggregation_key.
      Each value is:
        { 'succeeded' : True, details : {} }
    @type details: dict
    @ivar num_changes: The number of changes made during the operation.
        The granularity is up to the discretion of the handlers.
    @type num_changes: int
    """

    def __init__(self):
        Report.__init__(self)
        self.reboot = dict(scheduled=False, details={})