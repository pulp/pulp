#!/usr/bin/python
#
# Pulp Registration and subscription module
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
from optparse import OptionGroup

from pulp.client.connection import (
    setup_connection, SearchConnection, RepoConnection,
    PackageConnection)
from pulp.client.core.base import Action, Command
from pulp.client.core.utils import print_header, system_exit

# package action base class ---------------------------------------------------

class SearchAction(Action):

    def setup_connections(self):
        self.sconn = setup_connection(SearchConnection)
        self.rconn = setup_connection(RepoConnection)
        self.pconn = setup_connection(PackageConnection)

# search actions -------------------------------------------------------------

class Packages(SearchAction):

    description = _('search for packages')

    def setup_parser(self):
        self.parser.add_option("-a", "--arch", dest="arch", default=None,
                               help=_("package arch regex to search for"))
        self.parser.add_option("-e", "--epoch", dest="epoch", default=None,
                               help=_("package epoch regex to search for"))
        self.parser.add_option("-f", "--filename", dest="filename", default=None,
                               help=_("package filename regex to search for"))
        self.parser.add_option("-n", "--name", dest="name", default=None,
                               help=_("package name regex to search for"))
        self.parser.add_option("-r", "--release", dest="release", default=None,
                               help=_("package release regex to search for"))
        self.parser.add_option("-v", "--version", dest="version", default=None,
                               help=_("package version regex to search for"))

    def run(self):
        arch = self.opts.arch
        epoch = self.opts.epoch
        filename = self.opts.filename
        name = self.opts.name
        release = self.opts.release
        version = self.opts.version
        pkgs = self.sconn.packages(name=name, epoch=epoch, version=version,
                release=release, arch=arch, filename=filename)
        if not pkgs:
           system_exit(os.EX_DATAERR, _("No packages found."))

        print_header(_("Package Information"))
        for pkg in pkgs:
            print """%s \t%s:%s-%s.%s\t%s""" % (pkg["name"], pkg["epoch"], pkg["version"], pkg["release"], pkg["arch"], pkg["filename"])



# search command -------------------------------------------------------------

class Search(Command):

    description = _('search actions to pulp server')
