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
from pulp.client.arg_utils import convert_boolean_arguments
from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOption
from pulp.client.commands.polling import PollingCommand
from pulp.client.commands.consumer.query import ConsumerListCommand
from pulp.client.commands.options import OPTION_REPO_ID, OPTION_CONSUMER_ID
from pulp.client.commands.repo.cudl import ListRepositoriesCommand

from pulp_node import constants
from pulp_node.extension import missing_resources, node_activated, repository_enabled, ensure_node_section
from pulp_node.extensions.admin import sync_schedules
from pulp_node.extensions.admin.options import NODE_ID_OPTION, MAX_BANDWIDTH_OPTION, MAX_CONCURRENCY_OPTION
from pulp_node.extensions.admin.rendering import ProgressTracker, UpdateRenderer


# --- resources --------------------------------------------------------------

NODE = _('Node')
CONSUMER = _('Consumer')
REPOSITORY = _('Repository')


# --- names ------------------------------------------------------------------

REPO_NAME = 'repo'
ACTIVATE_NAME = 'activate'
DEACTIVATE_NAME = 'deactivate'
ENABLE_NAME = 'enable'
DISABLE_NAME = 'disable'
SYNC_NAME = 'sync'
PUBLISH_NAME = 'publish'
BIND_NAME = 'bind'
UNBIND_NAME = 'unbind'
UPDATE_NAME = 'run'
SCHEDULES_NAME = 'schedules'


# --- descriptions -----------------------------------------------------------

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
AUTO_PUBLISH_DESC = _('if "true", the nodes information will be automatically published each '
                      'time the repository is synchronized; defaults to "true"')
SYNC_DESC = _('child node synchronization commands')
PUBLISH_DESC = _('publishing commands')
STRATEGY_DESC = _('synchronization strategy (mirror|additive) default is additive')
SCHEDULES_DESC = _('manage node sync schedules')


# --- titles -----------------------------------------------------------------

NODE_LIST_TITLE = _('Child Nodes')
REPO_LIST_TITLE = _('Enabled Repositories')


# --- options ----------------------------------------------------------------

AUTO_PUBLISH_OPTION = PulpCliOption('--auto-publish', AUTO_PUBLISH_DESC, required=False, default='true')

STRATEGY_OPTION = \
    PulpCliOption('--strategy', STRATEGY_DESC, required=False, default=constants.ADDITIVE_STRATEGY)

# --- messages ---------------------------------------------------------------

REPO_ENABLED = _('Repository enabled.')
REPO_DISABLED = _('Repository disabled.')
PUBLISH_SUCCEEDED = _('Publish succeeded.')
PUBLISH_FAILED = _('Publish failed. See: pulp log for details.')
NODE_ACTIVATED = _('Consumer activated as child node.')
NODE_DEACTIVATED = _('Child node deactivated.')
BIND_SUCCEEDED = _('Node bind succeeded.')
UNBIND_SUCCEEDED = _('Node unbind succeeded')
ALREADY_ENABLED = _('Repository already enabled. Nothing done.')
FAILED_NOT_ENABLED = _('Repository not enabled. See: the \'node repo enable\' command.')
NOT_BOUND_NOTHING_DONE = _('Node not bound to repository. No action performed.')
NOT_ACTIVATED_ERROR = _('%(t)s [ %(id)s ] not activated as a node. See: the \'node activate\' command.')
NOT_ACTIVATED_NOTHING_DONE = _('%(t)s is not activated as a node. No action performed.')
NOT_ENABLED_NOTHING_DONE = _('%(t)s not enabled. No action performed.')
STRATEGY_NOT_SUPPORTED = _('Strategy [ %(n)s ] not supported. Must be one of: %(s)s')
RESOURCE_MISSING_ERROR = _('%(t)s [ %(id)s ] not found on the server.')
ALREADY_ACTIVATED_NOTHING_DONE = _('%(n)s already activated as child node. No action performed.')

BIND_WARNING = \
    _('Note: Repository [ %(r)s ] will be included in node synchronization.')
UNBIND_WARNING = \
    _('Warning: Repository [ %(r)s ] will NOT be included in node synchronization')

ENABLE_WARNING = \
    _('Note: Repository [ %(r)s ] will not be available for node synchronization until published.'
      '  See: the \'node repo publish\' command.')

AUTO_PUBLISH_WARNING = \
    _('Warning: enabling with auto-publish may degrade repository synchronization performance.')


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
    repo_section.add_command(NodeRepoPublishCommand(context))

    sync_section = node_section.create_subsection(SYNC_NAME, SYNC_DESC)
    sync_section.add_command(NodeUpdateCommand(context))

    schedules_section = sync_section.create_subsection(SCHEDULES_NAME, SCHEDULES_DESC)
    schedules_section.add_command(sync_schedules.NodeCreateScheduleCommand(context))
    schedules_section.add_command(sync_schedules.NodeDeleteScheduleCommand(context))
    schedules_section.add_command(sync_schedules.NodeUpdateScheduleCommand(context))
    schedules_section.add_command(sync_schedules.NodeListScheduleCommand(context))
    schedules_section.add_command(sync_schedules.NodeNextRunCommand(context))


# --- listing ----------------------------------------------------------------

class NodeListCommand(ConsumerListCommand):

    STRATEGY_FIELD = 'update_strategy'

    _ALL_FIELDS = ConsumerListCommand._ALL_FIELDS[0:-1] \
        + [STRATEGY_FIELD] + ConsumerListCommand._ALL_FIELDS[-1:]

    def __init__(self, context):
        super(NodeListCommand, self).__init__(context, description=NODE_LIST_DESC)

    def get_title(self):
        return NODE_LIST_TITLE

    def get_consumer_list(self, kwargs):
        nodes = []
        for consumer in super(NodeListCommand, self).get_consumer_list(kwargs):
            notes = consumer['notes']
            if not notes.get(constants.NODE_NOTE_KEY):
                continue
            consumer[self.STRATEGY_FIELD] = \
                notes.get(constants.STRATEGY_NOTE_KEY, constants.DEFAULT_STRATEGY)
            nodes.append(consumer)
        return nodes

    def format_bindings(self, consumer):
        formatted = {}
        key = 'bindings'
        for b in consumer.get(key, []):
            repo_id = b['repo_id']
            strategy = b['binding_config'].get('strategy', constants.DEFAULT_STRATEGY)
            repo_ids = formatted.get(strategy)
            if repo_ids is None:
                repo_ids = []
                formatted[strategy] = repo_ids
            repo_ids.append(repo_id)
        consumer[key] = formatted


class NodeListRepositoriesCommand(ListRepositoriesCommand):

    def __init__(self, context):
        super(NodeListRepositoriesCommand, self).__init__(
            context,
            description=REPO_LIST_DESC,
            repos_title=REPO_LIST_TITLE)

    def get_repositories(self, query_params, **kwargs):
        enabled = []
        _super = super(NodeListRepositoriesCommand, self)
        repositories = _super.get_repositories(query_params, **kwargs)
        for repository in repositories:
            repo_id = repository['id']
            http = self.context.server.repo_distributor.distributors(repo_id)
            for dist in http.response_body:
                if dist['distributor_type_id'] in constants.ALL_DISTRIBUTORS:
                    enabled.append(repository)
        return enabled


# --- publishing -------------------------------------------------------------

class NodeRepoPublishCommand(PollingCommand):

    def __init__(self, context):
        super(NodeRepoPublishCommand, self).__init__(PUBLISH_NAME, PUBLISH_DESC, self.run, context)
        self.add_option(OPTION_REPO_ID)

    def run(self, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]

        if not repository_enabled(self.context, repo_id):
            msg = FAILED_NOT_ENABLED
            self.context.prompt.render_success_message(msg)
            return

        try:
            http = self.context.server.repo_actions.publish(repo_id, constants.HTTP_DISTRIBUTOR, {})
            task = http.response_body
            self.poll([task], kwargs)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'repo_id':
                    msg = RESOURCE_MISSING_ERROR % dict(t=REPOSITORY, id=_id)
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR

    def succeeded(self, task):
        self.context.prompt.render_success_message(PUBLISH_SUCCEEDED)

    def failed(self, task):
        self.context.prompt.render_failure_message(PUBLISH_FAILED)


# --- activation -------------------------------------------------------------

class NodeActivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeActivateCommand, self).__init__(ACTIVATE_NAME, ACTIVATE_DESC, self.run)
        self.add_option(OPTION_CONSUMER_ID)
        self.add_option(STRATEGY_OPTION)
        self.context = context

    def run(self, **kwargs):

        consumer_id = kwargs[OPTION_CONSUMER_ID.keyword]
        strategy = kwargs[STRATEGY_OPTION.keyword]
        delta = {'notes': {constants.NODE_NOTE_KEY: True, constants.STRATEGY_NOTE_KEY: strategy}}

        if node_activated(self.context, consumer_id):
            msg = ALREADY_ACTIVATED_NOTHING_DONE % dict(n=CONSUMER)
            self.context.prompt.render_success_message(msg)
            return

        if strategy not in constants.STRATEGIES:
            msg = STRATEGY_NOT_SUPPORTED % dict(n=strategy, s=constants.STRATEGIES)
            self.context.prompt.render_failure_message(msg)
            return os.EX_DATAERR

        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.context.prompt.render_success_message(NODE_ACTIVATED)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'consumer':
                    msg = RESOURCE_MISSING_ERROR % dict(t=CONSUMER, id=_id)
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR


class NodeDeactivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeDeactivateCommand, self).__init__(DEACTIVATE_NAME, DEACTIVATE_DESC, self.run)
        self.add_option(NODE_ID_OPTION)
        self.context = context

    def run(self, **kwargs):

        consumer_id = kwargs[NODE_ID_OPTION.keyword]
        delta = {'notes': {constants.NODE_NOTE_KEY: None, constants.STRATEGY_NOTE_KEY: None}}

        if not node_activated(self.context, consumer_id):
            msg = NOT_ACTIVATED_NOTHING_DONE % dict(t=CONSUMER)
            self.context.prompt.render_success_message(msg)
            return

        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.context.prompt.render_success_message(NODE_DEACTIVATED)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'consumer':
                    msg = RESOURCE_MISSING_ERROR % dict(t=CONSUMER, id=_id)
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR


# --- enable -----------------------------------------------------------------

class NodeRepoEnableCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoEnableCommand, self).__init__(ENABLE_NAME, ENABLE_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.add_option(AUTO_PUBLISH_OPTION)
        self.context = context

    def run(self, **kwargs):

        convert_boolean_arguments([AUTO_PUBLISH_OPTION.keyword], kwargs)

        repo_id = kwargs[OPTION_REPO_ID.keyword]
        auto_publish = kwargs[AUTO_PUBLISH_OPTION.keyword]
        binding = self.context.server.repo_distributor

        if repository_enabled(self.context, repo_id):
            msg = ALREADY_ENABLED
            self.context.prompt.render_success_message(msg)
            return

        try:
            binding.create(
                repo_id,
                constants.HTTP_DISTRIBUTOR,
                {},
                auto_publish,
                constants.HTTP_DISTRIBUTOR)
            self.context.prompt.render_success_message(REPO_ENABLED)
            self.context.prompt.render_warning_message(ENABLE_WARNING % dict(r=repo_id))
            if auto_publish:
                self.context.prompt.render_warning_message(AUTO_PUBLISH_WARNING)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'repository':
                    msg = RESOURCE_MISSING_ERROR % dict(t=REPOSITORY, id=_id)
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR


class NodeRepoDisableCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeRepoDisableCommand, self).__init__(DISABLE_NAME, DISABLE_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.context = context

    def run(self, **kwargs):

        repo_id = kwargs[OPTION_REPO_ID.keyword]

        try:
            self.context.server.repo_distributor.delete(repo_id, constants.HTTP_DISTRIBUTOR)
            self.context.prompt.render_success_message(REPO_DISABLED)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'repository':
                    msg = RESOURCE_MISSING_ERROR % dict(t=REPOSITORY, id=_id)
                    self.context.prompt.render_failure_message(msg)
                    continue
                if _type == 'distributor':
                    msg = NOT_ENABLED_NOTHING_DONE % dict(t=REPOSITORY)
                    self.context.prompt.render_success_message(msg)
                    continue
                raise
            return os.EX_DATAERR


# --- bind -------------------------------------------------------------------

class BindingCommand(PulpCliCommand):

    def missing_resources(self, prompt, exception):
        unhandled = []
        for _id, _type in missing_resources(exception):
            if _type == 'consumer_id':
                msg = RESOURCE_MISSING_ERROR % dict(t=NODE, id=_id)
                prompt.render_failure_message(msg)
                continue
            if _type == 'repo_id':
                msg = RESOURCE_MISSING_ERROR % dict(t=REPOSITORY, id=_id)
                prompt.render_failure_message(msg)
                continue
            unhandled.append((_id, _type))
        return unhandled


class NodeBindCommand(BindingCommand):

    def __init__(self, context):
        super(NodeBindCommand, self).__init__(BIND_NAME, BIND_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.add_option(NODE_ID_OPTION)
        self.add_option(STRATEGY_OPTION)
        self.context = context

    def run(self, **kwargs):

        repo_id = kwargs[OPTION_REPO_ID.keyword]
        node_id = kwargs[NODE_ID_OPTION.keyword]
        dist_id = constants.HTTP_DISTRIBUTOR
        strategy = kwargs[STRATEGY_OPTION.keyword]
        binding_config = {constants.STRATEGY_KEYWORD: strategy}

        if not node_activated(self.context, node_id):
            msg = NOT_ACTIVATED_ERROR % dict(t=CONSUMER, id=node_id)
            self.context.prompt.render_failure_message(msg)
            return os.EX_USAGE

        if strategy not in constants.STRATEGIES:
            msg = STRATEGY_NOT_SUPPORTED % dict(n=strategy, s=constants.STRATEGIES)
            self.context.prompt.render_failure_message(msg)
            return os.EX_DATAERR

        try:
            self.context.server.bind.bind(
                node_id,
                repo_id,
                dist_id,
                notify_agent=False,
                binding_config=binding_config)
            self.context.prompt.render_success_message(BIND_SUCCEEDED)
            warning = BIND_WARNING % dict(r=repo_id)
            self.context.prompt.render_warning_message(warning)
        except NotFoundException, e:
            unhandled = self.missing_resources(self.context.prompt, e)
            for _id, _type in unhandled:
                if _type == 'distributor':
                    msg = FAILED_NOT_ENABLED
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR


class NodeUnbindCommand(BindingCommand):

    def __init__(self, context):
        super(NodeUnbindCommand, self).__init__(UNBIND_NAME, UNBIND_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.add_option(NODE_ID_OPTION)
        self.context = context

    def run(self, **kwargs):

        repo_id = kwargs[OPTION_REPO_ID.keyword]
        node_id = kwargs[NODE_ID_OPTION.keyword]
        dist_id = constants.HTTP_DISTRIBUTOR

        try:
            self.context.server.bind.unbind(node_id, repo_id, dist_id)
            self.context.prompt.render_success_message(UNBIND_SUCCEEDED)
            warning = UNBIND_WARNING % dict(r=repo_id)
            self.context.prompt.render_warning_message(warning)
        except NotFoundException, e:
            unhandled = self.missing_resources(self.context.prompt, e)
            for _id, _type in unhandled:
                if _type == 'bind_id':
                    msg = NOT_BOUND_NOTHING_DONE
                    self.context.prompt.render_success_message(msg)
                else:
                    raise
            return os.EX_DATAERR


# --- synchronization --------------------------------------------------------

class NodeUpdateCommand(PollingCommand):

    def __init__(self, context):
        super(NodeUpdateCommand, self).__init__(UPDATE_NAME, UPDATE_DESC, self.run, context)
        self.add_option(NODE_ID_OPTION)
        self.add_option(MAX_CONCURRENCY_OPTION)
        self.add_option(MAX_BANDWIDTH_OPTION)
        self.tracker = ProgressTracker(self.context.prompt)

    def run(self, **kwargs):
        node_id = kwargs[NODE_ID_OPTION.keyword]
        max_bandwidth = kwargs[MAX_BANDWIDTH_OPTION.keyword]
        max_concurrency = kwargs[MAX_CONCURRENCY_OPTION.keyword]
        units = [dict(type_id='node', unit_key=None)]
        options = {
            constants.MAX_DOWNLOAD_BANDWIDTH_KEYWORD: max_bandwidth,
            constants.MAX_DOWNLOAD_CONCURRENCY_KEYWORD: max_concurrency,
        }

        if not node_activated(self.context, node_id):
            msg = NOT_ACTIVATED_ERROR % dict(t=CONSUMER, id=node_id)
            self.context.prompt.render_failure_message(msg)
            return os.EX_USAGE

        try:
            http = self.context.server.consumer_content.update(node_id, units=units, options=options)
            task = http.response_body
            self.poll([task], kwargs)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'consumer':
                    msg = RESOURCE_MISSING_ERROR % dict(t=NODE, id=_id)
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR

    def progress(self, task, spinner):
        self.tracker.display(task.progress_report)

    def succeeded(self, task):
        report = task.result['details'].values()[0]
        r = UpdateRenderer(self.context.prompt, report)
        r.render()
