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

DISTRIBUTOR_ID = 'pulp_distributor'


class BindCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        super(BindCommand, self).__init__(name, description, self.bind)
        self.create_option('--pulp-id', _('identifies the downstream pulp server'), required=True)
        self.create_option('--repo-id', _('repository to bind'), required=True)
        self.context = context

    def bind(self, **kwargs):
        pulp_id = kwargs['pulp-id']
        repo_id = kwargs['repo-id']
        self.associate_distributor(repo_id)
        try:
            self.context.server.bind.bind(pulp_id, repo_id, DISTRIBUTOR_ID)
            m = '[%(c)s] successfully bound to repository [%(r)s]'
            self.context.prompt.render_success_message(_(m) % {'c' : pulp_id, 'r' : repo_id})
        except NotFoundException:
            m = '[%(c)s] does not exist on the server'
            self.context.prompt.write(_(m) % {'c' : pulp_id}, tag='not-found')
            
    def associate_distributor(self, repo_id):
        """
        Automatically associate the pulp_distributor.
        TODO: Fix this after prototype.
        """
        try:
            config = {}
            binding = self.context.server.repo_distributor
            binding.create(
                repo_id,
                DISTRIBUTOR_ID,
                config, 
                False,
                DISTRIBUTOR_ID)
        except Exception:
            # should log this
            pass


class UnbindCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        super(UnbindCommand, self).__init__(name, description, self.bind)
        self.create_option('--pulp-id', _('identifies the consumer'), required=True)
        self.create_option('--repo-id', _('repository to bind'), required=True)
        self.context = context

    def bind(self, **kwargs):
        pulp_id = kwargs['pulp-id']
        repo_id = kwargs['repo-id']
        try:
            self.context.server.bind.unbind(pulp_id, repo_id, DISTRIBUTOR_ID)
            m = '[%(c)s] successfully unbound from repository [%(r)s]'
            self.context.prompt.render_success_message(_(m) % {'c' : pulp_id, 'r' : repo_id})
        except NotFoundException:
            m = '[%(c)s] does not exist on the server'
            self.context.prompt.write(_(m) % {'c' : pulp_id}, tag='not-found')
