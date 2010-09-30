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

import sys
import time
from gettext import gettext as _
from optparse import SUPPRESS_HELP

import pulp.client.constants as constants
from pulp.client.config import Config
from pulp.client.connection import (
    ErrataConnection, RepoConnection, ConsumerConnection,
    ConsumerGroupConnection)
from pulp.client.core.base import Action, BaseCore, system_exit
from pulp.client.logutil import getLogger


CFG = Config()
log = getLogger(__name__)

# errata action base class ----------------------------------------------------

class ErrataAction(Action):

    def connections(self):
        conns = {
            'econn': ErrataConnection,
            'rconn': RepoConnection,
            'cconn': ConsumerConnection,
            'cgconn': ConsumerGroupConnection,
        }
        return conns

# errata actions --------------------------------------------------------------

class List(ErrataAction):

    name = 'list'
    plug = 'list applicable errata'

    def setup_parser(self):
        default = None
        help = 'consumer id'
        if hasattr(self, 'id'):
            default = self.id
            help = SUPPRESS_HELP
        self.parser.add_option("--consumerid", dest="consumerid",
                               default=default, help=help)
        self.parser.add_option("--repoid", dest="repoid",
                               help="repository id")
        self.parser.add_option("--type", dest="type", action="append",
                               help="type of errata to lookup; supported types: security, bugfix, enhancement")

    def run(self):
        consumerid = self.opts.consumerid
        repoid = self.opts.repoid
        if not (consumerid or repoid):
            system_exit(0, _("a consumer or a repo is required to lookup errata"))
        if repoid:
            errata = self.rconn.errata(repoid, self.options.type)
        elif consumerid:
            errata = self.cconn.errata(consumerid, self.options.type)
        if not errata:
            print _("no errata available to list")
            system_exit(0)
        print errata


class Info(ErrataAction):

    name = 'info'
    plug = 'see details on a specific errata'

    def setup_parser(self):
        self.parser.add_option("--id", dest="id", help="errata id")

    def run(self):
        id = self.get_required_option('id')
        errata = self.econn.erratum(id)
        effected_pkgs = [str(pinfo['filename'])
                         for pkg in errata['pkglist']
                         for pinfo in pkg['packages']]
        print constants.ERRATA_INFO % (errata['id'], errata['title'],
                                       errata['description'], errata['type'],
                                       errata['issued'], errata['updated'],
                                       errata['version'], errata['release'],
                                       errata['status'], effected_pkgs,
                                       errata['references'])


class Install(ErrataAction):

    name = 'install'
    plug = 'install errata on a consumer'

    def setup_parser(self):
        self.parser.add_option("--consumerid", dest="consumerid",
                               help="consumer id")
        self.parser.add_option("--consumergroupid", dest="consumergroupid",
                               help="consumer group id")

    def run(self):
        data = self.args
        consumerid = self.opts.consumerid
        consumergroupid = self.opts.consumergroupid
        if not (consumerid or consumergroupid):
            system_exit(0, _("a consumerid or a consumergroupid is required to perform an install"))
        errataids = data[2:]
        if not errataids:
            system_exit(0, _("specify an errata id to install"))
        if self.options.consumerid:
            task = self.cconn.installerrata(consumerid, errataids)
        elif self.options.consumergroupid:
            task = self.cgconn.installerrata(consumergroupid, errataids)
        print _('created task id: %s') % task['id']
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
                  (status['result'], (consumerid or (consumergroupid)))
        else:
            print("\nerrata install failed")

# errata command --------------------------------------------------------------

class Errata(BaseCore):

    name = 'errata'
    _default_actions = ('list', 'info', 'install')

    def __init__(self, actions=_default_actions, action_state={}):
        super(Errata, self).__init__(actions, action_state)
        self.list = List()
        self.info = Info()
        self.install = Install()

    def short_description(self):
        return _('errata specific actions to pulp server')


command_class = errata = Errata
