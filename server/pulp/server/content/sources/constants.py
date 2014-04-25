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
HEADERS = 'headers'

# format: <property>, <nectar-property>, <conversion-function>
NECTAR_PROPERTIES = (
    (MAX_CONCURRENT, 'max_concurrent', int),
    (MAX_SPEED, 'max_speed', int),
    (SSL_VALIDATION, 'ssl_validation', parse_bool),
    (SSL_CA_CERT, 'ssl_ca_cert_path', str),
    (SSL_CLIENT_KEY, 'ssl_client_key_path', str),
    (SSL_CLIENT_CERT, 'ssl_client_cert_path', str),
    (PROXY_URL, 'proxy_url', str),
    (PROXY_PORT, 'proxy_port', int),
    (PROXY_USERID, 'proxy_username', str),
    (PROXY_PASSWORD, 'proxy_password', str),
    (HEADERS, 'headers', str),
)

SOURCE_ID = 'source_id'
TYPE_ID = 'type_id'
UNIT_KEY = 'unit_key'
DESTINATION = 'destination'