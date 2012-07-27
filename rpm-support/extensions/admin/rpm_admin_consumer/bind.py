# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.bindings.exceptions import NotFoundException
from pulp.client.extensions.extensions import PulpCliCommand

YUM_DISTRIBUTOR_ID = 'yum_distributor'

class BindCommand(PulpCliCommand):
    def __init__(self, context, name, description):
        super(BindCommand, self).__init__(name, description, self.bind)

        self.create_option('--consumer-id', _('identifies the consumer'), required=True)
        self.create_option('--repo-id', _('repository to bind'), required=True)

        self.context = context

    def bind(self, **kwargs):
        id = kwargs['consumer-id']
        repo_id = kwargs['repo-id']

        try:
            self.context.server.bind.bind(id, repo_id, YUM_DISTRIBUTOR_ID)
            m = 'Consumer [%(c)s] successfully bound to repository [%(r)s]'
            self.context.prompt.render_success_message(_(m) % {'c' : id, 'r' : repo_id})
        except NotFoundException:
            m = 'Consumer [%(c)s] does not exist on the server'
            self.context.prompt.write(_(m) % {'c' : id}, tag='not-found')

class UnbindCommand(PulpCliCommand):
    def __init__(self, context, name, description):
        super(UnbindCommand, self).__init__(name, description, self.bind)

        self.create_option('--consumer-id', _('identifies the consumer'), required=True)
        self.create_option('--repo-id', _('repository to bind'), required=True)

        self.context = context

    def bind(self, **kwargs):
        id = kwargs['consumer-id']
        repo_id = kwargs['repo-id']

        try:
            self.context.server.bind.unbind(id, repo_id, YUM_DISTRIBUTOR_ID)
            m = 'Consumer [%(c)s] successfully unbound from repository [%(r)s]'
            self.context.prompt.render_success_message(_(m) % {'c' : id, 'r' : repo_id})
        except NotFoundException:
            m = 'Consumer [%(c)s] does not exist on the server'
            self.context.prompt.write(_(m) % {'c' : id}, tag='not-found')
