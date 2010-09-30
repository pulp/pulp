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
from gettext import gettext as _

from pulp.client.cli.base import PulpBase
from pulp.client.core.base import system_exit


# TODO make this configurable
_consumer_id_file = '/etc/pulp/consumer'


def get_consumer():
    if not os.path.exists(_consumer_id_file):
        system_exit(0, _("error: this client is currently not registered; please register to continue"))
    try:
        consumerid = file(_consumer_id_file).read()
    except Exception, e:
        system_exit(-1, ("error reading consumer:" + e))
    return consumerid


class PulpClient(PulpBase):

    _id = get_consumer()
    _commands = ('consumer', 'repo', 'errata')
    _actions = {
        'consumer': ('create', 'delete', 'update', 'bind', 'unbind', 'history'),
        'repo': ('list',),
        'errata': ('list',),
    }
    _actions_states = {
        'consumer': {'id': _id},
        'errata': {'id': _id}
    }

    def __init__(self):
        super(PulpClient, self).__init__()
