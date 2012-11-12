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
    The dispatch delegates operations to handlers based on
    the type_id specified in the request object.
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
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content units.
        @type units: list
        @param options: Unit install options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        dispatch_report = DispatchReport()
        collated = Units(units)
        for type_id, units in collated.items():
            try:
                handler = self.__handler(type_id, CONTENT)
                report = handler.install(conduit, units, dict(options))
                report.aggregation_key = type_id
                report.update(dispatch_report)
            except Exception:
                log.exception('handler failed')
                report = HandlerReport()
                report.aggregation_key = type_id
                report.set_failed(LastExceptionDetails())
                report.update(dispatch_report)
        mgr = RebootManager(conduit, self, options)
        reboot_report = mgr.reboot(dispatch_report.num_changes)
        reboot_report.update(dispatch_report)
        return dispatch_report

    def update(self, conduit, units, options):
        """
        Update content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content units.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        dispatch_report = DispatchReport()
        collated = Units(units)
        for type_id, units in collated.items():
            try:
                handler = self.__handler(type_id, CONTENT)
                report = handler.update(conduit, units, dict(options))
                report.aggregation_key = type_id
                report.update(dispatch_report)
            except Exception:
                log.exception('handler failed')
                report = HandlerReport()
                report.aggregation_key = type_id
                report.set_failed(LastExceptionDetails())
                report.update(dispatch_report)
        mgr = RebootManager(conduit, self, options)
        reboot_report = mgr.reboot(dispatch_report.num_changes)
        reboot_report.update(dispatch_report)
        return dispatch_report

    def uninstall(self, conduit, units, options):
        """
        Uninstall content unit(s).
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content units.
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        dispatch_report = DispatchReport()
        collated = Units(units)
        for type_id, units in collated.items():
            try:
                handler = self.__handler(type_id, CONTENT)
                report = handler.uninstall(conduit, units, dict(options))
                report.aggregation_key = type_id
                report.update(dispatch_report)
            except Exception:
                log.exception('handler failed')
                report = HandlerReport()
                report.aggregation_key = type_id
                report.set_failed(LastExceptionDetails())
                report.update(dispatch_report)
        mgr = RebootManager(conduit, self, options)
        reboot_report = mgr.reboot(dispatch_report.num_changes)
        reboot_report.update(dispatch_report)
        return dispatch_report

    def profile(self, conduit):
        """
        Get an installed content unit report.
        Each handler registered to support content operations is
        called and the returned profile reports are aggregated by
        the type_id to which each handler is registered.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        NAME = 'profile'
        dispatch_report = DispatchReport()
        for type_id, handler in self.container.all(CONTENT):
            method = getattr(handler, NAME, 0)
            if not callable(method):
                continue
            try:
                report = method(conduit)
                report.aggregation_key = type_id
                report.update(dispatch_report)
            except NotImplementedError:
                # optional
                pass
            except Exception:
                log.exception('handler failed')
                report = ProfileReport()
                report.set_failed(LastExceptionDetails())
                report.aggregation_key = type_id
                report.update(dispatch_report)
        return dispatch_report

    def reboot(self, conduit, options):
        """
        Schedule a reboot.
        Uses os.uname()[0] as type_id.  For linux this would be: 'Linux'
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param options: reboot options.
        @type options: dict
        @return: A dispatch report.
        @rtype: L{DispatchReport}
        """
        dispatch_report = DispatchReport()
        try:
            type_id = os.uname()[0]
            handler = self.__handler(type_id, SYSTEM)
            report = handler.reboot(conduit, options)
            report.aggregation_key = type_id
            report.update(dispatch_report)
        except Exception:
            log.exception('handler failed')
            report = RebootReport()
            report.set_failed(LastExceptionDetails())
            report.update(report)
        return dispatch_report

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
        dispatch_report = DispatchReport()
        for binding in bindings:
            type_id = binding.pop('type_id')
            try:
                handler = self.__handler(type_id, BIND)
                report = handler.bind(conduit, binding, options)
                report.aggregation_key = type_id
                report.update(dispatch_report)
            except Exception:
                log.exception('handler failed')
                report = BindReport(binding['repo_id'])
                report.aggregation_key = type_id
                report.set_failed(LastExceptionDetails())
                report.update(dispatch_report)
        return dispatch_report

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
        dispatch_report = DispatchReport()
        for binding in bindings:
            repo_id = binding['repo_id']
            type_id = binding.pop('type_id', None)
            try:
                if type_id:
                    handler = self.__handler(type_id, BIND)
                    report = handler.unbind(conduit, repo_id, options)
                    report.aggregation_key = type_id
                    report.update(dispatch_report)
                else:
                    reports = self.unbind_all(conduit, repo_id, options)
                    for r in reports:
                        r.update(dispatch_report)
            except Exception:
                log.exception('handler failed')
                report = BindReport(repo_id)
                report.aggregation_key = type_id
                report.set_failed(LastExceptionDetails())
                report.update(dispatch_report)
        return dispatch_report

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
        for type_id, handler in self.container.all(BIND):
            try:
                report = handler.unbind(conduit, repo_id, options)
                report.aggregation_key = type_id
                reports.append(report)
            except Exception:
                log.exception('handler failed')
                report = BindReport(repo_id)
                report.aggregation_key = type_id
                report.set_failed(LastExceptionDetails())
                reports.append(report)
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
        dispatch_report = DispatchReport()
        for type_id, handler in self.container.all():
            method = getattr(handler, NAME, 0)
            if not callable(method):
                continue
            try:
                report = method(conduit)
                report.aggregation_key = type_id
                report.update(dispatch_report)
            except NotImplementedError:
                # optional
                pass
            except Exception:
                log.exception('handler failed')
                report = CleanReport()
                report.set_failed(LastExceptionDetails())
                report.aggregation_key = type_id
                report.update(dispatch_report)
        return dispatch_report

    def __handler(self, type_id, role):
        """
        Find a handler by type ID.
        @param type_id: A content type ID.
        @type type_id: str
        @param role: The handler role requested.
        @type role: int
        @return: The found handler.
        @rtype: L{Handler}
        @raise HandlerNotFound: When not found.
        """
        handler = self.container.find(type_id, role)
        if handler is None:
            raise HandlerNotFound(type=type_id)
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

    def reboot(self, num_changes):
        """
        Request a reboot be scheduled.
        @param num_changes: The current change count.
        @type num_changes: int
        @return: A reboot report.
        @rtype: L{RebootReport}
        """
        report = RebootReport()
        requested = self.options.get('reboot', 0)
        if requested and num_changes > 0:
            dispatch_report = self.dispatcher.reboot(self.conduit, self.options)
            scheduled = dispatch_report.reboot['scheduled']
            details = dispatch_report.reboot['details']
            if dispatch_report.succeeded:
                report.set_succeeded(details, num_changes=1)
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
            type_id = unit['type_id']
            lst = self.get(type_id)
            if lst is None:
                lst = []
                self[type_id] = lst
            lst.append(unit['unit_key'])

