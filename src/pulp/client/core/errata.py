#!/usr/bin/python
#
# Pulp Repo management module
#
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
from optparse import OptionGroup, SUPPRESS_HELP

from pulp.client import utils
from pulp.client import constants
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.consumergroup import ConsumerGroupAPI
from pulp.client.api.errata import ErrataAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import system_exit, print_header
from pulp.client.logutil import getLogger

log = getLogger(__name__)

# errata action base class ----------------------------------------------------

class ErrataAction(Action):

    def __init__(self):
        super(ErrataAction, self).__init__()
        self.consumer_api = ConsumerAPI()
        self.consumer_group_api = ConsumerGroupAPI()
        self.errata_api = ErrataAPI()
        self.repository_api = RepositoryAPI()

# errata actions --------------------------------------------------------------

class List(ErrataAction):

    description = _('list applicable errata')

    def __init__(self, is_consumer_client=False):
        super(List, self).__init__()
        self.is_consumer_client = is_consumer_client

    def setup_parser(self):
        default = None
        consumerid = self.getconsumerid()

        # Only want to default the consumer ID when running the consumer client
        if consumerid is not None and self.is_consumer_client:
            default = consumerid
            help = SUPPRESS_HELP

        self.parser.add_option("--consumerid",
                               dest="consumerid",
                               default=default,
                               help=_('this option is required if a consumer doesn\'t exist locally'))
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repository id"))
        self.parser.add_option("--type", dest="type", action="append", default=[],
                               help=_("type of errata to lookup; supported types: security, bugfix, enhancement"))

    def run(self):
        consumerid = self.opts.consumerid
        repoid = self.opts.repoid

        if not (consumerid or repoid):
            system_exit(os.EX_USAGE, _("A consumer or a repository is required to lookup errata"))

        # Only do the double argument check when not running the consumer client
        if not self.is_consumer_client and (consumerid and repoid):
            system_exit(os.EX_USAGE, _('Please select either a consumer or a repository, not both'))

        # If running the consumer client, let the repo ID override the consumer's retrieved ID
        if self.is_consumer_client and repoid:
            consumerid = None

        if repoid:
            errata = self.repository_api.errata(repoid, self.opts.type)
            if errata:
                print_header(_("Available Errata in Repo [%s]" % repoid))
        elif consumerid:
            errata = self.consumer_api.errata(consumerid, self.opts.type)
            if errata:
                print_header(_("Applicable Errata for consumer [%s]" % consumerid))
        if not errata:
            system_exit(os.EX_OK, _("No errata available to list"))
        print(" , ".join(errata))


class Info(ErrataAction):

    description = _('see details on a specific errata')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help=_("errata id (required)"))

    def run(self):
        id = self.get_required_option('id')
        errata = self.errata_api.erratum(id)
        if not errata:
            system_exit(os.EX_DATAERR, _("Errata Id %s not found." % id))
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


class Install(ErrataAction):

    description = _('install errata on a consumer')

    def setup_parser(self):
        self.parser.add_option("-e", "--erratum", action="append", dest="id",
                               help=_("id of the erratum to be installed; to specify multiple erratum use multiple uses of this flag"))
        id_group = OptionGroup(self.parser, _('Consumer or Consumer Group id (one is required)'))
        id_group.add_option("--consumerid", dest="consumerid",
                            help=_("consumer id"))
        id_group.add_option("--consumergroupid", dest="consumergroupid",
                            help=_("consumer group id"))
        self.parser.add_option_group(id_group)
        self.parser.add_option("-y", "--assumeyes", action="store_true", dest="assumeyes",
                            help=_("assume yes; assume that install performs all the suggested actions such as reboot on successful install"))

    def run(self):
        errataids = self.opts.id

        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            self.parser.error(_("A consumerid or a consumergroupid is required to perform an install"))

        if not errataids:
            system_exit(os.EX_USAGE, _("Specify an erratum id to perform install"))

        assumeyes = False
        if self.opts.assumeyes:
            assumeyes = True
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
                        assumeyes = True
                    elif ask_reboot.strip().lower() == 'n':
                        assumeyes = False
                    elif ask_reboot.strip().lower() == 'q':
                        system_exit(os.EX_OK, _("Errata install aborted upon user request."))
                    else:
                        continue
        try:
            if self.opts.consumerid:
                task = self.consumer_api.installerrata(consumerid, errataids, assumeyes=assumeyes)
            elif self.opts.consumergroupid:
                task = self.consumer_group_api.installerrata(consumergroupid, errataids, assumeyes=assumeyes)
        except Exception,e:
            system_exit(os.EX_DATAERR, _("Error:%s" % e[1] ))
        if not task:
            system_exit(os.EX_DATAERR,
                _("The requested errataids %s are not applicable for your system" % errataids))
        print _('Created task id: %s') % task['id']
        state = None
        spath = task['status_path']
        while state not in ['finished', 'error']:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(2)
            status = self.consumer_api.task_status(spath)
            state = status['state']
        if state == 'finished' and consumerid:
            (installed, reboot_status) = status['result']
            if not reboot_status:
                print _('\nSuccessfully installed [%s] on [%s]') % \
                      (installed, (consumerid or (consumergroupid)))
            elif reboot_status.has_key('reboot_performed') and reboot_status['reboot_performed']:
                print _('\nSuccessfully installed [%s] and reboot scheduled on [%s]' % (installed, (consumerid or (consumergroupid))))
            elif reboot_status.has_key('reboot_performed') and not reboot_status['reboot_performed']:
                print _('\nSuccessfully installed [%s]; This update requires a reboot, please reboot [%s] at your earliest convenience' % \
                        (installed, (consumerid or (consumergroupid))))

        elif state == 'finished' and consumergroupid:
            print _("\nSuccessfully performed consumergroup install with following consumer result list %s" % status['result'])
        else:
            print("\nErrata install failed")
            
class Create(ErrataAction):
    
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
            system_exit(os.EX_DATAERR, _("Erratum with id [%s] already exists on server." % errata_id))
        # process package list
        references = []
        if self.opts.refcsv:
            if not os.path.exists(self.opts.refcsv):
                system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
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
                system_exit(os.EX_DATAERR, _("CSV file [%s] not found"))
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
            system_exit(os.EX_DATAERR, _("Error: Invalid pushcount [%s]; should be an integer " % self.opts.pushcount))
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
        
class update(ErrataAction):
    #TODO: put this in place once update semantics is done
    pass

class Delete(ErrataAction):
    
    description = _('delete a custom errata')

    def setup_parser(self):
        self.parser.add_option("--id", dest="id",
                               help=_("errata id to delete"))
        
    def run(self):
        if not self.opts.id:
            system_exit(os.EX_USAGE, _("Errata Id is required; see --help"))
        found = self.errata_api.erratum(self.opts.id)
        if not found:
            system_exit(os.EX_DATAERR, _("Erratum with id [%s] not found." % self.opts.id))
        
        self.errata_api.delete(self.opts.id)
        print _("Successfully deleted Erratum with id [%s]" % self.opts.id)

# errata command --------------------------------------------------------------

class Errata(Command):

    description = _('errata specific actions to pulp server')
