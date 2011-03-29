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

import os
import sys
import time
from gettext import gettext as _

import pulp.client.constants as constants
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit
from pulp.client.logutil import getLogger


_log = getLogger(__name__)

# base package group action class ---------------------------------------------

class PackageGroupAction(Action):

    def __init__(self):
        super(PackageGroupAction, self).__init__()
        self.consumer_api = ConsumerAPI()
        self.repository_api = RepositoryAPI()

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("package group id (required)"))

# package group actions -------------------------------------------------------

class List(PackageGroupAction):

    description = _('list available package groups')

    def setup_parser(self):
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        repoid = self.get_required_option('repoid')
        groups = self.repository_api.packagegroups(repoid)
        if not groups:
            system_exit(os.EX_DATAERR,
                        _("No package groups found in repo [%s]") % (repoid))
        print_header(_("Repository: %s") % (repoid), _("Package Group Information"))
        for key in sorted(groups.keys()):
            print "\t %s" % (key)
        


class Info(PackageGroupAction):

    description = _('lookup information for a package group')

    def setup_parser(self):
        super(Info, self).setup_parser()
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        groupid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        groups = self.repository_api.packagegroups(repoid)
        if not groups or groupid not in groups:
            system_exit(os.EX_DATAERR,
                        _("Package group [%s] not found in repo [%s]") %
                        (groupid, repoid))
        print_header(_("Package Group Information"))
        info = groups[groupid]
        print constants.PACKAGE_GROUP_INFO % (
                info["name"], info["id"], info["mandatory_package_names"],
                info["default_package_names"], info["optional_package_names"],
                info["conditional_package_names"])


class Create(PackageGroupAction):

    description = _('create a package group')

    def setup_parser(self):
        super(Create, self).setup_parser()
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-n", "--name", dest="name",
                               help=_("group name (required)"))
        self.parser.add_option("-d", "--description", dest="description", default="",
                               help=_("group description, default is ''"))

    def run(self):
        repoid = self.get_required_option('repoid')
        groupid = self.get_required_option('id')
        groupname = self.get_required_option('name')
        description = self.opts.description
        try:
            status = self.repository_api.create_packagegroup(repoid, groupid, groupname, description)
        except Exception, e:
            _log.error(_("Failed on group [%s] create:\n%s") % (groupid, e))
            status = False
        if not status:
            print _("Unable to create package group [%s] in repository [%s]") % \
                    (groupid, repoid)
        else:
            print _("Package group [%s] created in repository [%s]") % \
                (groupid, repoid)


class Delete(PackageGroupAction):

    description = _('delete a package group')

    def setup_parser(self):
        super(Delete, self).setup_parser()
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        repoid = self.get_required_option('repoid')
        groupid = self.get_required_option('id')
        try:
            self.repository_api.delete_packagegroup(repoid, groupid)
        except Exception, e:
            _log.error(e)
            print _("Unable to delete Packagegroup [%s] from repository [%s]") % \
                (groupid, repoid)
        else:
            print _("Packagegroup [%s] deleted from repository [%s]") % \
                (groupid, repoid)


class AddPackage(PackageGroupAction):

    description = _('add package to an existing package group')

    def setup_parser(self):
        super(AddPackage, self).setup_parser()
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-n", "--name", action="append", dest="name",
                               help=_("packages to be added; to specify multiple packages use multiple -n (required)"))
        self.parser.add_option("-t", "--type", dest="grouptype", default="default",
                               help=_("type of list to add package to, example 'mandatory', 'optional', 'default', 'conditional'"))
        self.parser.add_option("--requires", dest="requires", default=None,
                               help=_("required package name, only used by 'conditional' package group type"))

    def run(self):
        repoid = self.get_required_option('repoid')
        pnames = self.get_required_option('name')
        groupid = self.get_required_option('id')
        grouptype = self.opts.grouptype
        requires = None # Only used by conditional group type
        supported_types = ["mandatory", "optional", "default", "conditional"]
        if grouptype not in supported_types:
            system_exit(1,
                    _("Bad package group type [%s].  Supported types are: %s" % \
                        (grouptype, supported_types)))
        if grouptype == "conditional":
            requires = self.get_required_option("requires")

        self.repository_api.add_packages_to_group(repoid, groupid, pnames, grouptype, requires)
        if grouptype == "conditional":
            print _("Following packages added to group [%s] in repository [%s] for required package [%s]: \n %s") % \
                (groupid, repoid, requires, pnames)
        else:
            print _("Following packages added to group [%s] in repository [%s]: \n %s") % \
                (groupid, repoid, pnames)


class DeletePackage(PackageGroupAction):

    description = _('delete package from an existing package group')

    def setup_parser(self):
        super(DeletePackage, self).setup_parser()
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-n", "--name", dest="name",
                               help=_("package name (required)"))
        self.parser.add_option("-t", "--type", dest="grouptype", default='default',
                               help=_("type of list to delete package from, example 'mandatory', 'optional', 'default'"))

    def run(self):
        repoid = self.get_required_option('repoid')
        pkgname = self.get_required_option('name')
        groupid = self.get_required_option('id')
        grouptype = self.opts.grouptype
        try:
            self.repository_api.delete_package_from_group(repoid, groupid, pkgname, grouptype)
        except Exception, e:
            _log.error(e)
            print _("Unable to delete [%s] from group [%s] in repository [%s]") % \
                    (pkgname, groupid, repoid)
        else:
            print _("Package [%s] deleted from group [%s] in repository [%s]") % \
                    (pkgname, groupid, repoid)


class Install(PackageGroupAction):

    description = _('schedule a packagegroup install')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", action="append",
                               help=_("package group id (required)"))
        self.parser.add_option("--consumerid", dest="consumerid",
                               help=_("consumer id (required)"))

    def run(self):
        consumerid = self.get_required_option('consumerid')
        pkggroupid = self.get_required_option('id')
        task = self.consumer_api.installpackagegroups(consumerid, pkggroupid)
        print _('Created task id: %s') % task['id']
        state = None
        spath = task['status_path']
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.consumer_api.task_status(spath)
            state = status['state']
        if state == 'finished':
            print _('\n[%s] installed on %s') % (status['result'], consumerid)
        else:
            print("\nPackage group install failed")

# --- Package Group Category Operations ---
class ListCategory(PackageGroupAction):

    description = _('list available package group categories')

    def setup_parser(self):
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        repoid = self.get_required_option('repoid')
        cats = self.repository_api.packagegroupcategories(repoid)
        if not cats:
            system_exit(os.EX_DATAERR,
                        _("No package group categories found in repo [%s]") % (repoid))
        print_header(_("Repository: %s") % (repoid), _("Package Group Category Information"))
        for key in sorted(cats.keys()):
            print "\t %s" % (key)


class InfoCategory(PackageGroupAction):

    description = _('lookup information for a package group category')

    def setup_parser(self):
        self.parser.add_option("--categoryid", dest="categoryid",
                               help=_("category id (required)"))
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        categoryid = self.get_required_option('categoryid')
        repoid = self.get_required_option('repoid')
        cats = self.repository_api.packagegroupcategories(repoid)
        if not cats or categoryid not in cats:
            system_exit(os.EX_DATAERR,
                        _("Package group category [%s] not found in repo [%s]") %
                        (categoryid, repoid))
        print_header(_("Package Group Category Information"))
        info = cats[categoryid]
        print constants.PACKAGE_GROUP_CATEGORY_INFO % (
                info["name"], info["id"], info["packagegroupids"])

class CreateCategory(PackageGroupAction):

    description = _('create a package group category')

    def setup_parser(self):
        self.parser.add_option("--categoryid", dest="categoryid",
                               help=_("category id (required)"))
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-n", "--name", dest="name",
                               help=_("category name (required)"))
        self.parser.add_option("-d", "--description", dest="description", default="",
                               help=_("category description, default is ''"))

    def run(self):
        repoid = self.get_required_option('repoid')
        categoryid = self.get_required_option('categoryid')
        categoryname = self.get_required_option('name')
        description = self.opts.description
        try:
            status = self.repository_api.create_packagegroupcategory(repoid, categoryid,
                    categoryname, description)
        except Exception, e:
            _log.error(_("Failed on category [%s] create:\n%s") % (categoryid, e))
            status = False
        if not status:
            print _("Unable to create package group category [%s] in repository [%s]") % \
                    (categoryid, repoid)
        else:
            print _("Package group category [%s] created in repository [%s]") % \
                (categoryid, repoid)


class DeleteCategory(PackageGroupAction):

    description = _('delete a package group category')

    def setup_parser(self):
        self.parser.add_option("--categoryid", dest="categoryid",
                               help=_("category id (required)"))
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        repoid = self.get_required_option('repoid')
        categoryid = self.get_required_option('categoryid')
        try:
            self.repository_api.delete_packagegroupcategory(repoid, categoryid)
        except Exception, e:
            _log.error(e)
            print _("Unable to delete package group category [%s] from repository [%s]") % \
                (categoryid, repoid)
        else:
            print _("Package group category [%s] deleted from repository [%s]") % \
                (categoryid, repoid)

class InstallCategory(PackageGroupAction):

    description = _('schedule a packagegroupcategory install')

    def setup_parser(self):
        self.parser.add_option("--categoryid", dest="categoryid", action="append",
                               help=_("package group category id (required)"))
        self.parser.add_option("--consumerid", dest="consumerid",
                               help=_("consumer id (required)"))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repo id (required)"))

    def run(self):
        consumerid = self.get_required_option('consumerid')
        categoryid = self.get_required_option('categoryid')
        repoid = self.get_required_option('repoid')
        task = self.consumer_api.installpackagegroupcategories(consumerid,
                repoid, categoryid)
        print _('Created task id: %s') % task['id']
        state = None
        spath = task['status_path']
        while state not in ('finished', 'error', 'canceled', 'timed_out'):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.consumer_api.task_status(spath)
            state = status['state']
        if state == 'finished':
            print _('\n[%s] installed on %s') % (status['result'], consumerid)
        else:
            print("\nPackage group category install failed")

class AddGroupToCategory(PackageGroupAction):

    description = _('add package group to an existing package group category')

    def setup_parser(self):
        super(AddGroupToCategory, self).setup_parser()
        self.parser.add_option("--categoryid", dest="categoryid",
                               help=_("category id (required)"))
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        repoid = self.get_required_option('repoid')
        categoryid = self.get_required_option('categoryid')
        groupid = self.get_required_option('id')

        try:
            self.repository_api.add_packagegroup_to_category(repoid, categoryid, groupid)
        except Exception, e:
            _log.error(e)
            print _("Unable to add group [%s] to category [%s] in repository [%s]") % \
                    (groupid, categoryid, repoid)
        else:
            print _("Package group [%s] added to category [%s] in repository [%s]") % \
                (groupid, categoryid, repoid)



class DeleteGroupFromCategory(PackageGroupAction):

    description = _('delete package group from an existing package group category')

    def setup_parser(self):
        super(DeleteGroupFromCategory, self).setup_parser()
        self.parser.add_option("--categoryid", dest="categoryid",
                               help=_("category id (required)"))
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))

    def run(self):
        groupid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        categoryid = self.get_required_option('categoryid')
        try:
            self.repository_api.delete_packagegroup_from_category(repoid, categoryid, groupid)
        except Exception, e:
            _log.error(e)
            print _("Unable to delete [%s] from category [%s] in repository [%s]") % \
                    (groupid, categoryid, repoid)
        else:
            print _("Group [%s] deleted from category [%s] in repository [%s]") % \
                    (groupid, categoryid, repoid)
                    
class ImportComps(PackageGroupAction):
    
    description = _('Import package groups and categories from an existing comps.xml')
    
    def setup_parser(self):
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("--comps", dest="comps",
                               help=_("comps xml file to import (required)"))
        
    def run(self):
        repoid = self.get_required_option('repoid')
        compsfile = self.get_required_option('comps')
        
        if not os.path.exists(compsfile):
            system_exit(os.EX_DATAERR, _("Comps file could not be found."))
            
        try:
            compsobj = open(compsfile, 'r').read()
            status = self.repository_api.import_comps(repoid, compsobj)
        except Exception, e:
            _log.error(e)
            system_exit(os.EX_DATAERR, _("Comps file import failed with error %s") % e)
        
        if status:
            system_exit(os.EX_OK, _("Successfully imported comps groups and categories into repository [%s]") % repoid)
        else:
            system_exit(os.EX_DATAERR, _("Failed to import comps file. Please double check the comps file."))
            
class ExportComps(PackageGroupAction):
    
    description = _('Export comps.xml for package groups and categories in a repo')
    
    def setup_parser(self):
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-o", "--out", dest="out",
                               help=_("output file to store the exported comps data (optional); default is stdout"))
        
    def run(self):
        repoid = self.get_required_option('repoid')
        
        try:
            comps_xml = self.repository_api.export_comps(repoid)
        except Exception, e:
            _log.error(e)
            system_exit(os.EX_DATAERR, _("Error:%s") % e[1])
        else:
            if self.opts.out:
                try:
                    f = open(self.opts.out, 'w')
                    f.write(comps_xml.encode("utf8"))
                    f.close()
                except Exception,e:
                    system_exit(os.EX_DATAERR, _("Error occurred while storing the comps data %s" % e))
                system_exit(os.EX_OK, _("Successfully exported the comps data to [%s]" % self.opts.out))
            else:
                print comps_xml.encode("utf8")
    

# package group command -------------------------------------------------------

class PackageGroup(Command):

    description = _('package group specific actions to pulp server')
