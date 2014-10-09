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
"""
The descriptor declares and defines properties for a content source.
The [section] defines the content source ID.  The following properties
are supported:
 - enabled <bool>
     The content source is enabled. Disabled sources are ignored.
 - name <str>
     The content source display name.
 - type <str>
     The type of content source.  Must correspond to the ID of a cataloger plugin ID.
 - priority <int>
     The source priority used when downloading content.  (0 is lowest and the default).
 - expires <str>
     How long until cataloged information expires. The default unit is seconds however
     an optional suffix can (and should) be used.  Supported suffixes:
     (s=seconds, m=minutes, h=hours, d=days)
 - base_url <str>
     The URL used to fetch info used to refresh the catalog.
 - paths <str>
     An optional list of URL relative paths.  Delimited by space or newline.
 - max_concurrent <int>
     Limit the number of concurrent downloads.
 - max_speed <int>
     Limit the bandwidth used during downloads.
 - ssl_ca_cert <str>
     An optional SSL CA certificate (absolute path).
 - ssl_validation <bool>
     An optional flag to validate the server SSL certificate using the CA.
 - ssl_client_cert <str>
     An optional SSL client certificate (absolute path).
 - ssl_client_key <str>
     An optional SSL client key (absolute path).
 - proxy_url <str>
     An optional URL for a proxy.
 - proxy_port <short>
     An optional proxy port#.
 - proxy_username <str>
     An optional proxy userid.
 - proxy_password <str>
     An optional proxy password.

Example:

[content-world]
enabled: 1
priority: 0
expires: 3d
name: Content World
type: yum
base_url: http://content-world/content/
paths: f18/x86_64/os/ \
     f18/i386/os/ \
     f19/x86_64/os \
     f19/i386/os
max_concurrent: 10
max_speed: 1000
ssl_ca_cert: /etc/pki/tls/certs/content-world.ca
ssl_client_key: /etc/pki/tls/private/content-world.key
ssl_client_cert: /etc/pki/tls/certs/content-world.crt
"""

from logging import getLogger

from nectar.config import DownloaderConfig
from pulp.common.config import Config, Validator, ValidationException
from pulp.common.config import REQUIRED, OPTIONAL, BOOL, ANY, NUMBER

from pulp.server.content.sources import constants


log = getLogger(__name__)

DEFAULT = {
    constants.PRIORITY: '0',
    constants.EXPIRES: '24h',
    constants.MAX_CONCURRENT: '2',
    constants.SSL_VALIDATION: 'true'
}

SCHEMA = [
    None, REQUIRED,
    (
        (constants.ENABLED, REQUIRED, BOOL),
        (constants.TYPE, REQUIRED, ANY),
        (constants.BASE_URL, REQUIRED, ANY),
        (constants.PRIORITY, OPTIONAL, NUMBER),
        (constants.EXPIRES, OPTIONAL, ANY),
        (constants.PATHS, OPTIONAL, ANY),
        (constants.MAX_CONCURRENT, OPTIONAL, NUMBER),
        (constants.MAX_SPEED, OPTIONAL, NUMBER),
        (constants.SSL_VALIDATION, OPTIONAL, BOOL),
        (constants.SSL_CA_CERT, OPTIONAL, ANY),
        (constants.SSL_CLIENT_KEY, OPTIONAL, ANY),
        (constants.SSL_CA_CERT, OPTIONAL, ANY),
        (constants.PROXY_URL, OPTIONAL, ANY),
        (constants.PROXY_PORT, OPTIONAL, NUMBER),
        (constants.PROXY_USERID, OPTIONAL, ANY),
        (constants.PROXY_PASSWORD, OPTIONAL, ANY),
    )
]


def is_valid(source_id, descriptor):
    """
    Get whether a content source descriptor is valid.
    :param source_id: A content source ID.
    :type source_id: str
    :param descriptor: A content source descriptor.
    :type descriptor: dict
    :return: True if valid.
    :rtype: bool
    """
    try:
        schema = list(SCHEMA)
        schema[0] = source_id
        validator = Validator((schema,))
        cfg = Config({source_id: descriptor})
        validator.validate(cfg)
        return True
    except ValidationException, e:
        log.error(str(e))
    return False


def to_seconds(duration):
    """
    Convert the specified duration into seconds.
    The duration unit is seconds by default or specified as follows
    using an optional suffix (s=seconds, m=minutes, h=hours, d=days).
    Example: '10m' = 10 minutes; '30d' = 30 days.
    :param duration: A duration.
    :type duration: str
    :return: The duration in seconds.
    :rtype: int
    """
    if duration.endswith('s'):
        return int(duration[:-1])
    if duration.endswith('m'):
        return int(duration[:-1]) * 60
    if duration.endswith('h'):
        return int(duration[:-1]) * 3600
    if duration.endswith('d'):
        return int(duration[:-1]) * 3600 * 24
    return int(duration)


def nectar_config(descriptor):
    """
    Create a nectar download configuration using the specified
    content source descriptor.  The nectar options are a subset of
    the properties included in the descriptor.
    :param descriptor: A content source descriptor.
    :type descriptor: dict
    :return: A nectar configuration.
    :rtype: DownloaderConfig
    """
    options = {}
    for key, option, fn in constants.NECTAR_PROPERTIES:
        value = descriptor.get(key)
        if value:
            options[option] = fn(value)
    return DownloaderConfig(**options)
