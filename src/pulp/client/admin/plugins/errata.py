#
# Pulp Repo management module
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
import string
import sys
import time
from gettext import gettext as _
from optparse import OptionGroup
from pulp.common import dateutils
from pulp.common.capabilities import AgentCapabilities
from pulp.client.admin.plugin import AdminPlugin
from pulp.client import constants
from pulp.client.api.job import JobAPI, job_end
from pulp.client.api.task import TaskAPI, task_end, task_succeeded
from pulp.client.api.service import ServiceAPI
from pulp.client.lib import utils
from pulp.client.lib.logutil import getLogger
from pulp.client.plugins.errata import ErrataAction, Errata, List


log = getLogger(__name__)

# errata actions --------------------------------------------------------------

class Info(ErrataAction):

    name = "info"
    description = _('see details on a specific errata')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help=_("errata id (required)"))

    def run(self):
        id = self.get_required_option('id')
        errata = self.errata_api.erratum(id)
        if not errata:
            utils.system_exit(os.EX_DATAERR, _("Errata Id %s not found." % id))
        effected_pkgs = [str(pinfo['filename'])
                         for pkg in errata['pkglist']
                         for pinfo in pkg['packages']]
        ref = ""
        for reference in errata['references']:
            for key, value in reference.items():
                ref += "\n\t\t\t%s : %s" % (key, value)
        print constants.ERRATA_INFO % (errata['id'], errata['title'],
                                       errata['description'], errata['type'],
                                       errata['issued'], errata['updated'],
                                       errata['version'], errata['release'],
                                       errata['status'], ",\n\t\t\t".join(effected_pkgs),
                                       errata['reboot_suggested'], ref)


class Search(ErrataAction):

    name = "search"
    description = _('search for a specific errata')

    def __init__(self, cfg):
        super(Search, self).__init__(cfg)
        self.id_field_size = 20
        self.type_field_size = 15

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help=_("errata id"))
        self.parser.add_option("--title", dest="title", help=_("errata title"))
        self.parser.add_option("--type", dest="type",
                               help=_("type of errata to search; eg. security, bugfix etc."))
        self.parser.add_option("--bzid", dest="bzid", help=_("reference bugzilla id"))
        self.parser.add_option("--cve", dest="cve", help=_("reference CVE"))
        self.parser.add_option("--orphaned", action="store_false", dest="orphaned", default=True,
                               help=_("search only orphaned packages"))

    def run(self):
        orphaned = getattr(self.opts, 'orphaned', True)
        if orphaned:
            orphaned_value = True
        else:
            orphaned_value = False
        
        errata = self.errata_api.errata(id=self.opts.id, title=self.opts.title, types=self.opts.type,
                                        repo_defined=orphaned_value, bzid=self.opts.bzid, cve=self.opts.cve)
        print _("\n%s\t%s\t%s\n" % (self.form_item_string("Id", self.id_field_size),
                self.form_item_string("Type", self.type_field_size),
                "Title"))
        for erratum in errata:
            print "%s\t%s\t%s" % \
                (self.form_item_string(erratum["id"], self.id_field_size),
                 self.form_item_string(erratum["type"], self.type_field_size),
                 erratum['title'])

    def form_item_string(self, msg, field_size):
        return string.ljust(msg, field_size)


class Install(ErrataAction):

    name = "install"
    description = _('install errata on a consumer')

    def __init__(self, cfg):
        super(Install, self).__init__(cfg)
        self.job_api = JobAPI()
        self.task_api = TaskAPI()
        self.service_api = ServiceAPI()

    def setup_parser(self):
        self.parser.add_option("-e", "--erratum", action="append", dest="id",
                               help=_("id of the erratum to be installed; to specify multiple erratum use multiple uses of this flag"))
        id_group = OptionGroup(self.parser, _('Consumer or Consumer Group id (one is required)'))
        id_group.add_option("--consumerid", dest="consumerid",
                            help=_("consumer id"))
        id_group.add_option("--consumergroupid", dest="consumergroupid",
                            help=_("consumer group id"))
        self.parser.add_option_group(id_group)
        self.parser.add_option("-i", "--importkeys", action="store_true", dest="importkeys",
                            help=_("permit the import of GPG keys as needed"))
        self.parser.add_option("--when", dest="when", default=None,
                       help=_("specifies when to execute the install.  "
                       "Format: iso8601, YYYY-MM-DDThh:mm"))
        self.parser.add_option("--nowait", dest="nowait", default=False,
            action="store_true",
            help=_("if specified, don't wait for the install to finish, "
            "return immediately."))

    def run(self):
        errataids = self.opts.id
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            self.parser.error(_("A consumerid or a consumergroupid is required to perform an install"))
        if not errataids:
            utils.system_exit(os.EX_USAGE, _("Specify an erratum id to perform install"))
        importkeys = False
        if self.opts.importkeys:
            importkeys = True
        else:
            reboot_sugg = []
            for eid in errataids:
                eobj = self.errata_api.erratum(eid)
                if eobj:
                    reboot_sugg.append(eobj['reboot_suggested'])
            if True in reboot_sugg:
                ask_reboot = ''
                while ask_reboot.lower() not in ['y', 'n', 'q']:
                    ask_reboot = raw_input(_("\nOne or more erratum provided requires a system reboot. Would you like to perform a reboot if the errata is applicable and successfully installed(Y/N/Q):"))
                    if ask_reboot.strip().lower() == 'y':
                        importkeys = True
                    elif ask_reboot.strip().lower() == 'n':
                        importkeys = False
                    elif ask_reboot.strip().lower() == 'q':
                        utils.system_exit(os.EX_OK, _("Errata install aborted upon user request."))
                    else:
                        continue
        if consumerid:
            self.on_consumer(consumerid, errataids, importkeys=importkeys)
        elif self.opts.consumergroupid:
            self.on_group(consumergroupid, errataids, importkeys=importkeys)

    def on_consumer(self, id, errataids, importkeys):
        when = utils.parse_at_schedule(self.opts.when)
        wait = self.getwait([id,])
        task = self.consumer_api.installerrata(
                id,
                errataids,
                importkeys=importkeys,
                when=when)
        print _('Created task id: %s') % task['id']
        if when:
            print _('Task is scheduled for: %s') % when
        if not wait:
            utils.system_exit(0)
        utils.startwait()
        while not task_end(task):
            utils.printwait()
            task = self.task_api.info(task['id'])
        if task_succeeded(task):
            reboot = self.reboot_requested(task)
            result = task['result']
            installed = result['installed']['resolved']+result['installed']['deps']
            reboot_scheduled = result['reboot_scheduled']
            if installed:
                print _('\nErrata applied to [%s]; packages installed: %s' % \
                       (id, installed))
            else:
                print _('\nErrata applied to [%s]; no packages installed' % id)
            if reboot and not reboot_scheduled:
                print _('Please reboot at your earliest convenience')
        else:
            print("\nErrata install failed: %s" % task['exception'])

    def on_group(self, id, errataids, importkeys):
        when = utils.parse_at_schedule(self.opts.when)
        group = self.consumer_group_api.consumergroup(id)
        if not group:
            utils.system_exit(-1,
                _('Invalid group: %s' % id))
        wait = self.getwait(group['consumerids'])
        job = self.consumer_group_api.installerrata(
                id,
                errataids,
                importkeys=importkeys,
                when=when)
        print _('Created job id: %s') % job['id']
        if when:
            print _('Job is scheduled for: %s') % when
        if not wait:
            utils.system_exit(0)
        utils.startwait()
        while not job_end(job):
            job = self.job_api.info(job['id'])
            utils.printwait()
        print _('\nInstall Summary:')
        for t in job['tasks']:
            state = t['state']
            exception = t['exception']
            id, packages = t['args']
            if exception:
                details = '; %s' % exception
            else:
                s = []
                reboot = self.reboot_requested(t)
                result = t['result']
                installed = result['installed']['resolved']+result['installed']['deps']
                reboot_scheduled = result['reboot_scheduled']
                if reboot and not reboot_scheduled:
                    s.append('reboot needed')
                s.append('packages installed: %s' % installed)
                details = ', '.join(s)
            print _('\t[ %-8s ] %s; %s' % (state.upper(), id, details))

    def reboot_requested(self, task):
        return task['args'][1]

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
            if not utils.askcontinue():
                utils.system_exit(0)
            # The consumer is unavailable, if wait was specified, verify that
            # we still want to wait.
            if wait:
                wait = utils.askwait()
        return wait


class Create(ErrataAction):
    
    name = "create"
    description = _('create a custom errata')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("advisory id of the erratum to be created"))
        self.parser.add_option("--title", dest="title",
                               help=_("title of the erratum"))
        self.parser.add_option("--description", dest="description", default="",
                               help=_("description of the erratum"))
        self.parser.add_option("--version", dest="version",
                               help=_("version of the erratum"))
        self.parser.add_option("--release", dest="release",
                               help=_("release of the erratum"))
        self.parser.add_option("--type", dest="type",
                               help=_("type of the erratum.Supported:security, enhancement, bugfix"))
        self.parser.add_option("--issued", dest="issued",default="",
                               help=_("erratum issued date; format:YYYY-MM-DD HH:MM:SS"))
        self.parser.add_option("--status", dest="status",
                               help=_("status of this update. eg:stable"))
        self.parser.add_option("--updated", dest="updated",default="",
                               help=_("erratum updated date; format:YYYY-MM-DD HH:MM:SS"))
        self.parser.add_option("--fromstr", dest="fromstr",default="",
                               help=_("from contact string who released the Erratum, eg:updates@fedoraproject.org"))
        self.parser.add_option("--effected-packages", dest="pkgcsv",
                               help=_("a csv file with effected packages; format:name,version,release,epoch,arch,filename,checksum,checksum_type,sourceurl"))
        self.parser.add_option("--pushcount", dest="pushcount", default=1,
                               help=_("pushcount on the erratum"))
        self.parser.add_option("--references", dest="refcsv",
                            help=_("A reference csv file; format:href,type,id,title"))
        self.parser.add_option("--reboot-suggested", action="store_true", dest="reboot_sugg",
                            help=_("reboot suggested on errata"))
        self.parser.add_option("--short", dest="short",
                            help=_("short release name; eg: F14"))
        self.parser.add_option("--severity", dest="severity",
                            help=_("optional severity information; eg: Low,Moderate,Critical"))
        self.parser.add_option("--rights", dest="rights",
                            help=_("optional copyright information"))
        self.parser.add_option("--summary", dest="summary",
                            help=_("optional summary information"))
        self.parser.add_option("--solution", dest="solution",
                            help=_("optional solution information"))
        
        
    def run(self):
        errata_id = self.get_required_option('id')
        errata_title = self.get_required_option('title')
            
        if not self.opts.description:
            self.opts.description = self.opts.title
            
        errata_version = str(self.get_required_option('version'))
        errata_release = str(self.get_required_option('release'))
        errata_type = self.get_required_option('type')

        found = self.errata_api.erratum(errata_id)
        if found:
            utils.system_exit(os.EX_DATAERR, _("Erratum with id [%s] already exists on server." % errata_id))
        # process package list
        references = []
        if self.opts.refcsv:
            if not os.path.exists(self.opts.refcsv):
                utils.system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
            reflist = utils.parseCSV(self.opts.refcsv)
            for ref in reflist:
                if not len(ref) == 4:
                    log.error(_("Bad format [%s] in csv, skipping" % ref))
                    continue
                href,type,id,title = ref
                refdict = dict(href=href,type=type,id=id,title=title)
                references.append(refdict)
        #process references
        pkglist = []
        if self.opts.pkgcsv:
            if not os.path.exists(self.opts.pkgcsv):
                utils.system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
            plist = utils.parseCSV(self.opts.pkgcsv)
            pkgs = []
            for p in plist:
                if not len(p) == 9:
                    log.error(_("Bad format [%s] in csv, skipping" % p))
                    continue
                name,version,release,epoch,arch,filename,sums,type,sourceurl = p
                pdict = dict(name=name, version=version, release=release, 
                             epoch=epoch, arch=arch, filename=filename, sums=sums, type=type, src=sourceurl)
                pkgs.append(pdict)
            plistdict = {'packages' : pkgs,
                         'name'     : errata_release,
                         'short'    : self.opts.short or ""} 
            pkglist = [plistdict]
        pushcount = None
        try:
            pushcount = int(self.opts.pushcount)
        except:
            utils.system_exit(os.EX_DATAERR, _("Error: Invalid pushcount [%s]; should be an integer " % self.opts.pushcount))
        #create an erratum

        erratum_new = self.errata_api.create(errata_id, errata_title, self.opts.description,
                               errata_version, errata_release, errata_type,
                               status=self.opts.status, updated=self.opts.updated or "", 
                               issued=self.opts.issued or "", pushcount=pushcount,
                               update_id="", from_str=self.opts.fromstr or "", 
                               reboot_suggested=self.opts.reboot_sugg or "", 
                               references=references, pkglist=pkglist, severity=self.opts.severity or "",
                               rights=self.opts.rights or "", summary=self.opts.summary or "",
                               solution=self.opts.solution or "")
        if erratum_new:
            print _("Successfully created an Erratum with id [%s]" % erratum_new['id'])

class Update(ErrataAction):

    name = "update"
    description = _('update a custom errata')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
            help=_("advisory id of the erratum"))
        self.parser.add_option("--title", dest="title",
            help=_("title of the erratum"))
        self.parser.add_option("--description", dest="description", default="",
            help=_("description of the erratum"))
        self.parser.add_option("--version", dest="version",
            help=_("version of the erratum"))
        self.parser.add_option("--release", dest="release",
            help=_("release of the erratum"))
        self.parser.add_option("--type", dest="type",
            help=_("type of the erratum.Supported:security, enhancement, bugfix"))
        self.parser.add_option("--issued", dest="issued",default="",
            help=_("erratum issued date; format:YYYY-MM-DD HH:MM:SS"))
        self.parser.add_option("--status", dest="status",
            help=_("status of this update. eg:stable"))
        self.parser.add_option("--updated", dest="updated",default="",
            help=_("erratum updated date; format:YYYY-MM-DD HH:MM:SS"))
        self.parser.add_option("--fromstr", dest="fromstr",default="",
            help=_("from contact string who released the Erratum, eg:updates@fedoraproject.org"))
        self.parser.add_option("--effected-packages", dest="pkgcsv",
            help=_("a csv file with effected packages; format:name,version,release,epoch,arch,filename,checksum,checksum_type,sourceurl"))
        self.parser.add_option("--pushcount", dest="pushcount", default=1,
            help=_("pushcount on the erratum"))
        self.parser.add_option("--references", dest="refcsv",
            help=_("A reference csv file; format:href,type,id,title"))
        self.parser.add_option("--reboot-suggested", action="store_true", dest="reboot_sugg",
            help=_("reboot suggested on errata"))
        self.parser.add_option("--short", dest="short",
            help=_("short release name; eg: F14"))
        self.parser.add_option("--severity", dest="severity",
            help=_("optional severity information; eg: Low,Moderate,Critical"))
        self.parser.add_option("--rights", dest="rights",
            help=_("optional copyright information"))
        self.parser.add_option("--summary", dest="summary",
            help=_("optional summary information"))
        self.parser.add_option("--solution", dest="solution",
            help=_("optional solution information"))

    def run(self):
        id = self.get_required_option('id')
        found = self.errata_api.erratum(self.opts.id)
        if not found:
            utils.system_exit(os.EX_DATAERR, _("Erratum with id [%s] not found." % self.opts.id))
        delta = {}
        optdict = vars(self.opts)
        for k, v in optdict.items():
            if not v:
                continue
            if k == 'id':
                # cannot update id, skip
                continue
            if k == 'pkgcsv':
                plist = utils.parseCSV(self.opts.pkgcsv)
                pkgs = []
                for p in plist:
                    if not len(p) == 9:
                        log.error(_("Bad format [%s] in csv, skipping" % p))
                        continue
                    name,version,release,epoch,arch,filename,sums,type,sourceurl = p
                    pdict = dict(name=name, version=version, release=release,
                                 epoch=epoch, arch=arch, filename=filename, sums=sums, type=type, src=sourceurl)
                    pkgs.append(pdict)
                plistdict = {'packages' : pkgs,
                             'name'     : self.opts.release,
                             'short'    : self.opts.short or ""}
                pkglist = [plistdict]
                delta['pkglist'] = pkglist
                continue
            if k == 'refcsv':
                reflist = utils.parseCSV(self.opts.refcsv)
                references = []
                for ref in reflist:
                    if not len(ref) == 4:
                        log.error(_("Bad format [%s] in csv, skipping" % ref))
                        continue
                    href,type,id,title = ref
                    refdict = dict(href=href,type=type,id=id,title=title)
                    references.append(refdict)
                delta['references'] = references
                continue

            if k == 'pushcount':
                delta['pushcount'] = int(self.opts.pushcount)
                continue
            delta[k] = v
            continue
        erratum_updated = self.errata_api.update(found['id'], delta)
        if erratum_updated:
            print _("Successfully updated Erratum with id [%s]" % found['id'])
        else:
            utils.system_exit(os.EX_DATAERR, _("Unable to update Erratum with id [%s]; see pulp.log for more info." % found['id']))

class Delete(ErrataAction):
    
    name = "delete"
    description = _('delete a custom errata')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("errata id to delete"))
        
    def run(self):
        if not self.opts.id:
            utils.system_exit(os.EX_USAGE, _("Errata Id is required; see --help"))
        found = self.errata_api.erratum(self.opts.id)
        if not found:
            utils.system_exit(os.EX_DATAERR, _("Erratum with id [%s] not found." % self.opts.id))
        
        self.errata_api.delete(self.opts.id)
        print _("Successfully deleted Erratum with id [%s]" % self.opts.id)

# errata overridden actions --------------------------------------------------------------

class AdminList(List):

    def setup_parser(self):
        self.parser.add_option("--consumerid",
                               dest="consumerid",
                               default=None,
                               help=_('consumer id if a consumer doesn\'t exist locally'))
        List.setup_parser(self)


    def run(self):
        consumerid = self.opts.consumerid
        repoid = self.opts.repoid

        # Only do the double argument check when not running the consumer client
        if consumerid and repoid:
            utils.system_exit(os.EX_USAGE, _('Please select either a consumer or a repository, not both'))

        List.run(self, consumerid)

# errata command --------------------------------------------------------------

class AdminErrata(Errata):

    actions = [ AdminList,
                Search,
                Info,
                Install,
                Create,
                Update,
                Delete ]

# errata plugin --------------------------------------------------------------

class AdminErrataPlugin(AdminPlugin):

    name = "errata"
    commands = [ AdminErrata ]
