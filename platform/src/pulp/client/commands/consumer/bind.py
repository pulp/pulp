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
from pulp.client.extensions.extensions import PulpCliCommand


CONSUMER_BIND_DESCRIPTION = _('binds a consumer to a repository')
CONSUMER_UNBIND_DESCRIPTION = _('removes the binding between a consumer and a repository')

DISTRIBUTOR_OPTION_NAME = 'distributor'

FORCE_FLAG_NAME = 'force'
FORCE_FLAG_DESCRIPTION = _('delete the binding immediately and discontinue tracking consumer actions')

NOT_FOUND_TAG = 'not-found'


class ConsumerBindCommand(PulpCliCommand):
    """
    Bind a consumer to a repository.
    """

    def __init__(self, context, name='bind', description=CONSUMER_BIND_DESCRIPTION):
        super(self.__class__, self).__init__(name, description, self.bind)
        self.context = context
        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_REPO_ID)
        self.create_option('--' + DISTRIBUTOR_OPTION_NAME, DESC_ID, required=True)

    def bind(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        distributor_id = kwargs[DISTRIBUTOR_OPTION_NAME]

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
                self.context.prompt.write(msg % {'t': option_title, 'i': option_id}, tag=NOT_FOUND_TAG)

        else:
            msg = _('Bind tasks successfully created:')
            self.context.prompt.render_success_message(msg)
            task_dicts = [dict(('task_id', str(t.task_id))) for t in response.response_body]
            self.context.prompt.render_document_list(task_dicts)


class ConsumerUnbindCommand(PulpCliCommand):
    """
    Remove a consumer-repository binding.
    """

    def __init__(self, context, name='unbind', description=CONSUMER_UNBIND_DESCRIPTION):
        super(self.__class__, self).__init__(name, description, self.unbind)
        self.context = context
        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(OPTION_REPO_ID)
        self.create_option('--' + DISTRIBUTOR_OPTION_NAME, DESC_ID, required=True)
        self.create_flag('--' + FORCE_FLAG_NAME, FORCE_FLAG_DESCRIPTION)

    def unbind(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        distributor_id = kwargs[DISTRIBUTOR_OPTION_NAME]
        force = kwargs[FORCE_FLAG_NAME]

        try:
            response = self.context.server.bind.unbind(consumer_id, repo_id, distributor_id, force)

        except NotFoundException:
            msg = _('Binding [consumer: %(c)s, repository: %(r)s] does not exist on the server')
            self.context.prompt.write(msg % {'c': consumer_id, 'r': repo_id}, tag=NOT_FOUND_TAG)

        else:
            msg = _('Unbind tasks successfully created:')
            self.context.prompt.render_success_message(msg)
            task_dicts = [dict(('task_id', t.task_id)) for t in response.response_body]
            self.context.prompt.render_document_list(task_dicts)


