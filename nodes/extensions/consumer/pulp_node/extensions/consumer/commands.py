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
from pulp.client.commands.consumer.bind import ConsumerBindCommand, ConsumerUnbindCommand
from pulp.client.consumer_utils import load_consumer_id

from pulp_node import constants
from pulp_node.extension import ensure_node_section
from pulp_node.extension import render_missing_resources


# --- constants --------------------------------------------------------------


ACTIVATE_NAME = _('activate')
DEACTIVATE_NAME = _('deactivate')

BIND_DESC = _('bind a child node to a repository')
UNBIND_DESC = _('removes the binding between a child node and a repository')
ACTIVATE_DESC = _('activate a consumer as a child node')
DEACTIVATE_DESC = _('deactivate a child node')
STRATEGY_DESC = _('synchronization strategy (mirror|additive) default is additive')

ACTIVATED_NOTE = {constants.NODE_NOTE_KEY: True}
DEACTIVATED_NOTE = {constants.NODE_NOTE_KEY: None}

NODE_ACTIVATED = _('Consumer activated as child node')
NODE_DEACTIVATED = _('Child node deactivated')

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
        self.context = context

    def run(self, **kwargs):
        consumer_id = load_consumer_id(self.context)
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
        self.context = context

    def run(self, **kwargs):
        consumer_id = load_consumer_id(self.context)
        delta = {'notes': DEACTIVATED_NOTE}
        try:
            self.context.server.consumer.update(consumer_id, delta)
            self.context.prompt.render_success_message(NODE_DEACTIVATED)
        except NotFoundException, e:
            render_missing_resources(self.context.prompt, e)
            return os.EX_DATAERR


# --- bind -------------------------------------------------------------------


class NodeBindCommand(ConsumerBindCommand):

    def __init__(self, context):
        super(NodeBindCommand, self).__init__(context, description=BIND_DESC)
        self.add_option(STRATEGY_OPTION)

    def add_consumer_option(self):
        pass

    def get_consumer_id(self, kwargs):
        return load_consumer_id(self.context)

    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return constants.HTTP_DISTRIBUTOR


class NodeUnbindCommand(ConsumerUnbindCommand):

    def __init__(self, context):
        super(NodeUnbindCommand, self).__init__(context, description=UNBIND_DESC)

    def add_consumer_option(self):
        pass

    def get_consumer_id(self, kwargs):
        return load_consumer_id(self.context)

    def add_distributor_option(self):
        pass

    def get_distributor_id(self, kwargs):
        return constants.HTTP_DISTRIBUTOR