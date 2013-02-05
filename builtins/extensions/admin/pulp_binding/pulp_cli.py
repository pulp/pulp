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

from pulp.client.extensions.extensions import PulpCliSection, PulpCliFlag
from pulp.client.commands.criteria import CriteriaCommand


def initialize(context):
    """
    :type  context: pulp.client.extensions.core.ClientContext
    """
    context.cli.add_section(BindingSection(context))


class BindingSection(PulpCliSection):

    def __init__(self, context):
        """
        :type  context: pulp.client.extensions.core.ClientContext
        """
        PulpCliSection.__init__(self, 'bindings', _('search consumer bindings'))
        self.context = context
        # search
        self.add_command(Search(context))
        # unconfirmed actions
        self.add_command(SearchUnconfirmed(context))


class Search(CriteriaCommand):

    def __init__(self, context):
        CriteriaCommand.__init__(self, self.run)
        self.context = context

    def run(self, **options):
        for binding in self.context.server.bindings.search(**options):
            self.context.prompt.render_document(binding)


class SearchUnconfirmed(CriteriaCommand):

    FILTER = {'consumer_actions.status':{'$in':['pending', 'failed']}}

    def __init__(self, context):
        m = _('list bindings with consumer actions with a status of pending or failed')
        CriteriaCommand.__init__(self, self.run, 'unconfirmed', m, filtering=False)
        self.add_flag(PulpCliFlag('--bind', _('limit search to bindings with unconfirmed bind actions')))
        self.add_flag(PulpCliFlag('--unbind', _('limit search to bindings with unconfirmed unbind actions')))
        self.context = context

    def run(self, **options):
        _and = [self.FILTER]
        filter = {'$and':_and}
        if options.pop('bind'):
            _and.append({'consumer_actions.action':'bind'})
        if options.pop('unbind'):
            _and.append({'consumer_actions.action':'unbind'})
        options['filters'] = filter
        for binding in self.context.server.bindings.search(**options):
            self.context.prompt.render_document(binding)