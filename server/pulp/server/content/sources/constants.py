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

from pulp.common.config import parse_bool


URL = 'url'

ENABLED = 'enabled'
NAME = 'name'
TYPE = 'type'
BASE_URL = 'base_url'
PATHS = 'paths'
PRIORITY = 'priority'
EXPIRES = 'expires'

MAX_CONCURRENT = 'max_concurrent'
MAX_SPEED = 'max_speed'
SSL_VALIDATION = 'ssl_validation'
SSL_CA_CERT = 'ssl_ca_cert'
SSL_CLIENT_KEY = 'ssl_client_key'
SSL_CLIENT_CERT = 'ssl_client_cert'
PROXY_URL = 'proxy_url'
PROXY_PORT = 'proxy_port'
PROXY_USERID = 'proxy_username'
PROXY_PASSWORD = 'proxy_password'

NECTAR_PROPERTIES = (
    (MAX_CONCURRENT, int),
    (MAX_SPEED, int),
    (SSL_VALIDATION, parse_bool),
    (SSL_CA_CERT, str),
    (SSL_CLIENT_KEY, str),
    (SSL_CLIENT_CERT, str),
    (PROXY_URL, str),
    (PROXY_PORT, int),
    (PROXY_USERID, str),
    (PROXY_PASSWORD, str),
)

SOURCE_ID = 'source_id'
TYPE_ID = 'type_id'
UNIT_KEY = 'unit_key'
DESTINATION = 'destination'