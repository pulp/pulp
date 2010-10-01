#!/usr/bin/python
#
# Pulp Registration and subscription module
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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

import sys
import time
from gettext import gettext as _

import pulp.client.constants as constants
from pulp.client.connection import ConsumerConnection, RepoConnection
from pulp.client.core.base import print_header, BaseCore, system_exit, Action

# base package group action class ---------------------------------------------

class PackageGroupAction(Action):

    def connections(self):
        conns = {
            'pconn': RepoConnection,
            'cconn': ConsumerConnection,
        }
        return conns

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help="packagegroup id")


# package group actions -------------------------------------------------------

class List(PackageGroupAction):

    name = 'list'
    description = 'list available packagegroups'

    def setup_parser(self):
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")

    def run(self):
        repoid = self.get_required_option('repoid')
        groups = self.pconn.packagegroups(repoid)
        if not groups:
            system_exit(-1, _("no packagegroups found in repo [%s]") % (repoid))
        print_header("Repository: %s" % (repoid), "Package Group Information")
        for key in sorted(groups.keys()):
            print "\t %s" % (key)



class Info(PackageGroupAction):

    name = 'info'
    description = 'lookup information for a packagegroup'

    def setup_parser(self):
        super(Info, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")

    def run(self):
        groupid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        groups = self.pconn.packagegroups(repoid)
        if groupid not in groups:
            system_exit(-1, _("packagegroup [%s] not found in repo [%s]") %
                        (groupid, repoid))
        print_header("Package Group Information")
        info = groups[self.options.groupid]
        print constants.PACKAGE_GROUP_INFO % (
                info["name"], info["id"], info["mandatory_package_names"],
                info["default_package_names"], info["optional_package_names"],
                info["conditional_package_names"])



class Create(PackageGroupAction):

    name = 'create'
    description = 'create a packagegroup'

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")
        self.parser.add_option("--name", dest="groupname", help="group name")
        self.parser.add_option("--description", dest="description",
                               help="group description, default is ''", default="")

    def run(self):
        repoid = self.get_required_option('repoid')
        groupid = self.get_required_option('id')
        groupname = self.get_required_option('groupname')
        description = self.opts.description
        self.pconn.create_packagegroup(repoid, groupid, groupname, description)
        print_header("package group [%s] created in repository [%s]" %
                     (self.options.groupid, self.options.repoid))



class Delete(PackageGroupAction):

    name = 'delete'
    description = 'delete a packagegroup'

    def setup_parser(self):
        super(Delete, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")

    def run(self):
        repoid = self.get_required_option('repoid')
        groupid = self.get_required_option('id')
        self.pconn.delete_packagegroup(repoid, groupid)
        print _("packagegroup [%s] deleted from repository [%s]") % \
                (groupid, repoid)



class AddPackage(PackageGroupAction):

    name = 'add_package'
    description = 'add package to an existing packagegroup'

    def setup_parser(self):
        super(AddPackage, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")
        self.parser.add_option("-n", "--name", action="append", dest="pnames",
                               help="packages to be added; to specify multiple packages use multiple -n")
        self.parser.add_option("--type", dest="grouptype", default="default",
                               help="type of list to add package to, example 'mandatory', 'optional', 'default'")


    def run(self):
        repoid = self.get_required_option('repoid')
        pnames = self.get_required_option('pnames')
        groupid = self.get_required_option('id')
        grouptype = self.opts.grouptype
        self.pconn.add_packages_to_group(repoid, groupid, pnames, grouptype)
        print _("following packages added to group [%s] in repository [%s]: \n %s") % \
                (groupid, repoid, pnames)



class DeletePackage(PackageGroupAction):

    name = 'delete'
    description = 'delete package from an existing packagegroup'

    def setup_parser(self):
        super(DeletePackage, self).setup_parser()
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository label")
        self.parser.add_option("--pkgname", dest="pkgname", help="package name")
        self.parser.add_option("--type", dest="grouptype", default='default',
                               help="type of list to delete package from, example 'mandatory', 'optional', 'default'")

    def run(self):
        repoid = self.get_required_option('repoid')
        pkgname = self.get_required_option('pkgname')
        groupid = self.get_required_option('id')
        grouptype = self.opts.grouptype
        self.pconn.delete_package_from_group(repoid, groupid, pkgname, grouptype)
        print _("package [%s] deleted from group [%s] in repository [%s]") % \
                (pkgname, groupid, repoid)



class Install(PackageGroupAction):

    name = 'install'
    description = 'schedule a packagegroup install'

    def setup_parser(self):
        self.parser.add_option("-g", "--pkggroupid", action="append", dest="pkggroupid",
                               help="packagegroup to install on a given consumer; to specify multiple package groups use multiple -g")
        self.parser.add_option("--consumerid", dest="consumerid",
                               help="consumer id")

    def run(self):
        consumerid = self.get_required_option('consumerid')
        pkggroupid = self.get_required_option('pkggroupid')
        task = self.cconn.installpackagegroups(consumerid, pkggroupid)
        print _('created task ID: %s') % task['id']
        state = None
        spath = task['status_path']
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.cconn.task_status(spath)
            state = status['state']
        if state == 'finished':
            print _('\n[%s] installed on %s') % (status['result'], consumerid)
        else:
            print("\npackage group install failed")


# package group command -------------------------------------------------------

class PackageGroup(BaseCore):

    name = 'packagegroup'
    description = _('packagegroup specific actions to pulp server')
    _default_actions = ('list', 'info', 'create', 'delete',
                        'add_package', 'delete_package', 'install')

    def __init__(self, actions=None, action_state={}):
        super(PackageGroup, self).__init__(actions, action_state)
        self.list = List()
        self.info = Info()
        self.create = Create()
        self.delete = Delete()
        self.add_package = AddPackage()
        self.delete_package = DeletePackage()
        self.install = Install()


command_class = packagegroup = PackageGroup
