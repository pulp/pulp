# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from logging import getLogger

from pulp_rpm.handler.rpmtools import Package, PackageGroup, ProgressReport
from rhsm.profile import get_profile
from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import ProfileReport, ContentReport

log = getLogger(__name__)


class PackageReport(ContentReport):
    """
    Package (install|update|uninstall) report.
    Calculates the chgcnt.
    """

    def succeeded(self, details):
        chgcnt = \
            len(details['resolved'])+ \
            len(details['deps'])
        ContentReport.succeeded(self, details, chgcnt)


class GroupReport(ContentReport):
    """
    Package Group (install|update|uninstall) report.
    Calculates the chgcnt.
    """

    def succeeded(self, details):
        chgcnt = \
            len(details['resolved'])+ \
            len(details['deps'])
        ContentReport.succeeded(self, details, chgcnt)


class PackageProgress(ProgressReport):
    """
    Provides integration with the handler conduit.
    @ivar conduit: A handler conduit.
    @type conduit: L{pulp.agent.lib.conduit.Conduit}
    """

    def __init__(self, conduit):
        """
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        """
        ProgressReport.__init__(self)
        self.conduit = conduit

    def _updated(self):
        """
        Notification that the report has been updated.
        The updated report is sent to the server using the conduit.
        """
        report = dict(steps=self.steps, details=self.details)
        self.conduit.update_progress(report)


class PackageHandler(ContentHandler):
    """
    The package (rpm) content handler.
    @ivar cfg: configuration
    @type cfg: dict
    """

    def install(self, conduit, units, options):
        """
        Install content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit install options.
          - apply : apply the transaction
          - importkeys : import GPG keys
          - reboot : Reboot after installed
        @type options: dict
        @return: An install report.  See: L{Package.install}
        @rtype: L{PackageReport}
        """
        report = PackageReport()
        pkg = self.__impl(conduit, options)
        names = [key['name'] for key in units]
        details = pkg.install(names)
        report.succeeded(details)
        return report

    def update(self, conduit, units, options):
        """
        Update content unit(s).
        Unit key of {} or None indicates updates update all
        but only if (all) option is True.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit update options.
          - apply : apply the transaction
          - importkeys : import GPG keys
          - reboot : Reboot after installed
        @type options: dict
        @return: An update report.  See: L{Package.update}
        @rtype: L{PackageReport}
        """
        report = PackageReport()
        all = options.get('all', False)
        pkg = self.__impl(conduit, options)
        names = [key['name'] for key in units if key]
        if names or all:
            details = pkg.update(names)
            report.succeeded(details)
        return report

    def uninstall(self, conduit, units, options):
        """
        Uninstall content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit uninstall options.
          - apply : apply the transaction
          - reboot : Reboot after installed
        @type options: dict
        @return: An uninstall report.  See: L{Package.uninstall}
        @rtype: L{PackageReport}
        """
        report = PackageReport()
        pkg = self.__impl(conduit, options)
        names = [key['name'] for key in units]
        details = pkg.uninstall(names)
        report.succeeded(details)
        return report
    
    def profile(self, conduit):
        """
        Get package profile.
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @return: An profile report.
        @rtype: L{ProfileReport}
        """
        report = ProfileReport()
        details = get_profile("rpm").collect()
        report.succeeded(details)
        return report

    def __impl(self, conduit, options):
        """
        Get package implementation.
        @param options: Passed options.
        @type options: dict
        @return: A package object.
        @rtype: L{Package}
        """
        apply = options.get('apply', True)
        importkeys = options.get('importkeys', False)
        impl = Package(
            apply=apply,
            importkeys=importkeys,
            progress=PackageProgress(conduit))
        return impl


class GroupHandler(ContentHandler):
    """
    The package group content handler.
    @ivar cfg: configuration
    @type cfg: dict
    """

    def install(self, conduit, units, options):
        """
        Install content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit install options.
        @type options: dict
        @return: An install report.
        @rtype: L{GroupReport}
        """
        report = GroupReport()
        grp = self.__impl(conduit, options)
        names = [key['name'] for key in units]
        details = grp.install(names)
        report.succeeded(details)
        return report

    def uninstall(self, conduit, units, options):
        """
        Uninstall content unit(s).
        @param conduit: A handler conduit.
        @type conduit: L{pulp.agent.lib.conduit.Conduit}
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit uninstall options.
        @type options: dict
        @return: An uninstall report.
        @rtype: L{GroupReport}
        """
        report = GroupReport()
        grp = self.__impl(conduit, options)
        names = [key['name'] for key in units]
        details = grp.uninstall(names)
        report.succeeded(details)
        return report

    def __impl(self, conduit, options):
        """
        Get package group implementation.
        @param options: Passed options.
        @type options: dict
        @return: A package object.
        @rtype: L{Package}
        """
        apply = options.get('apply', True)
        importkeys = options.get('importkeys', False)
        impl = PackageGroup(
            apply=apply,
            importkeys=importkeys,
            progress=PackageProgress(conduit))
        return impl
