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
import socket

from pulp.common.config import Config
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings


def parent_bindings():
    # OAUTH
    node_conf = Config('/etc/pulp/nodes/child.conf')
    node_conf = node_conf.graph()
    oauth = node_conf.oauth
    if oauth.host and oauth.port and oauth.key and oauth.secret and oauth.user_id:
        connection = PulpConnection(
            host=oauth.host,
            port=oauth.port,
            oauth_key=oauth.key,
            oauth_secret=oauth.secret,
            oauth_user=oauth.user_id)
        return Bindings(connection)
    # SSL
    path = '/etc/pulp/consumer/consumer.conf'
    if os.path.exists(path):
        pulp_conf = Config(path)
        pulp_conf = pulp_conf.graph()
        cert_path = os.path.join(
            pulp_conf.filesystem.id_cert_dir, pulp_conf.filesystem.id_cert_filename)
        connection = PulpConnection(
            pulp_conf.server.host,
            pulp_conf.server.port,
            cert_filename=cert_path)
        return Bindings(connection)


def pulp_bindings():
    # OAUTH
    pulp_conf = Config('/etc/pulp/server.conf')
    pulp_conf = pulp_conf.graph()
    oauth = pulp_conf.oauth
    if oauth.enabled:
        connection = PulpConnection(
            host=pulp_conf.server.host,
            port=pulp_conf.server.port,
            oauth_key=oauth.oauth_key,
            oauth_secret=oauth.oauth_secret,
            oauth_user=pulp_conf.server.default_login)
        return Bindings(connection)
    # SSL
    host = socket.gethostname()
    port = 443
    cert_path = '/etc/pki/pulp/nodes/local.crt'
    connection = PulpConnection(host=host, port=port, cert_filename=cert_path)
    return Bindings(connection)