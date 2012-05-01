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
from pulp.client.agent.container import Container


class HandlerNotFound(Exception):
    pass


class Dispatcher:

    def __init__(self, container=None):
        self.container = container or Container()
        self.container.load()

    def install(self, units, options):
        """
        Install content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit install options.
        @type options: dict
        """
        report = DispatchReport()
        collated = self.__collated(units)
        for type_id, units in collated.items():
            try:
                handler = self.__handler(type_id)
                r = handler.install(units, options)
                report.update(type_id, r)
            except Exception:
                report.raised(type_id)
        return report


    def update(self, units, options):
        """
        Update content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        """
        report = DispatchReport()
        collated = self.__collated(units)
        for type_id, units in collated.items():
            try:
                handler = self.__handler(type_id)
                r = handler.update(units, options)
                report.update(type_id, r)
            except Exception:
                report.raised(type_id)
        return report

    def uninstall(self, units, options):
        """
        Uninstall content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        """
        report = DispatchReport()
        collated = self.__collated(units)
        for type_id, units in collated.items():
            try:
                handler = self.__handler(type_id)
                hr = handler.uninstall(units, options)
                report.update(type_id, hr)
            except Exception:
                report.raised(type_id)
        return report

    def profile(self, type_id):
        handler = self.__handler(type_id)
        return handler.profile()

    def __handler(self, type_id):
        handler = self.container.find(type_id)
        if handler is None:
            raise HandlerNotFound(type_id)
        return handler

    def __collated(self, units):
        """
        Get collated units.
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units
        @type units: list
        @return: A dict of units collated by type_id.
        @rtype: dict
        """
        collated = {}
        for unit in units:
            type_id = unit['type_id']
            lst = collated.get(type_id)
            if lst is None:
                lst = []
                collated[type_id] = lst
            lst.append(unit['unit_key'])
        return collated


class Report:
    """
    Content install/update/uninstall report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool, True=succeeded
    @ivar reboot_scheduled: Indicates reboot was scheduled.
    @type reboot_scheduled: bool
    @ivar details: operation details keyed by type_id.
    @type details: dict
    """

    def __init__(self):
        self.status = True
        self.reboot_scheduled = False
        self.details = {}

    def __str__(self):
        return str(self.dict())

    def dict(self):
        """
        Dictionary representation.
        @return: A dict.
        @rtype: dict
        """
        return dict(
            status=self.status,
            reboot_scheduled=self.reboot_scheduled,
            details=self.details)


class HandlerReport(Report):
    """
    Content install/update/uninstall report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool, True=succeeded
    @ivar reboot_scheduled: Indicates reboot was scheduled.
    @type reboot_scheduled: bool
    @ivar details: operation details keyed by type_id.
    @type details: dict
    """

    def succeeded(self, details):
        """
        Called (by handler) on operation succeeded.
        @param type_id: The content type ID.
        @type type_id: str
        @param details: The details of the operation.
        @type details: dict
        """
        self.status = True
        self.details = dict(status=True, details=details)

    def failed(self, details):
        """
        Called (by handler) on operation failed.
        @param type_id: The content type ID.
        @type type_id: str
        @param details: The details of the operation.
        @type details: dict
        """
        self.status = False
        self.details = dict(status=False, details=details)


class DispatchReport(Report):
    """
    Content install/update/uninstall report.
    @ivar status: Overall status (succeeded|failed).
    @type status: bool, True=succeeded
    @ivar reboot_scheduled: Indicates reboot was scheduled.
    @type reboot_scheduled: bool
    @ivar details: operation details keyed by type_id.
    @type details: dict
    """

    def update(self, type_id, report):
        """
        Update using the specified report.
        @param report: A handler report.
        @type report: L{Report}
        @return: self
        @rtype: L{Report}
        """
        if not isinstance(report, Report):
            raise Exception('must be Report')
        if not report.status:
            self.status = False
        if report.reboot_scheduled:
            self.reboot_scheduled = True
        self.details[type_id] = report.details
        return self

    def raised(self, type_id):
        """
        The handler raised an exception.
        Used by L{Dispatcher} only.
        @param type_id: The content type ID.
        @type type_id: str
        @param details: The details of the operation.
        @type details: dict
        """
        self.status = False
        info = sys.exc_info()
        inst = info[1]
        trace = '\n'.join(tb.format_exception(*info))
        raised = dict(
            message=str(inst),
            trace=trace)
        self.details[type_id] = dict(status=False, details=raised)