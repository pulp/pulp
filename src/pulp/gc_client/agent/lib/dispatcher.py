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

from pulp.gc_client.agent.lib.handler import Handler
from pulp.gc_client.agent.lib.container import Container
from pulp.gc_client.agent.lib.container import CONTENT, DISTRIBUTOR
from pulp.gc_client.agent.lib.report import *


class HandlerNotFound(Exception):
    """
    Handler not found.
    """
    
    def __init__(self, **criteria):
        """
        @param criteria: The handler criteria.
        @type criteria: dict
        """
        Exception.__init__(self, criteria)

    def __str__(self):
        return 'No handler for: %s' % self.args[0]


class Dispatcher:
    """
    Dispatch (delegate) requests to handlers.
    @ivar container: A handler container.
    @type container: L{Container}
    """

    def __init__(self, container=None):
        """
        @param container: A handler container.
        @type container: L{Container}
        """
        self.container = container or Container()
        self.container.load()

    def install(self, units, options):
        """
        Install content unit(s).
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit install options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        report = DispatchReport()
        collated = Units(units)
        for typeid, units in collated.items():
            try:
                handler = self.__handler(typeid, CONTENT)
                r = handler.install(units, dict(options))
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = HandlerReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        rr = self.__reboot(report, options)
        report.update(rr)
        return report

    def update(self, units, options):
        """
        Update content unit(s).
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        report = DispatchReport()
        collated = Units(units)
        for typeid, units in collated.items():
            try:
                handler = self.__handler(typeid, CONTENT)
                r = handler.update(units, dict(options))
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = HandlerReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        rr = self.__reboot(report, options)
        report.update(rr)
        return report

    def uninstall(self, units, options):
        """
        Uninstall content unit(s).
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        report = DispatchReport()
        collated = Units(units)
        for typeid, units in collated.items():
            try:
                handler = self.__handler(typeid, CONTENT)
                r = handler.uninstall(units, dict(options))
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = HandlerReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        rr = self.__reboot(report, options)
        report.update(rr)
        return report

    def profile(self, types):
        """
        Request the installed content profile be sent
        to the pulp server.
        @param types: A list of content type IDs.
        @type types: list
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        report = DispatchReport()
        for typeid in types:
            try:
                handler = self.__handler(typeid, CONTENT)
                r = handler.profile()
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = ProfileReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        return report

    def reboot(self, options={}):
        """
        Schedule a reboot.
        @param options: reboot options.
        @type options: dict
        Find the 1st handler that implements reboot() and
        dispatch to that handler.
        @return: A reboot report.
        @rtype: L{RebootReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        NAME = 'reboot'
        for handler in self.container.all():
            method = getattr(handler, NAME, 0)
            if not callable(method):
                continue
            try:
                return handler.reboot(options)
            except Exception:
                r = RebootReport()
                r.failed(ExceptionReport())
                return r
        report = RebootReport()
        report.failed(dict(message='handler not found'))
        return report

    def bind(self, info):
        """
        Bind a repository.
        @param info: The bind informataion.
        @type info: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        report = DispatchReport()
        try:
            typeid = info['type_id']
            handler = self.__handler(typeid, DISTRIBUTOR)
            r = handler.bind(info)
            r.typeid = typeid
            report.update(r)
        except Exception:
            r = ProfileReport()
            r.typeid = typeid
            r.failed(ExceptionReport())
            report.update(r)
        return report

    def unbind(self, info):
        """
        Unbind a repository.
        @param info: The bind informataion.
        @type info: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        @raise HandlerNotFound: When hanlder not found.
        """
        report = DispatchReport()
        try:
            typeid = info['type_id']
            handler = self.__handler(typeid, DISTRIBUTOR)
            r = handler.bind(info)
            r.typeid = typeid
            report.update(r)
        except Exception:
            r = ProfileReport()
            r.typeid = typeid
            r.failed(ExceptionReport())
            report.update(r)
        return report

    def __reboot(self, report, options):
        """
        Schedule a reboot based on I{options} and reported progress.
        @param report: A dispatch report.
        @type report: L{DispatchReport}
        @param options: reboot options.
        @type options: dict
        @raise HandlerNotFound: When hanlder not found.
        """
        reboot = options.get('reboot', 0)
        if reboot:
            if report.chgcnt:
                return self.reboot(options)
        return RebootReport()

    def __handler(self, typeid, role):
        """
        Find a handler by type ID.
        @param typeid: A content type ID.
        @type typeid: str
        @param role: The handler role requested.
        @type role: int
        @return: The found handler.
        @rtype: L{Handler}
        @raise HandlerNotFound: When not found.
        """
        handler = self.container.find(typeid, role)
        if handler is None:
            raise HandlerNotFound(type=typeid)
        else:
            return handler


class Units(dict):
    """
    Collated content units
    """

    def __init__(self, units):
        """
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        """
        for unit in units:
            typeid = unit['type_id']
            lst = self.get(typeid)
            if lst is None:
                lst = []
                self[typeid] = lst
            lst.append(unit['unit_key'])
