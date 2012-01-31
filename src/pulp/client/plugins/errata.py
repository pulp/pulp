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
from gettext import gettext as _
from optparse import OptionGroup

from pulp.client.api.consumergroup import ConsumerGroupAPI
from pulp.client.api.consumer import ConsumerAPI
from pulp.client.api.errata import ErrataAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.lib.utils import print_header
from pulp.client.lib import utils
from pulp.client.lib.logutil import getLogger
from pulp.client.pluginlib.command import Action, Command

log = getLogger(__name__)

# errata action base class ----------------------------------------------------

class ErrataAction(Action):

    def __init__(self, cfg):
        super(ErrataAction, self).__init__(cfg)
        self.consumer_api = ConsumerAPI()
        self.consumer_group_api = ConsumerGroupAPI()
        self.errata_api = ErrataAPI()
        self.repository_api = RepositoryAPI()

# errata actions --------------------------------------------------------------

class List(ErrataAction):

    name = "list"
    description = _('list applicable errata')

    def __init__(self, cfg):
        super(List, self).__init__(cfg)
        self.id_field_size = 20
        self.type_field_size = 15


    def setup_parser(self):
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repository id"))
        self.parser.add_option("--type", dest="type", default=None,
                               help=_("type of errata to lookup; eg. security, bugfix etc."))


    def run(self, consumerid):
        repoid = self.opts.repoid

        # List all errata if no consumerid or repoid is specified
        if not (consumerid or repoid):
            errata = self.errata_api.errata(self.opts.type)
            if errata:
                print_header(_("Errata Information"))

        if repoid:
            errata = self.repository_api.errata(repoid, self.opts.type)
            if errata:
                print_header(_("Available Errata in Repo [%s]" % repoid))
        elif consumerid:
            errata = self.consumer_api.errata(consumerid, self.opts.type)
            if errata:
                print_header(_("Applicable Errata for consumer [%s]" % consumerid))
        
        if not errata:
            utils.system_exit(os.EX_OK, _("No errata available to list"))

        print _("\n%s\t%s\t%s\n" % (self.form_item_string("Id", self.id_field_size),
                self.form_item_string("Type", self.type_field_size),
                "Title"))
        for erratum in errata:
            print "%s\t%s\t%s" % \
                (self.form_item_string(erratum["id"], self.id_field_size),
                 self.form_item_string(erratum["type"], self.type_field_size),
                 erratum["title"])


    def form_item_string(self, msg, field_size):
        return string.ljust(msg, field_size)

# errata command --------------------------------------------------------------

class Errata(Command):

    name = "errata"
    description = _('errata specific actions to pulp server')
