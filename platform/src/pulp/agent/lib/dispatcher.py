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

from logging import getLogger

from pulp.agent.lib.container import Container
from pulp.agent.lib.container import SYSTEM, CONTENT, BIND
from pulp.agent.lib.report import *


log = getLogger(__name__)


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

    def install(self, conduit, units, options):
        """
        Install content unit(s).
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
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
                r = handler.install(conduit, units, dict(options))
                r.typeid = typeid
                r.update(report)
            except Exception:
                log.exception('handler failed')
                r = HandlerReport()
                r.typeid = typeid
                r.failed(LastExceptionDetails())
                r.update(report)
        mgr = RebootManager(conduit, self, options)
        rr = mgr.reboot(report.chgcnt)
        rr.update(report)
        return report

    def update(self, conduit, units, options):
        """
        Update content unit(s).
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
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
                r = handler.update(conduit, units, dict(options))
                r.typeid = typeid
                r.update(report)
            except Exception:
                log.exception('handler failed')
                r = HandlerReport()
                r.typeid = typeid
                r.failed(LastExceptionDetails())
                r.update(report)
        mgr = RebootManager(conduit, self, options)
        rr = mgr.reboot(report.chgcnt)
        rr.update(report)
        return report

    def uninstall(self, conduit, units, options):
        """
        Uninstall content unit(s).
        Unit is: {typeid:<str>, unit_key:<dict>}
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
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
                r = handler.uninstall(conduit, units, dict(options))
                r.typeid = typeid
                r.update(report)
            except Exception:
                log.exception('handler failed')
                r = HandlerReport()
                r.typeid = typeid
                r.failed(LastExceptionDetails())
                r.update(report)
        mgr = RebootManager(conduit, self, options)
        rr = mgr.reboot(report.chgcnt)
        rr.update(report)
        return report

    def profile(self, conduit):
        """
        Request the installed content profile be sent
        to the pulp server.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
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
                r = method(conduit)
                r.typeid = typeid
                r.update(report)
            except NotImplementedError:
                # optional
                pass
            except Exception:
                log.exception('handler failed')
                r = ProfileReport()
                r.failed(LastExceptionDetails())
                r.update(report)
        return report

    def reboot(self, conduit, options):
        """
        Schedule a reboot.
        Uses os.uname()[0] as typeid.  For linux this would be: 'Linux'
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param options: reboot options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        try:
            typeid = os.uname()[0]
            handler = self.__handler(typeid, SYSTEM)
            r = handler.reboot(conduit, options)
            r.typeid = typeid
            r.update(report)
        except Exception:
            log.exception('handler failed')
            r = RebootReport()
            r.failed(LastExceptionDetails())
            r.update(report)
        return report

    def bind(self, conduit, bindings, options):
        """
        Bind a repository.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param bindings: A list of bindings to add/update.
          Each binding is: {type_id:<str>, repo_id:<str>, details:<dict>}
            The 'details' are at the discretion of the distributor.
        @type bindings: list
        @param options: Bind options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        for binding in bindings:
            typeid = binding.pop('type_id')
            try:
                handler = self.__handler(typeid, BIND)
                r = handler.bind(conduit, binding, options)
                r.typeid = typeid
                r.update(report)
            except Exception:
                log.exception('handler failed')
                r = BindReport(binding['repo_id'])
                r.typeid = typeid
                r.failed(LastExceptionDetails())
                r.update(report)
        return report

    def unbind(self, conduit, bindings, options):
        """
        Unbind a repository.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param bindings: A list of bindings to be removed.
          Each binding is: {type_id:<str>, repo_id:<str>}
        @type bindings: list
        @param options: Unbind options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        report = DispatchReport()
        for binding in bindings:
            repo_id = binding['repo_id']
            typeid = binding.pop('type_id', None)
            try:
                if typeid:
                    handler = self.__handler(typeid, BIND)
                    r = handler.unbind(conduit, repo_id, options)
                    r.typeid = typeid
                    r.update(report)
                else:
                    reports = self.unbind_all(conduit, repo_id, options)
                    for r in reports:
                        r.update(report)
            except Exception:
                log.exception('handler failed')
                r = BindReport(repo_id)
                r.typeid = typeid
                r.failed(LastExceptionDetails())
                r.update(report)
        return report

    def unbind_all(self, conduit, repo_id, options):
        """
        Unbind a repository on all handlers.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param repo_id: A repository ID.
        @type repo_id: str
        @param options: Unbind options.
        @type options: dict
        @return: A list of UnbindReports
        @rtype: list
        """
        reports = []
        for typeid, handler in self.container.all(BIND):
            try:
                r = handler.unbind(conduit, repo_id, options)
                r.typeid = typeid
                reports.append(r)
            except Exception:
                log.exception('handler failed')
                r = BindReport(repo_id)
                r.typeid = typeid
                r.failed(LastExceptionDetails())
                reports.append(r)
        return reports

    def clean(self, conduit):
        """
        Notify all handlers to clean up artifacts.
        Dispatch clean() to ALL handlers.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
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
                r = method(conduit)
                r.typeid = typeid
                r.update(report)
            except NotImplementedError:
                # optional
                pass
            except Exception:
                log.exception('handler failed')
                r = CleanReport()
                r.failed(LastExceptionDetails())
                r.update(report)
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
    @ivar conduit: A handler conduit.
    @type conduit: L{pulp.agent.lib.conduit.Conduit}
    @ivar dispatcher: A dispatcher.
    @type dispatcher: L{Dispatcher}
    """

    def __init__(self, conduit, dispatcher, options):
        """
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param dispatcher: A dispatcher.
        @type dispatcher: L{Dispatcher}
        """
        self.conduit = conduit
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
            dr = self.dispatcher.reboot(self.conduit, self.options)
            scheduled = dr.reboot['scheduled']
            details = dr.reboot['details']
            if dr.status:
                report.succeeded(details, chgcnt=1)
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

