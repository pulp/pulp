# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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

import sys
from gettext import gettext as _

from pulp.client import credentials
from pulp.client.cli.base import PulpBase


class PulpClient(PulpBase):

    _commands = ('consumer', 'repo', 'errata')
    _actions = {
        'consumer': ('create', 'delete', 'update', 'bind', 'unbind', 'history'),
        'repo': ('list',),
        'errata': ('list',),
    }

    def __init__(self):
        super(PulpClient, self).__init__()
        if not credentials.set_local_consumer_id():
            print >> sys.stderr, \
                    _("warning: this client is currently not registered; please register to continue")
