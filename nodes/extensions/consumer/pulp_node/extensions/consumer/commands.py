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

from pulp.client.extensions.decorator import priority
from pulp.client.extensions.extensions import PulpCliOption, PulpCliCommand
from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.consumer_utils import load_consumer_id

from pulp_node import constants
from pulp_node.extension import ensure_node_section, node_activated
from pulp_node.extension import missing_resources


# --- resources --------------------------------------------------------------

NODE = _('Node')
REPOSITORY = _('Repository')


# --- names ------------------------------------------------------------------

ACTIVATE_NAME = 'activate'
DEACTIVATE_NAME = 'deactivate'
BIND_NAME = 'bind'
UNBIND_NAME = 'unbind'


# --- descriptions -----------------------------------------------------------

BIND_DESC = _('bind this node to a repository')
UNBIND_DESC = _('remove the binding between this node and a repository')
ACTIVATE_DESC = _('activate a consumer as a child node')
DEACTIVATE_DESC = _('deactivate a child node')
STRATEGY_DESC = _('synchronization strategy (mirror|additive) default is additive')


# --- messages ---------------------------------------------------------------

NODE_ACTIVATED = _('Consumer activated as child node')
NODE_DEACTIVATED = _('Child node deactivated')
BIND_SUCCEEDED = _('Node bind succeeded.')
UNBIND_SUCCEEDED = _('Node unbind succeeded')
BIND_FAILED_NOT_ENABLED = _('Repository not enabled. See: \'node repo enable\' command.')
NOT_BOUND_NOTHING_DONE = _('Node not bound to repository. No action performed.')
NOT_ACTIVATED_NOTHING_DONE = _('This consumer is not activated as a node. No action performed.')
NOT_ACTIVATED_ERROR = _('This consumer is not activated as a node. See: \'node activate\' command.')
STRATEGY_NOT_SUPPORTED = _('Strategy [ %(n)s ] not supported. Must be one of: %(s)s')
RESOURCE_MISSING_ERROR = _('%(t)s [ %(id)s ] not found on the server.')
NOT_REGISTERED_MESSAGE = _('This consumer is not registered.')
ALREADY_ACTIVATED_NOTHING_DONE = _('This consumer already activated.  No action performed.')

BIND_WARNING = \
    _('Note: Repository [ %(r)s ] will be included in node synchronization.')
UNBIND_WARNING = \
    _('Warning: Repository [ %(r)s ] will NOT be included in node synchronization')


# --- options ----------------------------------------------------------------

STRATEGY_OPTION = PulpCliOption('--strategy', STRATEGY_DESC, required=False,
                                default=constants.ADDITIVE_STRATEGY)


# --- extension loading ------------------------------------------------------

@priority()
def initialize(context):
    """
    :type context: pulp.client.extensions.core.ClientContext
    """
    node_section = ensure_node_section(context.cli)
    node_section.add_command(NodeActivateCommand(context))
    node_section.add_command(NodeDeactivateCommand(context))
    node_section.add_command(NodeBindCommand(context))
    node_section.add_command(NodeUnbindCommand(context))


# --- activation -------------------------------------------------------------

class NodeActivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeActivateCommand, self).__init__(ACTIVATE_NAME, ACTIVATE_DESC, self.run)
        self.add_option(STRATEGY_OPTION)
        self.context = context

    def run(self, **kwargs):

        consumer_id = load_consumer_id(self.context)
        strategy = kwargs[STRATEGY_OPTION.keyword]
        delta = {'notes': {constants.NODE_NOTE_KEY: True, constants.STRATEGY_NOTE_KEY: strategy}}

        if node_activated(self.context, consumer_id):
            self.context.prompt.render_success_message(ALREADY_ACTIVATED_NOTHING_DONE)
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
                    self.context.prompt.render_failure_message(NOT_REGISTERED_MESSAGE)
                else:
                    raise
            return os.EX_DATAERR


class NodeDeactivateCommand(PulpCliCommand):

    def __init__(self, context):
        super(NodeDeactivateCommand, self).__init__(DEACTIVATE_NAME, DEACTIVATE_DESC, self.run)
        self.context = context

    def run(self, **kwargs):

        consumer_id = load_consumer_id(self.context)
        delta = {'notes': {constants.NODE_NOTE_KEY: None, constants.STRATEGY_NOTE_KEY: None}}

        if not node_activated(self.context, consumer_id):
            self.context.prompt.render_success_message(NOT_ACTIVATED_NOTHING_DONE)
            return

        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.context.prompt.render_success_message(NODE_DEACTIVATED)
        except NotFoundException, e:
            for _id, _type in missing_resources(e):
                if _type == 'consumer':
                    self.context.prompt.render_failure_message(NOT_REGISTERED_MESSAGE)
                else:
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
        self.add_option(STRATEGY_OPTION)
        self.context = context

    def run(self, **kwargs):

        repo_id = kwargs[OPTION_REPO_ID.keyword]
        node_id = load_consumer_id(self.context)
        dist_id = constants.HTTP_DISTRIBUTOR
        strategy = kwargs[STRATEGY_OPTION.keyword]
        binding_config = {constants.STRATEGY_KEYWORD: strategy}

        if not node_activated(self.context, node_id):
            msg = NOT_ACTIVATED_ERROR
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
                    msg = BIND_FAILED_NOT_ENABLED
                    self.context.prompt.render_failure_message(msg)
                else:
                    raise
            return os.EX_DATAERR


class NodeUnbindCommand(BindingCommand):

    def __init__(self, context):
        super(NodeUnbindCommand, self).__init__(UNBIND_NAME, UNBIND_DESC, self.run)
        self.add_option(OPTION_REPO_ID)
        self.context = context

    def run(self, **kwargs):

        repo_id = kwargs[OPTION_REPO_ID.keyword]
        node_id = load_consumer_id(self.context)
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
