#!/usr/bin/python
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
from pulp.client.api.distribution import DistributionAPI
from pulp.client.api.repository import RepositoryAPI
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import system_exit, print_header
from pulp.client.config import Config

_cfg = Config()
# distribution action base class ----------------------------------------------------

class DistributionAction(Action):

    def __init__(self):
        super(DistributionAction, self).__init__()
        self.distribution_api = DistributionAPI()
        self.repository_api = RepositoryAPI()

# errata actions --------------------------------------------------------------

class List(DistributionAction):

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
            ksurl = _cfg._sections['cds'].__getitem__('ksurl') + '/' + distro['relativepath']
            print constants.DISTRO_LIST % (distro['id'], distro['description'], ksurl)


class Info(DistributionAction):

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
        ksurl = _cfg._sections['cds'].__getitem__('ksurl') + '/' + distribution['relativepath']
        print constants.DISTRO_INFO % (distribution['id'], distribution['description'], ksurl,
                                       '\n \t\t\t'.join(distribution['files'][:]), distribution['relativepath'])

class Distribution(Command):

    description = _('distribution specific actions to pulp server')
