# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains classes used by the RPM handler to perform
operations using YumBase.  This is provided by the following
collections of classes:
 * Layer 1: YumBase wrapper and callbacks
 * Layer 2: Package & PackageGroup provide a higher level abstraction for
   package and package group operations.
"""

from logging import getLogger, Logger

from yum import YumBase
from optparse import OptionParser
from yum.plugins import TYPE_CORE, TYPE_INTERACTIVE
from yum.rpmtrans import RPMBaseCallback, RPMTransaction
from yum.callbacks import DownloadBaseCallback, PT_MESSAGES


log = getLogger(__name__)


class Package:
    """
    Package management.
    Returned I{Package} NEVRA+ objects:
      - qname   : qualified name
      - repoid  : repository id
      - name    : package name
      - epoch   : package epoch
      - version : package version
      - release : package release
      - arch    : package arch
    """

    @classmethod
    def summary(cls, tsInfo, states=('i','u')):
        """
        Get transaction summary.
        @param tsInfo: A yum transaction.
        @type tsInfo: YumTransaction
        @param states: A list of yum transaction states.
        @type states: tuple|list
        @return: (resolved[],deps[])
        @rtype: tuple
        """
        resolved = []
        deps = []
        for t in tsInfo:
            if t.ts_state not in states:
                continue
            qname = str(t.po)
            package = dict(
                qname=qname,
                repoid=t.repoid,
                name=t.po.name,
                version=t.po.ver,
                release=t.po.rel,
                arch=t.po.arch,
                epoch=t.po.epoch)
            if t.isDep:
                deps.append(package)
            else:
                resolved.append(package)
        return (resolved, deps)

    @classmethod
    def installed(cls, tsInfo):
        """
        Get transaction summary for installed packages.
        @param tsInfo: A yum transaction.
        @type tsInfo: YumTransaction
        @return: (resolved[],deps[])
        @rtype: tuple
        """
        return cls.summary(tsInfo)

    @classmethod
    def erased(cls, tsInfo):
        """
        Get transaction summary for erased packages.
        @param tsInfo: A yum transaction.
        @type tsInfo: YumTransaction
        @return: (resolved[],deps[])
        @rtype: tuple
        """
        return cls.summary(tsInfo, ('e',))

    def __init__(self, apply=True, importkeys=False, progress=None):
        """
        @param apply: Apply changes (not dry-run).
        @type apply: bool
        @param importkeys: Allow the import of GPG keys.
        @type importkeys: bool
        @param progress: A progress report.
        @type progress: L{ProgressReport}
        """
        self.apply = apply
        self.importkeys = importkeys
        self.progress = progress

    def install(self, names):
        """
        Install packages by name.
        @param names: A list of package names.
        @type names: [str,]
        @return: Packages installed.
            {resolved=[Package,],deps=[Package,]}
        @rtype: dict
        """
        yb = Yum(self.importkeys, self.progress)
        try:
            for info in names:
                yb.install(pattern=info)
            yb.resolveDeps()
            resolved, deps = self.installed(yb.tsInfo)
            if self.apply and resolved:
                yb.processTransaction()
            else:
                yb.progress.set_status(True)
        finally:
            yb.close()
        return dict(resolved=resolved, deps=deps)

    def uninstall(self, names):
        """
        Uninstall (erase) packages by name.
        @param names: A list of package names to be removed.
        @type names: list
        @return: Packages uninstalled (erased).
            {resolved=[Package,],deps=[Package,]}
        @rtype: dict
        """
        yb = Yum(progress=self.progress)
        try:
            for info in names:
                yb.remove(pattern=info)
            yb.resolveDeps()
            resolved, deps = self.erased(yb.tsInfo)
            if self.apply and resolved:
                yb.processTransaction()
            else:
                yb.progress.set_status(True)
        finally:
            yb.close()
        return dict(resolved=resolved, deps=deps)

    def update(self, names=[]):
        """
        Update installed packages.
        When (names) is not specified, all packages are updated.
        @param names: A list of package names.
        @type names: [str,]
        @return: Packages installed (updated).
            {resolved=[Package,],deps=[Package,]}
        @rtype: dict
        """
        yb = Yum(self.importkeys, self.progress)
        try:
            if names:
                for info in names:
                    yb.update(pattern=info)
            else:
                yb.update()
            yb.resolveDeps()
            resolved, deps = self.installed(yb.tsInfo)
            if self.apply and resolved:
                yb.processTransaction()
            else:
                yb.progress.set_status(True)
        finally:
            yb.close()
        return dict(resolved=resolved, deps=deps)


class PackageGroup:
    """
    PackageGroup management.
    """

    def __init__(self, apply=True, importkeys=False, progress=None):
        """
        @param apply: Apply changes (not dry-run).
        @type apply: bool
        @param importkeys: Allow the import of GPG keys.
        @type importkeys: bool
        """
        self.apply = apply
        self.importkeys = importkeys
        self.progress = progress

    def install(self, names):
        """
        Install package groups by name.
        @param names: A list of package group names.
        @type names: list
        @return: Packages installed.
            {resolved=[Package,],deps=[Package,]}
        @rtype: dict
        """
        yb = Yum(self.importkeys, self.progress)
        try:
            for name in names:
                yb.selectGroup(name)
            yb.resolveDeps()
            resolved, deps = Package.installed(yb.tsInfo)
            if self.apply and resolved:
                yb.processTransaction()
            else:
                yb.progress.set_status(True)
        finally:
            yb.close()
        return dict(resolved=resolved, deps=deps)

    def uninstall(self, names):
        """
        Uninstall package groups by name.
        @param names: A list of package group names.
        @type names: [str,]
        @return: Packages uninstalled.
            {resolved=[Package,],deps=[Package,]}
        @rtype: dict
        """
        removed = {}
        yb = Yum(progress=self.progress)
        try:
            for name in names:
                yb.groupRemove(name)
            yb.resolveDeps()
            resolved, deps = Package.erased(yb.tsInfo)
            if self.apply and resolved:
                yb.processTransaction()
            else:
                yb.progress.set_status(True)
        finally:
            yb.close()
        return dict(resolved=resolved, deps=deps)


class ProgressReport:
    """
    Package (and group) progress reporting object.
    @ivar step: A list package steps.
        Each step is: (name, status)
    @type step: tuple
    @ivar details: Details about package actions taking place
        in the current step.
    """

    PENDING = None
    SUCCEEDED = True
    FAILED = False

    def __init__(self):
        """
        Constructor.
        """
        self.steps = []
        self.details = {}

    def push_step(self, name):
        """
        Push the specified step.
        First, update the last status to SUCCEEDED.
        @param name: The step name to push.
        @type name: str
        """
        self.set_status(self.SUCCEEDED)
        self.steps.append([name, self.PENDING])
        self.details = {}
        self._updated()

    def set_status(self, status):
        """
        Update the status of the current step.
        @param status: The status.
        @type status: bool
        """
        if not self.steps:
            return
        last = self.steps[-1]
        if last[1] is self.PENDING:
            last[1] = status
            self.details = {}
            self._updated()

    def set_action(self, action, package):
        """
        Set the specified package action for the current step.
        @param action: The action being performed.
        @type action: str
        """
        self.details = dict(action=action, package=str(package))
        self._updated()

    def error(self, msg):
        """
        Report an error on the current step.
        @param msg: The error message to report.
        @type msg: str
        """
        self.set_status(self.FAILED)
        self.details = dict(error=msg)
        self._updated()

    def _updated(self):
        """
        Notification that the report has been updated.
        Designed to be overridden and reported.
        """
        log.info('Progress [%s]:\n%s', self.steps, self.details)


class ProcessTransCallback:
    """
    The callback used by YumBase to report transaction progress.
    The event is forwarded to the report object to be consolidated
    with other reported progress information.
    @ivar report: A report object to be notified.
    @type report: L{ProgressReport}
    """

    def __init__(self, report):
        """
        @param report: A report object to be notified.
        @type report: L{ProgressReport}
        """
        self.report = report

    def event(self, state, data=None):
        """
        Called by YumBase to report transaction progress events.
        The event is forwarded to the report object to be consolidated
        with other reported progress information.
        @param state: The next state.
        @type state: int
        @param data: Information describing the event.
        @type data: object
        """
        if state in PT_MESSAGES:
            self.report.push_step(PT_MESSAGES[state])


class RPMCallback(RPMBaseCallback):
    """
    The RPM transaction progress callback.
    The event is forwarded to the report object to be consolidated
    with other reported progress information.
    @ivar report: A report object to be notified.
    @type report: L{ProgressReport}
    @ivar events: A set of event keys.
    @type events: set
    """

    def __init__(self, report):
        """
        @param report: A report object to be notified.
        @type report: L{ProgressReport}
        """
        RPMBaseCallback.__init__(self)
        self.report = report
        self.events = set()

    def event(self, package, action, *unused):
        """
        Notification of package progress events.
        This method is called multiple times to report progress on the
        same package/event combination.  The reporting is to granular for
        our purposes.  We store reported (package, action) tuples in a
        set which is used to ignore subsequent events for the same package
        and action combination.
        The event is forwarded to the report object to be consolidated
        with other reported progress information.
        @param package: A package object (subject of the event).
        @type package: str
        @param action: The action in progress on the package.
        @type action: int
        @param unused: Ignored parameters.
        """
        key = (str(package), action)
        if key in self.events:
            return
        self.events.add(key)
        self.report.set_action(self.action[action], package)

    def filelog(self, package, action):
        """
        Notification of file related package events.
        The event is forwarded to the report object to be consolidated
        with other reported progress information.
        Note: logging to /var/log/yum.log happens in the super impl.
        @param package: A package object (subject of the event).
        @type package: str
        @param action: The action in progress on the package.
        @type action: int
        """
        self.report.set_action(self.fileaction[action], package)

    def errorlog(self, msg):
        """
        Notification of package related errors.
        The event is forwarded to the report object to be consolidated
        with other reported progress information.
        @param msg: An error message.
        @type msg: str
        """
        self.report.error(msg)

    def verify_txmbr(self, base, tx, count):
        """
        Notification of package package verification.
        The event is forwarded to the report object to be consolidated
        with other reported progress information.
        @param base: The base transaction.
        @type base: object
        @param tx: A transaction member.
        @type tx: object
        @param count: The transaction member count.
        @type count: int
        """
        action = 'Verifying'
        self.report.set_action(action, tx.po)


class DownloadCallback(DownloadBaseCallback):
    """
    The callback used for YumBase to report file downloads.
    The event is forwarded to the report object to be consolidated
    with other reported progress information.
    @ivar report: A report object to be notified.
    @type report: L{ProgressReport}
    """

    def __init__(self, report):
        """
        @param report: A report object to be notified.
        @type report: L{ProgressReport}
        """
        DownloadBaseCallback.__init__(self)
        self.report = report

    def _do_start( self, now=None):
        """
        Notification that a file download has started.
        The event is forwarded to the report object to be consolidated
        with other reported progress information.
        @param now: timestamp.
        @type now: float
        """
        action = 'Downloading'
        package = ' | '.join((self._getName(), self.fsize))
        self.report.set_action(action, package)


class Yum(YumBase):
    """
    Provides custom configured yum object.
    This is where a bit of monkey business happens that
    provides the following:
      - Parser configuration so plugins will load.
      - Plugin loading.
      - Configuration as control GPG key importing.
      - Hack in callbacks for progress reporting.
      - Fix Logger leaks.
    """

    def __init__(self, importkeys=False, progress=None):
        """
        Construct a customized instance of YumBase.
        This includes:
          - loading yum plugins.
          - custom configuration.
          - setting the progress bar for download progress reporting.
          - prime our progress report object.
        @param importkeys: Allow the import of GPG keys.
        @type importkeys: bool
        @param progress: A progress reporting object.
        @type progress: L{ProgressReport}
        """
        parser = OptionParser()
        parser.parse_args([])
        self.__parser = parser
        YumBase.__init__(self)
        self.preconf.optparser = self.__parser
        self.preconf.plugin_types = (TYPE_CORE, TYPE_INTERACTIVE)
        self.conf.assumeyes = importkeys
        self.progress = progress or ProgressReport()
        bar = DownloadCallback(self.progress)
        self.repos.setProgressBar(bar)
        self.progress.push_step('Refresh Repository Metadata')

    def doPluginSetup(self, *args, **kwargs):
        """
        Set command line arguments.
        Support TYPE_INTERACTIVE plugins.
        """
        YumBase.doPluginSetup(self, *args, **kwargs)
        p = self.__parser
        options, args = p.parse_args([])
        self.plugins.setCmdLine(options, args)

    def registerCommand(self, command):
        """
        Support TYPE_INTERACTIVE plugins.
        Commands ignored.
        """
        pass

    def cleanLoggers(self):
        """
        Clean handlers leaked by yum.
        """
        def strip(logger):
            for handler in logger.handlers:
                logger.removeHandler(handler)
        try:
            for n,lg in Logger.manager.loggerDict.items():
                if n.startswith('yum.') and isinstance(lg, Logger):
                    strip(lg)
        except Exception:
            log.exception('logger cleanup failed')
            raise

    def close(self):
        """
        This should be handled by __del__() but YumBase
        objects never seem to completely go out of scope and
        garbage collected.
        """
        YumBase.close(self)
        self.closeRpmDB()
        self.cleanLoggers()

    def processTransaction(self):
        """
        Process the transaction.
        The method is overridden so we can add progress reporting.
        The I{callback} is used to report high-level progress.
        The I{display} is used to report rpm-level progress.
        """
        try:
            callback = ProcessTransCallback(self.progress)
            display = RPMCallback(self.progress)
            YumBase.processTransaction(self, callback, rpmDisplay=display)
            self.progress.set_status(True)
        except Exception:
            self.progress.set_status(False)
            raise

