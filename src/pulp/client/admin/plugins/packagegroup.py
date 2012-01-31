#
# Pulp Registration and subscription module
# Copyright (c) 2011 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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
import sys
import time
from gettext import gettext as _
from optparse import OptionGroup
from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.consumergroup import ConsumerGroupAPI
from pulp.client.api.service import ServiceAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.api.job import JobAPI, job_end
from pulp.client.api.task import TaskAPI, task_end, task_succeeded
import pulp.client.constants as constants
from pulp.client.lib.utils import (
    print_header, system_exit, askwait, parse_at_schedule,
    askcontinue, startwait, printwait)
from pulp.common.capabilities import AgentCapabilities
from pulp.client.lib.logutil import getLogger
from pulp.client.pluginlib.command import Action, Command


_log = getLogger(__name__)

# base package group action class ---------------------------------------------

class PackageGroupAction(Action):

    def __init__(self, cfg):
        super(PackageGroupAction, self).__init__(cfg)
        self.consumer_api = ConsumerAPI()
        self.consumergroup_api = ConsumerGroupAPI()
        self.consumer_group_api = ConsumerGroupAPI()
        self.repository_api = RepositoryAPI()
        self.service_api = ServiceAPI()
        self.job_api = JobAPI()
        self.task_api = TaskAPI()

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("package group id (required)"))

# package group actions -------------------------------------------------------

class List(PackageGroupAction):

    name = "list"
    description = _('list available package groups')

    def setup_parser(self):
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-f", "--filter", action="store_true",
                        dest="filter_incomplete_groups", default=False,
                        help=_("drop groups with missing packages from result"))

    def run(self):
        repoid = self.get_required_option('repoid')
        filter_incomplete_groups = self.opts.filter_incomplete_groups
        groups = self.repository_api.packagegroups(repoid,
                                                   filter_incomplete_groups=filter_incomplete_groups)
        if not groups:
            system_exit(os.EX_DATAERR,
                        _("No package groups found in repo [%s]") % (repoid))
        print_header(_("Repository: %s") % (repoid), _("Package Group Information"))
        for key in sorted(groups.keys()):
            print "\t %s" % (key)
        


class Info(PackageGroupAction):

    name = "info"
    description = _('lookup information for a package group')

    def setup_parser(self):
        super(Info, self).setup_parser()
        self.parser.add_option("-r", "--repoid", dest="repoid",
                               help=_("repository label (required)"))
        self.parser.add_option("-f", "--filter", action="store_true",
                        dest="filter_missing_packages", default=False,
                        help=_("filter packages not in repo from result"))
    def run(self):
        groupid = self.get_required_option('id')
        repoid = self.get_required_option('repoid')
        filter_missing_packages = self.opts.filter_missing_packages
        groups = self.repository_api.packagegroups(repoid, filter_missing_packages=filter_missing_packages)
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

    name = "create"
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

    name = "delete"
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

    name = "add_package"
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

    name = "delete_package"
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

    name = "install"
    description = _('schedule a packagegroup install')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", action="append",
                               help=_("package group id (required)"))
        id_group = OptionGroup(self.parser,
                               _('Consumer or Consumer Group id (one is required'))
        id_group.add_option("--consumerid", dest="consumerid",
                            help=_("consumer id"))
        id_group.add_option("--consumergroupid", dest="consumergroupid",
                            help=_("consumer group id"))
        self.parser.add_option_group(id_group)
        self.parser.add_option("--nowait", dest="nowait", default=False,
            action="store_true",
            help=_("if specified, don't wait for the install to finish, "
            "return immediately."))
        self.parser.add_option("--when", dest="when", default=None,
                               help=_("specifies when to execute the install.  "
                               "Format: iso8601, YYYY-MM-DDThh:mm"))

    def run(self):
        grpids = self.get_required_option('id')
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if consumerid:
            self.on_consumer(consumerid, grpids)
        elif consumergroupid:
            self.on_group(consumergroupid, grpids)
        else:
            system_exit(-1, _("No consumerid or consumergroupid specified"))

    def on_consumer(self, id, grpids):
        when = parse_at_schedule(self.opts.when)
        wait = self.getwait([id,])
        task = self.consumer_api.installpackagegroups(id, grpids, when=when)
        print _('Created task id: %s') % task['id']
        if when:
            print _('Task is scheduled for: %s') % when
        if not wait:
            system_exit(0)
        startwait()
        while not task_end(task):
            printwait()
            task = self.task_api.info(task['id'])
        print_packages_installed(id, task)

    def on_group(self, id, grpids):
        when = parse_at_schedule(self.opts.when)
        group = self.consumer_group_api.consumergroup(id)
        if not group:
            system_exit(-1,
                _('Invalid group: %s' % id))
        wait = self.getwait(group['consumerids'])
        job = self.consumer_group_api.installpackagegroups(id, grpids, when=when)
        print _('Created job id: %s') % job['id']
        if when:
            print _('Job is scheduled for: %s') % when
        if not wait:
            system_exit(0)
        startwait()
        while not job_end(job):
            job = self.job_api.info(job['id'])
            printwait()
        print _('\nInstall Summary:')
        for task in job['tasks']:
            id, packages = task['args']
            print_packages_installed(id, task)

    def getunavailable(self, ids):
        lst = []
        stats = self.service_api.agentstatus(ids)
        for id in ids:
            stat = stats[id]
            if stat['online']:
                continue
            capabilities = AgentCapabilities(stat['capabilities'])
            if not capabilities.heartbeat():
                continue
            lst.append(id)
        return lst

    def printunavailable(self, ualist):
        if ualist:
            sys.stdout.write(constants.UNAVAILABLE)
            for id in ualist:
                print id

    def getwait(self, ids):
        wait = not self.opts.nowait
        ualist = self.getunavailable(ids)
        if ualist:
            self.printunavailable(ualist)
            if not askcontinue():
                system_exit(0)
            # The consumer is unavailable, if wait was specified, verify that
            # we still want to wait.
            if wait:
                wait = askwait()
        return wait


class Uninstall(Install):

    name = "uninstall"
    description = _('schedule a packagegroup uninstall')

    def on_consumer(self, id, grpids):
        when = parse_at_schedule(self.opts.when)
        wait = self.getwait([id,])
        task = self.consumer_api.uninstallpackagegroups(id, grpids, when=when)
        print _('Created task id: %s') % task['id']
        if when:
            print _('Task is scheduled for: %s') % when
        if not wait:
            system_exit(0)
        startwait()
        while not task_end(task):
            printwait()
            task = self.task_api.info(task['id'])
        print_packages_removed(id, task)

    def on_group(self, id, grpids):
        when = parse_at_schedule(self.opts.when)
        group = self.consumer_group_api.consumergroup(id)
        if not group:
            system_exit(-1,
                _('Invalid group: %s' % id))
        wait = self.getwait(group['consumerids'])
        job = self.consumer_group_api.uninstallpackagegroups(id, grpids, when=when)
        print _('Created job id: %s') % job['id']
        if when:
            print _('Job is scheduled for: %s') % when
        if not wait:
            system_exit(0)
        startwait()
        while not job_end(job):
            job = self.job_api.info(job['id'])
            printwait()
        print _('\nUninstall Summary:')
        for task in job['tasks']:
            id, packages = task['args']
            print_packages_removed(id, task)

# --- Package Group Category Operations ---
class ListCategory(PackageGroupAction):

    name = "list_category"
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

    name = "info_category"
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

    name = "create_category"
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

    name = "delete_category"
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

    name = "install_category"
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
        startwait()
        while not task_end(task):
            printwait()
            task = self.task_api.info(task['id'])
        if task_succeeded(task):
            print _('\n[%s] installed on %s') % (task['result'], consumerid)
        else:
            print("\nPackage group category install failed")

class AddGroupToCategory(PackageGroupAction):

    name = "add_group"
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

    name = "delete_group"
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
    
    name = "import"
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
    
    name = "export"
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

def print_packages_installed(consumerid, task):
    if task_succeeded(task):
        print '\nConsumer ID: %s  [ SUCCEEDED ]' % consumerid
    else:
        print '\nConsumer ID: %s  [ FAILED ] %s' % (consumerid, task['exception'])
        return
    installed = task['result']
    resolved = installed['resolved']
    if not resolved:
        print _('\nNothing to do')
        return
    print '====================================================================='
    print _('Package                           Arch     Version    Repository')
    print '====================================================================='
    print _('Installed:')
    for pkg in sorted_packages(resolved):
        print '%-33s %-8s %-10s %s' % \
            (pkg['name'],
             pkg['arch'],
             pkg['version'],
             pkg['repoid'])
    deps = installed['deps']
    if not deps:
        return
    print _('\nInstalled for dependencies:')
    for pkg in sorted_packages(deps):
        print '%-33s %-8s %-10s %s' % \
            (pkg['name'],
             pkg['arch'],
             pkg['version'],
             pkg['repoid'])

def print_packages_removed(consumerid, task):
    if task_succeeded(task):
        print '\nConsumer ID: %s  [ SUCCEEDED ]' % consumerid
    else:
        print '\nConsumer ID: %s  [ FAILED ] %s' % (consumerid, task['exception'])
        return
    uninstalled = task['result']
    resolved = uninstalled['resolved']
    if not resolved:
        print _('\nNothing to do')
        return
    print '====================================================================='
    print _('Package                           Arch     Version    Repository')
    print '====================================================================='
    print _('Removed:')
    for pkg in sorted_packages(resolved):
        print '%-33s %-8s %-10s %s' % \
            (pkg['name'],
             pkg['arch'],
             pkg['version'],
             pkg['repoid'])
    deps = uninstalled['deps']
    if not deps:
        return
    print _('\nRemoved for dependencies:')
    for pkg in sorted_packages(deps):
        print '%-33s %-8s %-10s %s' % \
            (pkg['name'],
             pkg['arch'],
             pkg['version'],
             pkg['repoid'])

def sorted_packages(packages):
    d = {}
    result = []
    for p in packages:
        d[p['name']] = p
    for k in sorted(d.keys()):
        result.append(d[k])
    return result
    
# package group command -------------------------------------------------------

class PackageGroup(Command):

    name = "packagegroup"
    description = _('package group specific actions to pulp server')

    actions = [ List,
                Info,
                Create,
                Delete,
                AddPackage,
                DeletePackage,
                Install,
                Uninstall,
                InstallCategory,
                ListCategory,
                InfoCategory,
                CreateCategory,
                DeleteCategory,
                AddGroupToCategory,
                DeleteGroupFromCategory,
                ImportComps,
                ExportComps ]

# package group plugin -------------------------------------------------------

class PackageGroupPlugin(AdminPlugin):

    name = "packagegroup"
    commands = [ PackageGroup ]
