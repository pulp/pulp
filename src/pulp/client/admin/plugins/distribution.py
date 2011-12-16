#
# Pulp Distribution management module
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
from gettext import gettext as _

from pulp.client import constants
from pulp.client.admin.plugin import AdminPlugin
from pulp.client.api.distribution import DistributionAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.pluginlib.command import Action, Command
from pulp.client.lib.utils import print_header, system_exit
from pulp.client.admin.config import AdminConfig

# distribution action base class ----------------------------------------------------

class DistributionAction(Action):

    def __init__(self, cfg):
        super(DistributionAction, self).__init__(cfg)
        self.distribution_api = DistributionAPI()
        self.repository_api = RepositoryAPI()

# distribution actions --------------------------------------------------------------

class List(DistributionAction):

    name = "list"
    description = _('list available distributions')

    def setup_parser(self):
        help = _('repo id (optional)')
        self.parser.add_option("--repoid", dest="repoid",
                               help=_("repository id"))

    def run(self):
        repoid = self.opts.repoid
        if repoid:
            distribution = self.repository_api.distribution(repoid)
        else:
            distribution = self.distribution_api.distributions()
        if not distribution:
            system_exit(os.EX_OK, _("No distributions found to list"))
        print_header(_('List of Available Distributions'))
        for distro in distribution:
            print constants.DISTRO_LIST % (distro['id'], distro['description'], distro['family'],
                                           distro['variant'], distro['version'], distro['arch'], '\n \t\t\t'.join(distro['url'][:]), distro['timestamp'])


class Info(DistributionAction):

    name = "info"
    description = _('view information about a particular distribution')

    def setup_parser(self):
        help = _('distribution id (required)')
        self.parser.add_option("--id", dest="distid",
                               help=_("distribution id"))

    def run(self):
        distid = self.opts.distid
        if not distid:
            system_exit(os.EX_USAGE, _("Specify a distribution id"))
        distribution = self.distribution_api.distribution(distid)
        if not distribution:
            system_exit(os.EX_OK, _("No distribution found with id [%s]" % distid))
        print_header(_('Distribution Info for %s' % distid))
        print constants.DISTRO_INFO % (distribution['id'], distribution['description'], '\n \t\t\t'.join(distribution['url'][:]),
                                       distribution['family'], distribution['variant'], distribution['version'], distribution['arch'],
                                       '\n \t\t\t'.join(distribution['files'][:]), distribution['timestamp'])

# distribution command --------------------------------------------------------------

class Distribution(Command):

    name = "distribution"
    description = _('distribution specific actions to pulp server')

    actions = [ List,
                Info ]

# distribution plugin --------------------------------------------------------------

class DistributionPlugin(AdminPlugin):

    name = "distribution"
    commands = [ Distribution ]
