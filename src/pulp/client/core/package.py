#!/usr/bin/python
#
# Pulp Registration and subscription module
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import os
import sys
import time
from gettext import gettext as _

from pulp.client.connection import (
    setup_connection, RepoConnection, ConsumerConnection,
    ConsumerGroupConnection)
from pulp.client.core.base import Action, Command, print_header, system_exit

# package action base class ---------------------------------------------------

class PackageAction(Action):

    def setup_connections(self):
        self.pconn = setup_connection(RepoConnection)
        self.cconn = setup_connection(ConsumerConnection)
        self.cgconn = setup_connection(ConsumerGroupConnection)

# package actions -------------------------------------------------------------

class Info(PackageAction):

    name = 'info'
    description = 'lookup information for a package'

    def setup_parser(self):
        self.parser.add_option("-n", "--name", dest="name",
                               help="package name to lookup")
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")

    def run(self):
        name = self.get_required_option('name')
        repoid = self.get_required_option('repoid')
        pkg = self.pconn.get_package(repoid, name)
        if not pkg:
            system_exit(os.EX_DATAERR,
                        _("package [%s] not found in repo [%s]") %
                        (name, repoid))
        print_header("Package Information")
        for key, value in pkg.items():
            print """%s:                \t%-25s""" % (key, value)


class Install(PackageAction):

    name = 'install'
    description = 'schedule a package install'

    def setup_parser(self):
        self.parser.add_option("-n", "--name", action="append", dest="pnames",
                               help="packages to be installed; to specify multiple packages use multiple -n")
        self.parser.add_option("--consumerid", dest="consumerid",
                               help="consumer id")
        self.parser.add_option("--consumergroupid", dest="consumergroupid",
                               help="consumer group id")

    def run(self):
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            system_exit(os.EX_USAGE,
                        _("consumer or consumer group id required. try --help"))
        pnames = self.opts.pnames
        if not pnames:
            system_exit(os.EX_DATAERR, _("nothing to upload."))
        if consumergroupid:
            task = self.cgconn.installpackages(consumergroupid, pnames)
        else:
            task = self.cconn.installpackages(consumerid, pnames)
        print _('created task id: %s') % task['id']
        state = None
        spath = task['status_path']
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.cconn.task_status(spath)
            state = status['state']
        if state == 'finished':
            print _('\n[%s] installed on %s') % \
                  (status['result'], (consumerid or consumergroupid))
        else:
            print _("\npackage install failed")

# package command -------------------------------------------------------------

class Package(Command):

    name = 'package'
    description = _('package specific actions to pulp server')
    _default_actions = ('info', 'install')

    def __init__(self, actions=None):
        super(Package, self).__init__(actions)
        self.info = Info()
        self.install = Install()


command_class = Package
