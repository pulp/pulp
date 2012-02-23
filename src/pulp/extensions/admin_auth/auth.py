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

"""
Contains components for plugging into the client extension framework.
"""

import os

from pulp.gc_client.framework.extensions import PulpCliSection, PulpCliCommand

CONTEXT = None

# -- cli components -----------------------------------------------------------

class LoginCommand(PulpCliCommand):
    def __init__(self, context):
        PulpCliCommand.__init__(self, 'login', 'logs into the Pulp server and stores a session certificate', _do_login)

        global CONTEXT
        CONTEXT = context

# -- shell components ---------------------------------------------------------

# To be added when shell support exists

# -- functionality logic ------------------------------------------------------

def _do_login(self):

    # Make the login call to the server


    # Determine and create certificate directory
    relative_dir = CONTEXT.client_config.get('filesystem', 'user_cert_dir')
    cert_dir = os.path.expanduser(relative_dir)
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    filename = CONTEXT.client_config.get('filesystem', 'user_cert_filename')
    full_cert_filename = os.path.join(cert_dir, filename)
