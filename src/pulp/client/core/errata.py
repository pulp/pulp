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

import gettext
import sys

import pulp.client.constants as constants
from pulp.client.config import Config
from pulp.client.connection import (
    ErrataConnection, RestlibException, RepoConnection, ConsumerConnection,
    ConsumerGroupConnection)
from pulp.client.core.base import BaseCore, systemExit
from pulp.client.logutil import getLogger


CFG = Config()
log = getLogger(__name__)

_ = gettext.gettext


class errata(BaseCore):
    def __init__(self, is_admin=True, actions=None):
        usage = "errata [OPTIONS]"
        shortdesc = "errata specific actions to pulp server."
        desc = ""
        self.name = "errata"
        self.actions = actions or {"create" : "Create a custom errata",
                                   "update" : "Update an existing errata",
                                   "list"   : "List applicable errata",
                                   "delete" : "Delete an errata",
                                   "info"   : "See details on a specific errata",
                                   "install" : "Install Errata on a consumer", }
        self.is_admin = is_admin
        BaseCore.__init__(self, "errata", usage, shortdesc, desc)

    def load_server(self):
        self.econn = ErrataConnection(host=CFG.server.host or "localhost",
                                    port=CFG.server.port or 443,
                                    username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)
        self.rconn = RepoConnection(host=CFG.server.host or "localhost",
                                    port=CFG.server.port or 443,
                                    username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost",
                                    port=CFG.server.port or 443,
                                    username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)
        self.cgconn = ConsumerGroupConnection(host=CFG.server.host or "localhost",
                                    port=CFG.server.port or 443,
                                    username=self.username,
                                    password=self.password,
                                    cert_file=self.cert_filename,
                                    key_file=self.key_filename)
    def generate_options(self):
        self.action = self._get_action()
        if self.action == "create":
            usage = "errata create [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            pass
        if self.action == "update":
            usage = "errata update [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            pass

        if self.action == "delete":
            usage = "errata delete [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="errata Id")

        if self.action == "list":
            usage = "errata list [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            if self.is_admin:
                self.parser.add_option("--consumerid", dest="consumerid",
                                       help="consumer id")
            self.parser.add_option("--repoid", dest="repoid",
                            help="repository id")
            self.parser.add_option("--type", dest="type", action="append",
                            help="type of errata to lookup; supported types: security, bugfix, enhancement")

        if self.action == "info":
            usage = "errata info [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="errata id")

        if self.action == "install":
            usage = "errata install [OPTIONS] <errata>"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="consumer id")
            self.parser.add_option("--consumergroupid", dest="consumergroupid",
                           help="consumer group id")

    def _do_core(self):
        if self.action == "create":
            self._create()
        if self.action == "delete":
            self._delete()
        if self.action == "list":
            self._list()
        if self.action == "info":
            self._info()
        if self.action == "install":
            self._install()

    def _create(self):
        print _("Not Implemented")
        sys.exit(0)

    def _delete(self):
        print _("Not Implemented")
        sys.exit(0)

    def _list(self):
        if not (self.getConsumer() or self.options.repoid):
            print _("A consumer or a repo is required to lookup errata")
            sys.exit(0)

        try:
            if self.options.repoid:
                errata = self.rconn.errata(self.options.repoid, self.options.type)
            elif self.getConsumer():
                errata = self.cconn.errata(self.getConsumer(), self.options.type)
            if not len(errata):
                print _("No errata available to list")
                sys.exit(0)
            print errata

        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _info(self):
        if not self.options.id:
            print _("An Errata id is required for lookup")
            sys.exit(0)
        try:
            errata = self.econn.erratum(self.options.id)
            effected_pkgs = [str(pinfo['filename']) for pkg in errata['pkglist'] for pinfo in pkg['packages']]
            print constants.ERRATA_INFO % (errata['id'], errata['title'], errata['description'],
                                           errata['type'], errata['issued'], errata['updated'],
                                           errata['version'], errata['release'], errata['status'],
                                           effected_pkgs, errata['references'])
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def _install(self):
        (self.options, data) = self.parser.parse_args()
        if not (self.options.consumerid or self.options.consumergroupid):
            print _("A consumerid or a consumergroupid is required to perform an install")
            sys.exit(0)
        errataids = data[2:]
        if not len(errataids):
            print _("Specify an errata Id to install")
            sys.exit(0)

        try:
            if self.options.consumerid:
                task = self.cconn.installerrata(self.options.consumerid, errataids)
            elif self.options.consumergroupid:
                task = self.cgconn.installerrata(self.options.consumergroupid, errataids)
            print _('Created task ID: %s') % task['id']
            state = None
            spath = task['status_path']
            while state not in ['finished', 'error']:
                sys.stdout.write('.')
                sys.stdout.flush()
                time.sleep(2)
                status = self.cconn.task_status(spath)
                state = status['state']
            if state == 'finished':
                print _('\n[%s] installed on %s') % \
                      (status['result'],
                       (self.options.consumerid or
                       (self.options.consumergroupid)))
            else:
                print("\nErrata install failed")
        except RestlibException, re:
            log.error("Error: %s" % re)
            systemExit(re.code, re.msg)
        except Exception, e:
            log.error("Error: %s" % e)
            raise

    def getConsumer(self):
        if not self.options.consumerid:
            print _("consumer id required. Try --help")
            sys.exit(0)

        return self.options.consumerid

class FileError(Exception):
    pass

class SyncError(Exception):
    pass
