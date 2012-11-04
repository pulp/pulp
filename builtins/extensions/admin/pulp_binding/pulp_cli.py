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

from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand
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
        PulpCliSection.__init__(self, 'bindings', _('search bindings'))
        self.context = context
        # search
        self.add_command(Search(context))
        # outstanding
        outstanding = PulpCliSection('outstanding', _('find outstanding bindings'))
        outstanding.add_command(Outstanding(context))
        outstanding.add_command(OutstandingBindActions(context))
        outstanding.add_command(OutstandingUnbindActions(context))
        self.add_subsection(outstanding)


class Search(CriteriaCommand):

    def __init__(self, context):
        CriteriaCommand.__init__(self, self.run)
        self.context = context

    def run(self, **options):
        for binding in self.context.server.bindings.search(**options):
            self.context.prompt.render_document(binding)


class Outstanding(CriteriaCommand):

    FILTER = {'consumer_actions.status':{'$in':['pending', 'failed']}}

    def __init__(self, context):
        m = _('find bindings with outstanding actions')
        CriteriaCommand.__init__(self, self.run, 'all', m, filtering=False)
        self.context = context

    def run(self, **options):
        options['filters'] = self.FILTER
        for binding in self.context.server.bindings.search(**options):
            self.context.prompt.render_document(binding)

class OutstandingBindActions(CriteriaCommand):

    def __init__(self, context):
        m = _('list bindings with outstanding BIND actions')
        CriteriaCommand.__init__(self, self.run, 'binds', m, filtering=False)
        self.context = context

    def run(self, **options):
        filter = {
            '$and':[
                Outstanding.FILTER,
                {'consumer_actions.action':'bind'},
            ]
        }
        options['filters'] = filter
        for binding in self.context.server.bindings.search(**options):
            self.context.prompt.render_document(binding)


class OutstandingUnbindActions(CriteriaCommand):

    def __init__(self, context):
        m = _('list bindings with outstanding UNBIND actions')
        CriteriaCommand.__init__(self, self.run, 'unbinds', m, filtering=False)
        self.context = context

    def run(self, **options):
        filter = {
            '$and':[
                Outstanding.FILTER,
                {'consumer_actions.action':'unbind'},
            ]
        }
        options['filters'] = filter
        for binding in self.context.server.bindings.search(**options):
            self.context.prompt.render_document(binding)
