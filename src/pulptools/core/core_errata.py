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
import base64

import pulptools.utils as utils
import pulptools.constants as constants
from pulptools.core.basecore import BaseCore, systemExit
from pulptools.connection import ErrataConnection, RestlibException,\
    RepoConnection, ConsumerConnection
from pulptools.logutil import getLogger
from pulptools.config import Config
CFG = Config()

import gettext
_ = gettext.gettext
log = getLogger(__name__)

class errata(BaseCore):
    def __init__(self):
        usage = "errata [OPTIONS]"
        shortdesc = "errata specific actions to pulp server."
        desc = ""
        self.name = "errata"
        self.actions = {"create" : "Create a custom errata", 
                        "update" : "Update an existing errata", 
                        "list"   : "List applicable errata", 
                        "delete" : "Delete an errata", 
                        "info"   : "See details on a specific errata",
                        "install" : "Install Errata on a consumer",}
        BaseCore.__init__(self, "errata", usage, shortdesc, desc)

    def load_server(self):
        self.econn = ErrataConnection(host=CFG.server.host or "localhost", 
                                    port=CFG.server.port or 8811,
                                    username=self.username, 
                                    password=self.password)
        self.rconn = RepoConnection(host=CFG.server.host or "localhost", 
                                    port=CFG.server.port or 8811,
                                    username=self.username, 
                                    password=self.password)
        self.cconn = ConsumerConnection(host=CFG.server.host or "localhost", 
                                    port=CFG.server.port or 8811,
                                    username=self.username, 
                                    password=self.password)
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
            self.parser.add_option("--consumerid", dest="consumerid",
                           help="Consumer Id")
            self.parser.add_option("--repoid", dest="repoid",
                            help="Repository Id")
            self.parser.add_option("--type", dest="type", action="append",
                            help="Type of Errata to lookup \
                                    supported types: security, bugfix, enhancement")

        if self.action == "info":
            usage = "errata info [OPTIONS]"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--id", dest="id",
                           help="Errata Id")

        if self.action == "install":
            usage = "errata install [OPTIONS] <errata>"
            self.setup_option_parser(usage, "", True)
            self.parser.add_option("--consumerid", dest="id",
                           help="Consumer Id")

    def _do_core(self):
        if self.action == "create":
            self._create()
        if self.action == "delete":
            self._delete()
        if self.action == "list":
            self._list()
        if self.action == "info":
            self._info()

    def _create(self):
        pass

    def _delete(self):
        pass

    def _list(self):
        if not (self.options.consumerid or self.options.repoid):
            print _("A consumer or a repo is required to lookup errata")
            sys.exit(0)
            
        try:
            if self.options.repoid:
                errata = self.rconn.errata(self.options.repoid, self.options.type)
            elif self.options.consumerid:
                errata = self.cconn.errata(self.options.consumerid, self.options.type)
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

class FileError(Exception):
    pass

class SyncError(Exception):
    pass
