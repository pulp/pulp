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

from pulp.bindings.exceptions import NotFoundException

from pulp.client.validators import id_validator
from pulp.client.arg_utils import convert_boolean_arguments
from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption
from pulp.client.commands.consumer.query import ConsumerListCommand
from pulp.client.commands.consumer.bind import ConsumerBindCommand, ConsumerUnbindCommand
from pulp.client.commands.consumer.content import ConsumerContentUpdateCommand
from pulp.client.commands.options import DESC_ID, OPTION_REPO_ID, OPTION_CONSUMER_ID
from pulp.client.commands.repo.sync_publish import RunPublishRepositoryCommand
from pulp.client.commands.repo.cudl import ListRepositoriesCommand

from pulp_node.extension import render_missing_resources
from pulp_node.extension import ensure_node_section
from pulp_node.extensions.admin.rendering import *

from pulp_node.constants import HTTP_DISTRIBUTOR, ALL_DISTRIBUTORS, NODE_NOTE_KEY


# --- constants --------------------------------------------------------------

REPO_NAME = _('repo')
ACTIVATE_NAME = _('activate')
DEACTIVATE_NAME = _('deactivate')
ENABLE_NAME = _('enable')
DISABLE_NAME = _('disable')
SYNC_NAME = _('sync')
PUBLISH_NAME = _('publish')

NODE_LIST_DESC = _('list child nodes')
REPO_LIST_DESC = _('list node enabled repositories')
ACTIVATE_DESC = _('activate a consumer as a child node')
DEACTIVATE_DESC = _('deactivate a child node')
BIND_DESC = _('bind a child node to a repository')
UNBIND_DESC = _('removes the binding between a child node and a repository')
UPDATE_DESC = _('triggers an immediate synchronization of a child node')
ENABLE_DESC = _('enables binding to a repository by a child node')
DISABLE_DESC = _('disables binding to a repository by a child node')
REPO_DESC = _('repository related commands')
AUTO_PUBLISH_DESC = _('auto publish flag')
SYNC_DESC = _('child node synchronization commands')
PUBLISH_DESC = _('publishing commands')

ACTIVATED_NOTE = {NODE_NOTE_KEY: True}
DEACTIVATED_NOTE = {NODE_NOTE_KEY: None}

NODE_ID_OPTION = PulpCliOption('--node-id', DESC_ID, required=True, validate_func=id_validator)
AUTO_PUBLISH_OPTION = PulpCliOption('--auto-publish', AUTO_PUBLISH_DESC, required=False)

REPO_ENABLED = _('Repository enabled')
REPO_DISABLED = _('Repository disabled')

NODE_ACTIVATED = _('Consumer activated as child node')
NODE_DEACTIVATED = _('Child node deactivated')


# --- extension loading ------------------------------------------------------

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

    repo_section = node_section.create_subsection(REPO_NAME, REPO_DESC)
    repo_section.add_command(NodeRepoEnableCommand(context))
    repo_section.add_command(NodeRepoDisableCommand(context))
    repo_section.add_command(NodeListRepositoriesCommand(context))

    publish_section = repo_section.create_subsection(PUBLISH_NAME, PUBLISH_DESC)
    publish_section.add_command(NodeRepoPublishCommand(context))

    sync_section = node_section.create_subsection(SYNC_NAME, SYNC_DESC)
    sync_section.add_command(NodeUpdateCommand(context))


# --- listing ----------------------------------------------------------------


class NodeListCommand(ConsumerListCommand):

    def __init__(self, context):
        super(NodeListCommand, self).__init__(context, description=NODE_LIST_DESC)

    def get_title(self):
        return _('Child Nodes')

    def get_consumer_list(self, kwargs):
        nodes = []
        for consumer in super(NodeListCommand, self).get_consumer_list(kwargs):
            notes = consumer['notes']
            if notes.get(NODE_NOTE_KEY, False):
                nodes.append(consumer)
        return nodes

    def format_bindings(self, consumer):
        key = 'bindings'
        bindings = consumer.get(key)
        if bindings:
            consumer[key] = [b['repo_id'] for b in bindings]


class NodeListRepositoriesCommand(ListRepositoriesCommand):

    def __init__(self, context):
        super(NodeListRepositoriesCommand, self).__init__(context, description=REPO_LIST_DESC)

    def get_repositories(self, query_params, **kwargs):
        enabled = []
        _super = super(NodeListRepositoriesCommand, self)
        repositories = _super.get_repositories(query_params, **kwargs)
        for repository in repositories:
            repo_id = repository['id']
            http = self.context.server.repo_distributor.distributors(repo_id)
            for dist in http.response_body:
                if dist['distributor_type_id'] in ALL_DISTRIBUTORS:
                    enabled.append(repository)
        return enabled


# --- bind -------------------------------------------------------------------


class NodeBindCommand(ConsumerBindCommand):

    def __init__(self, context):
        super(NodeBindCommand, self).__init__(context, description=BIND_DESC)

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
        super(NodeUnbindCommand, self).__init__(context, description=UNBIND_DESC)

    def add_consumer_option(self):
        self.add_option(NODE_ID_OPTION)

    def get_consumer_id(self, kwargs):
        return kwargs[NODE_ID_OPTION.keyword]

    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return HTTP_DISTRIBUTOR


# --- publish ----------------------------------------------------------------


class NodeRepoPublishCommand(RunPublishRepositoryCommand):

    def __init__(self, context):
        renderer = PublishRenderer(context)
        super(NodeRepoPublishCommand, self).__init__(context, renderer, HTTP_DISTRIBUTOR)


# --- activation -------------------------------------------------------------


class NodeActivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeActivateCommand, self).__init__(ACTIVATE_NAME, ACTIVATE_DESC, self.run)
        self.add_option(OPTION_CONSUMER_ID)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        delta = {'notes': ACTIVATED_NOTE}
        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.context.prompt.render_success_message(NODE_ACTIVATED)
        except NotFoundException, e:
            render_missing_resources(self.context.prompt, e)
            return os.EX_DATAERR


class NodeDeactivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeDeactivateCommand, self).__init__(DEACTIVATE_NAME, DEACTIVATE_DESC, self.run)
        self.add_option(OPTION_CONSUMER_ID)
        self.context = context

    def run(self, **kwargs):
        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        delta = {'notes': DEACTIVATED_NOTE}
        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.context.prompt.render_success_message(NODE_DEACTIVATED)
        except NotFoundException, e:
            render_missing_resources(self.context.prompt, e)
            return os.EX_DATAERR


# --- enable -----------------------------------------------------------------


class NodeRepoEnableCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoEnableCommand, self).__init__(ENABLE_NAME, ENABLE_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.add_option(AUTO_PUBLISH_OPTION)
        self.context = context

    def run(self, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        auto_publish = convert_boolean_arguments([AUTO_PUBLISH_OPTION.keyword], kwargs)
        binding = self.context.server.repo_distributor
        try:
            binding.create(repo_id, HTTP_DISTRIBUTOR, {}, auto_publish, HTTP_DISTRIBUTOR)
            self.context.prompt.render_success_message(REPO_ENABLED)
        except NotFoundException, e:
            render_missing_resources(self.context.prompt, e)
            return os.EX_DATAERR


class NodeRepoDisableCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoDisableCommand, self).__init__(DISABLE_NAME, DISABLE_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.context = context

    def run(self, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        try:
            self.context.server.repo_distributor.delete(repo_id, HTTP_DISTRIBUTOR)
            self.context.prompt.render_success_message(REPO_DISABLED)
        except NotFoundException, e:
            render_missing_resources(self.context.prompt, e)
            return os.EX_DATAERR


# --- synchronization --------------------------------------------------------


class NodeUpdateCommand(ConsumerContentUpdateCommand):

    def __init__(self, context):
        super(NodeUpdateCommand, self).__init__(
            context,
            progress_tracker=ProgressTracker(context.prompt),
            description=UPDATE_DESC)

    def add_consumer_option(self):
        self.add_option(NODE_ID_OPTION)

    def get_consumer_id(self, kwargs):
        return kwargs[NODE_ID_OPTION.keyword]

    def add_content_options(self):
        pass

    def get_content_units(self, kwargs):
        unit = dict(type_id='node', unit_key=None)
        return [unit]

    def succeeded(self, consumer_id, task):
        details = task.result['details'].values()[0]['details']
        r = UpdateRenderer(self.context.prompt, details)
        r.render()
