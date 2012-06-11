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

from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand
from pulp.bindings.exceptions import RequestException

def initialize(context):
    context.cli.add_section(ServerPluginsSection(context))

class ServerPluginsSection(PulpCliSection):
    def __init__(self, context):
        PulpCliSection.__init__(self, 'server', 'displays information about plugins and types installed on the server')
        self.context = context

        self.add_command(PulpCliCommand('types', 'lists content types installed on the server', self.types))
        self.add_command(PulpCliCommand('importers', 'lists importers installed on the server', self.importers))
        self.add_command(PulpCliCommand('distributors', 'lists distributors installed on the server', self.distributors))

        # Disabled until we update the server-side API
        # self.add_command(PulpCliCommand('ping', 'tests server availability', self.ping))

    def types(self):
        all_types = self.context.server.server_info.get_types()

        self.context.prompt.render_title('Supported Content Types')
        self.context.prompt.render_document_list(all_types.response_body, order=['id', 'display_name'])

    def importers(self):
        all_importers = self.context.server.server_info.get_importers()

        self.context.prompt.render_title('Supported Importers')
        self.context.prompt.render_document_list(all_importers.response_body, order=['id'])

    def distributors(self):
        all_distributors = self.context.server.server_info.get_distributors()

        self.context.prompt.render_title('Supported Distributors')
        self.context.prompt.render_document_list(all_distributors.response_body, order=['id'])

    def ping(self):
        try:
            self.context.server.server_info.ping()
            self.context.prompt.render_success_message('Pulp server is online')
        except RequestException, e:
            self.context.prompt.render_failure_message('Pulp server is offline')
            self.context.prompt.render_spacer()
            self.context.prompt.write(e.error_message)
