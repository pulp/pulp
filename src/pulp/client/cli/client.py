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

import os
import sys
from gettext import gettext as _

from pulp.client.cli.base import PulpBase


# TODO make this configurable
_consumer_id_file = '/etc/pulp/consumer'


class PulpClient(PulpBase):

    _commands = ('consumer', 'repo', 'errata')
    _actions = {
        'consumer': ('create', 'delete', 'update', 'bind', 'unbind', 'history'),
        'repo': ('list',),
        'errata': ('list',),
    }
    _actions_states = {}

    def __init__(self):
        super(PulpClient, self).__init__()

    def get_consumer_id(self):
        if not os.path.exists(_consumer_id_file):
            print >> sys.stderr, _("this client is currently not registered; please register to continue")
            return None
        try:
            id = file(_consumer_id_file).read()
        except Exception, e:
            self.parser.error(_("cannot read consumer:") + str(e))
        return id

    def find_command(self, command):
        # get the registered consumer id and push it down to the commands
        id = self.get_consumer_id()
        if id is not None:
            for action in ('consumer', 'errata'):
                self._actions_states[action] = {'id': id}
        return super(PulpClient, self).find_command(command)
