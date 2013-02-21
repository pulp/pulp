# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

from gettext import gettext as _

from pulp.client.validators import id_validator
from pulp.client.arg_utils import convert_boolean_arguments
from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption
from pulp.client.commands.consumer.query import ConsumerListCommand
from pulp.client.commands.consumer.bind import ConsumerBindCommand, ConsumerUnbindCommand
from pulp.client.commands.consumer.content import ConsumerContentUpdateCommand
from pulp.client.commands.options import DESC_ID, OPTION_REPO_ID, OPTION_CONSUMER_ID

from pulp_node.extensions.common import ensure_node_section
from pulp_node.constants import HTTP_DISTRIBUTOR, NODE_NOTE_KEY


# --- constants -----------------------------------------------------------------------------------

REPO_NAME = _('repo')
ACTIVATE_NAME = _('activate')
DEACTIVATE_NAME = _('deactivate')
ENABLE_NAME = _('enable')
DISABLE_NAME = _('disable')
SYNC_NAME = _('sync')
PUBLISH_NAME = _('publish')

LIST_DESCRIPTION = _('list child nodes')
ACTIVATE_DESCRIPTION = _('activate a consumer as a child node')
DEACTIVATE_DESCRIPTION = _('deactivate a child node')
BIND_DESCRIPTION = _('bind a child node to a repository')
UNBIND_DESCRIPTION = _('removes the binding between a child node and a repository')
UPDATE_DESCRIPTION = _('triggers an immediate synchronization of a child node')
ENABLE_DESCRIPTION = _('enables binding to a repository by a child node')
DISABLE_DESCRIPTION = _('disables binding to a repository by a child node')
REPO_DESCRIPTION = _('repository related commands')
AUTO_PUBLISH_DESCRIPTION = _('auto publish flag')
SYNC_DESCRIPTION = _('child node synchronization commands')
PUBLISH_DESCRIPTION = _('publish nodes content')

ACTIVATED_NOTE = {NODE_NOTE_KEY: True}
DEACTIVATED_NOTE = {NODE_NOTE_KEY: None}

NODE_ID_OPTION = PulpCliOption('--node-id', DESC_ID, required=True, validate_func=id_validator)
AUTO_PUBLISH_OPTION = PulpCliOption('--auto-publish', AUTO_PUBLISH_DESCRIPTION, required=False)



# --- extension loading ---------------------------------------------------------------------------

@priority()
def initialize(context):
    """
    :type context: pulp.client.extensions.core.ClientContext
    """
    node_section = ensure_node_section(context.cli)
    node_section.add_command(NodeListCommand(context))
    node_section.add_command(NodeActivateCommand(context))
    node_section.add_command(NodeDeactivateCommand(context))
    node_section.add_command(NodeBindCommand(context))
    node_section.add_command(NodeUnbindCommand(context))
    repo_section = node_section.create_subsection(REPO_NAME, REPO_DESCRIPTION)
    repo_section.add_command(NodeRepoEnableCommand(context))
    repo_section.add_command(NodeRepoDisableCommand(context))
    sync_section = node_section.create_subsection(SYNC_NAME, SYNC_DESCRIPTION)
    sync_section.add_command(NodeUpdateCommand(context))


# --- commands ------------------------------------------------------------------------------------


class NodeListCommand(ConsumerListCommand):

    def __init__(self, context):
        super(NodeListCommand, self).__init__(context, description=LIST_DESCRIPTION)

    def get_title(self):
        return _('Child Nodes')

    def get_consumer_list(self, kwargs):
        nodes = []
        for consumer in super(NodeListCommand, self).get_consumer_list(kwargs):
            notes = consumer['notes']
            if notes.get(NODE_NOTE_KEY, False):
                nodes.append(consumer)
        return nodes


class NodeBindCommand(ConsumerBindCommand):

    def __init__(self, context):
        super(NodeBindCommand, self).__init__(context, description=BIND_DESCRIPTION)

    def add_consumer_option(self):
        self.add_option(NODE_ID_OPTION)

    def get_consumer_id(self, kwargs):
        return kwargs[NODE_ID_OPTION.keyword]

    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return HTTP_DISTRIBUTOR


class NodeUnbindCommand(ConsumerUnbindCommand):

    def __init__(self, context):
        super(NodeUnbindCommand, self).__init__(context, description=UNBIND_DESCRIPTION)

    def add_consumer_option(self):
        self.add_option(NODE_ID_OPTION)

    def get_consumer_id(self, kwargs):
        return kwargs[NODE_ID_OPTION.keyword]

    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return HTTP_DISTRIBUTOR


class NodeActivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeActivateCommand, self).__init__(ACTIVATE_NAME, ACTIVATE_DESCRIPTION, self.run)
        self.add_option(OPTION_CONSUMER_ID)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        delta = {'notes': ACTIVATED_NOTE}
        self.context.server.consumer.update(consumer_id, delta)


class NodeDeactivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeDeactivateCommand, self).__init__(DEACTIVATE_NAME, DEACTIVATE_DESCRIPTION, self.run)
        self.add_option(OPTION_CONSUMER_ID)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        delta = {'notes': DEACTIVATED_NOTE}
        self.context.server.consumer.update(consumer_id, delta)


class NodeRepoEnableCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoEnableCommand, self).__init__(ENABLE_NAME, ENABLE_DESCRIPTION, self.run)
        self.add_option(OPTION_REPO_ID)
        self.add_option(AUTO_PUBLISH_OPTION)
        self.context = context

    def run(self, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        auto_publish = convert_boolean_arguments([AUTO_PUBLISH_OPTION.keyword], kwargs)
        self.context.server.repo_distributor.create(
            repo_id,
            HTTP_DISTRIBUTOR,
            {},
            auto_publish,
            HTTP_DISTRIBUTOR)


class NodeRepoDisableCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoDisableCommand, self).__init__(DISABLE_NAME, DISABLE_DESCRIPTION, self.run)
        self.add_option(OPTION_REPO_ID)
        self.context = context

    def run(self, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        self.context.server.repo_distributor.delete(repo_id, HTTP_DISTRIBUTOR)


class NodeUpdateCommand(ConsumerContentUpdateCommand):

    def __init__(self, context):
        super(NodeUpdateCommand, self).__init__(context, description=UPDATE_DESCRIPTION)

    def add_consumer_option(self):
        self.add_option(NODE_ID_OPTION)

    def get_consumer_id(self, kwargs):
        return kwargs[NODE_ID_OPTION.keyword]


class NodeRepoPublishCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoPublishCommand, self).__init__(PUBLISH_NAME, PUBLISH_DESCRIPTION, self.run)
        self.add_option(OPTION_REPO_ID)
        self.context = context

    def run(self, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]