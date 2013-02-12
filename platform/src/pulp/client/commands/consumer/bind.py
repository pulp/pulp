# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

from gettext import gettext as _

from pulp.bindings.exceptions import NotFoundException
from pulp.client.commands.options import DESC_ID, OPTION_CONSUMER_ID, OPTION_REPO_ID
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliFlag, PulpCliOption

# consumer bindings management commands ----------------------------------------

class ConsumerBindCommand(PulpCliCommand):
    """
    Bind a consumer to a repository.
    """

    def __init__(self, context):
        description = _('binds a consumer to a repository')
        super(self.__class__, self).__init__('bind', description, self.bind)

        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_DISTRIBUTOR_ID)

        self.context = context

    def bind(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        distributor_id = kwargs[OPTION_DISTRIBUTOR_ID.keyword]

        try:
            response = self.context.server.bind.bind(consumer_id, repo_id, distributor_id)

        except NotFoundException, e:
            resources = e.extra_data['resources']
            missing = []
            msg = _('%(t)s [%(i)s] does not exists on the server')
            if 'consumer' in resources:
                missing.append((_('Consumer'), consumer_id))
            if 'repository' in resources:
                missing.append((_('Repository'), repo_id))
            if 'distributor' in resources:
                missing.append((_('Distributor'), distributor_id))
            for option_title, option_id in missing:
                self.context.prompt.write(msg % {'t': option_title, 'i': option_id}, tag='not-found')

        else:
            msg = _('Bind tasks successfully created:')
            self.context.prompt.render_success_message(msg)
            task_dicts = [dict(('task_id', str(t.task_id))) for t in response.response_body]
            self.context.prompt.render_document_list(task_dicts)


class ConsumerUnbindCommand(PulpCliCommand):
    """
    Remove a consumer-repository binding.
    """

    def __init__(self, context):
        description = _('removes the binding between a consumer and a repository')
        super(self.__class__, self).__init__('unbind', description, self.unbind)

        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_REPO_ID)
        self.add_option(OPTION_DISTRIBUTOR_ID)

        self.add_flag(FLAG_FORCE)

        self.context = context

    def unbind(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        distributor_id = kwargs[OPTION_DISTRIBUTOR_ID.keyword]
        force = kwargs[FLAG_FORCE.keyword]

        try:
            response = self.context.server.bind.unbind(consumer_id, repo_id, distributor_id, force)

        except NotFoundException:
            msg = _('Binding [consumer: %(c)s, repository: %(r)s] does not exist on the server')
            self.context.prompt.write(msg % {'c': consumer_id, 'r': repo_id}, tag='not-found')

        else:
            msg = _('Unbind tasks successfully created:')
            self.context.prompt.render_success_message(msg)
            task_dicts = [dict(('task_id', t.task_id)) for t in response.response_body]
            self.context.prompt.render_document_list(task_dicts)

# options and flags ------------------------------------------------------------

OPTION_DISTRIBUTOR_ID = PulpCliOption('--distributor-id', DESC_ID, required=True)

FLAG_FORCE = PulpCliFlag('--force',
                         _('delete the binding immediately and discontinue tracking consumer actions'))

