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

import os
from pulp.gc_client.agent.lib.handler import Handler
from pulp.gc_client.agent.lib.container import Container
from pulp.gc_client.agent.lib.container import SYSTEM, CONTENT, BIND
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
        mgr = RebootManager(self, options)
        rr = mgr.reboot(report.chgcnt)
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
        mgr = RebootManager(self, options)
        rr = mgr.reboot(report.chgcnt)
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
        mgr = RebootManager(self, options)
        rr = mgr.reboot(report.chgcnt)
        report.update(rr)
        return report

    def profile(self):
        """
        Request the installed content profile be sent
        to the pulp server.
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        NAME = 'profile'
        report = DispatchReport()
        for typeid, handler in self.container.all(CONTENT):
            method = getattr(handler, NAME, 0)
            if not callable(method):
                continue
            try:
                r = method()
                r.typeid = typeid
                report.update(r)
            except NotImplementedError:
                # optional
                pass
            except Exception:
                r = ProfileReport()
                r.failed(ExceptionReport())
                report.update(r)
        return report

    def reboot(self, options={}):
        """
        Schedule a reboot.
        Uses os.uname()[0] as typeid.  For linux this would be: 'Linux'
        @param options: reboot options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        try:
            typeid = os.uname()[0]
            handler = self.__handler(typeid, SYSTEM)
            r = handler.reboot(options)
            r.typeid = typeid
            report.update(r)
        except Exception:
            r = RebootReport()
            r.failed(ExceptionReport())
            report.update(r)
        return report

    def bind(self, definitions):
        """
        Bind a repository.
        @param definitions: The list of bind definitions.
        Definition:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @type definitions: list
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        collated = Binds(definitions)
        for typeid, definition in collated.items():
            try:
                handler = self.__handler(typeid, BIND)
                r = handler.bind(definition)
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = ProfileReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        return report

    def rebind(self, definitions):
        """
        (Re)bind a repository.
        @param definitions: The list of bind definitions.
        Definition:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @type definitions: list
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        collated = Binds(definitions)
        for typeid, definition in collated.items():
            try:
                handler = self.__handler(typeid, BIND)
                r = handler.rebind(definition)
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = ProfileReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        return report

    def unbind(self, repoid):
        """
        Unbind a repository.
        Dispatch unbind() to all BIND handlers.
        @param repoid: A repository ID.
        @type repoid: str
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        for typeid, handler in self.container.all(BIND):
            try:
                r = handler.unbind(repoid)
                r.typeid = typeid
                report.update(r)
            except Exception:
                r = ProfileReport()
                r.typeid = typeid
                r.failed(ExceptionReport())
                report.update(r)
        return report

    def clean(self):
        """
        Notify all handlers to clean up artifacts.
        Dispatch clean() to ALL handlers.
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        NAME = 'clean'
        report = DispatchReport()
        for typeid, handler in self.container.all():
            method = getattr(handler, NAME, 0)
            if not callable(method):
                continue
            try:
                r = method()
                r.typeid = typeid
                report.update(r)
            except NotImplementedError:
                # optional
                pass
            except Exception:
                r = CleanReport()
                r.failed(ExceptionReport())
                report.update(r)
        return report

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


class RebootManager:
    """
    Reboot Manager
    @ivar dispatcher: A dispatcher.
    @type dispatcher: L{Dispatcher}
    """

    def __init__(self, dispatcher, options):
        """
        @param dispatcher: A dispatcher.
        @type dispatcher: L{Dispatcher}
        """
        self.dispatcher = dispatcher
        self.options = options

    def reboot(self, chgcnt):
        """
        Request a reboot be scheduled.
        @param chgcnt: The current change count.
        @type chgcnt: int
        @return: A reboot report.
        @rtype: L{RebootReport}
        """
        report = RebootReport()
        requested = self.options.get('reboot', 0)
        if requested and chgcnt > 0:
            dr = self.dispatcher.reboot(self.options)
            scheduled = dr.reboot['scheduled']
            details = dr.reboot['details']
            if dr.status:
                report.succeeded(scheduled, details)
            else:
                report.failed(details)
        return report


class Units(dict):
    """
    Collated content units
    """

    def __init__(self, units):
        """
        Unit is: {type_id:<str>, unit_key:<dict>}
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


class Binds(dict):
    """
    Collated bind definitions
    """

    def __init__(self, definitions):
        """
        @param definitions: A list of bind definitions.
        @type definitions: list
        """
        for definition in definitions:
            typeid = definition.pop('type_id')
            lst = self.get(typeid)
            if lst is None:
                lst = []
                self[typeid] = lst
            lst.append(definition)
