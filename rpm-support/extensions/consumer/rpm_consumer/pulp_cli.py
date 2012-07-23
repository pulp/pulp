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
from pulp.client.consumer_utils import load_consumer_id
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption

YUM_DISTRIBUTOR_TYPE_ID = 'yum_distributor'

# -- framework hook -----------------------------------------------------------

def initialize(context):

    # Replace the existing bind command with one scoped specifically to the
    # yum distributor
    context.cli.remove_command('bind')
    context.cli.remove_command('unbind')

    d = 'binds this consumer to a Pulp repository'
    context.cli.add_command(BindCommand(context, 'bind', _(d)))

    d = 'unbinds this consumer from a Pulp repository'
    context.cli.add_command(UnbindCommand(context, 'unbind', _(d)))

class BindCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.bind)
        self.context = context
        self.prompt = context.prompt

        self.add_option(PulpCliOption('--repo-id', 'repository id', required=True))

    def bind(self, **kwargs):
        consumer_id = load_consumer_id(self.context)

        if not consumer_id:
            m = 'This consumer is not registered to the Pulp server'
            self.prompt.render_failure_message(_(m))
            return

        repo_id = kwargs['repo-id']

        try:
            self.context.server.bind.bind(consumer_id, repo_id, YUM_DISTRIBUTOR_TYPE_ID)
            m = 'Consumer [%(c)s] successfully bound to repository [%(r)s]'
            self.prompt.render_success_message(_(m) % {'c' : consumer_id, 'r' : repo_id})
        except NotFoundException:
            m = 'Consumer [%(c)s] does not exist on the server'
            self.prompt.render_failure_message(_(m) % {'c' : consumer_id})

class UnbindCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.unbind)
        self.context = context
        self.prompt = context.prompt

        self.add_option(PulpCliOption('--repo-id', 'repository id', required=True))

    def unbind(self, **kwargs):
        consumer_id = load_consumer_id(self.context)
        if not consumer_id:
            m = 'This consumer is not registered to the Pulp server'
            self.prompt.render_failure_message(_(m))
            return

        repo_id = kwargs['repo-id']

        try:
            self.context.server.bind.unbind(consumer_id, repo_id, YUM_DISTRIBUTOR_TYPE_ID)
            m = 'Consumer [%(c)s] successfully unbound from repository [%(r)s]'
            self.prompt.render_success_message(_(m) % {'c' : consumer_id, 'r' : repo_id})
        except NotFoundException:
            m = 'Consumer [%(c)s] does not exist on the server'
            self.prompt.render_failure_message(_(m) % {'c' : consumer_id}, tag='not-found')
