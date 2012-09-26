# Copyright (c) 2012 Red Hat, Inc.
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
Contains option definitions for RPM repository configuration and update, pulled
out of the repo commands module itself to keep it from becoming unwieldy.
"""

from gettext import gettext as _

from pulp.client import parsers
from pulp.client.commands import options as std_options
from pulp.client.extensions.extensions import PulpCliOption, PulpCliOptionGroup

from pulp_rpm.common import ids

# -- data ---------------------------------------------------------------------

# Used to validate user entered skip types
VALID_SKIP_TYPES = [ids.TYPE_ID_RPM, ids.TYPE_ID_DRPM, ids.TYPE_ID_DISTRO, ids.TYPE_ID_ERRATA]

# -- validators ---------------------------------------------------------------

def parse_skip_types(t):
    """
    The user-entered value is comma separated and will be the full list of
    types to skip; there is no concept of a diff.

    :param t: user entered value or None
    """
    if t is None:
        return

    parsed = t.split(',')
    parsed = [p.strip() for p in parsed]

    unmatched = [p for p in parsed if p not in VALID_SKIP_TYPES]
    if len(unmatched) > 0:
        msg = _('Types must be a comma-separated list using only the following values: %(t)s')
        msg = msg % {'t' : ', '.join(VALID_SKIP_TYPES)}
        raise ValueError(msg)

    return parsed

# -- group names --------------------------------------------------------------

NAME_BASIC = _('Basic')
NAME_THROTTLING = _('Throttling')
NAME_FEED = _('Feed Authentication')
NAME_PROXY = _('Feed Proxy')
NAME_SYNC = _('Synchronization')
NAME_PUBLISHING = _('Publishing')
NAME_AUTH = _('Client Authentication')

ALL_GROUP_NAMES = (NAME_BASIC, NAME_THROTTLING, NAME_FEED, NAME_PROXY, NAME_SYNC,
                   NAME_PUBLISHING, NAME_AUTH)

# -- metadata options ---------------------------------------------------------

d = _('URL of the external source repository to sync')
OPT_FEED = PulpCliOption('--feed', d, required=False)

# -- synchronization options --------------------------------------------------

d = _('if "true", only the newest version of a given package is downloaded; '
      'defaults to false')
OPT_NEWEST = PulpCliOption('--only-newest', d, required=False)

d = _('comma-separated list of types to omit when synchronizing, if not '
      'specified all types will be synchronized; valid values are: %(t)s')
d = d % {'t' : ', '.join(VALID_SKIP_TYPES)}
OPT_SKIP = PulpCliOption('--skip', d, required=False, parse_func=parse_skip_types)

d = _('if "true", the size of each synchronized file will be verified against '
      'the repo metadata; defaults to false')
OPT_VERIFY_SIZE = PulpCliOption('--verify-size', d, required=False, parse_func=parsers.parse_boolean)

d = _('if "true", the checksum of each synchronized file will be verified '
      'against the repo metadata; defaults to false')
OPT_VERIFY_CHECKSUM = PulpCliOption('--verify-checksum', d, required=False, parse_func=parsers.parse_boolean)

d = _('if "true", removes old packages from the repo; defaults to false')
OPT_REMOVE_OLD = PulpCliOption('--remove-old', d, required=False, parse_func=parsers.parse_boolean)

d = _('count indicating how many old rpm versions to retain; defaults to 0; '
      'this count only takes effect when remove-old option is set to true.')
OPT_RETAIN_OLD_COUNT = PulpCliOption('--retain-old-count', d, required=False,
                                     parse_func=parsers.parse_positive_int)

# -- proxy options ------------------------------------------------------------

d = _('URL to the proxy server to use')
OPT_PROXY_URL = PulpCliOption('--proxy-url', d, required=False)

d = _('port on the proxy server to make requests')
OPT_PROXY_PORT = PulpCliOption('--proxy-port', d, required=False,
                               parse_func=parsers.parse_positive_int)

d = _('username used to authenticate with the proxy server')
OPT_PROXY_USER = PulpCliOption('--proxy-user', d, required=False)

d = _('password used to authenticate with the proxy server')
OPT_PROXY_PASS = PulpCliOption('--proxy-pass', d, required=False)

# -- throttling options -------------------------------------------------------

d = _('maximum bandwidth used per download thread, in KB/sec, when '
      'synchronizing the repo')
OPT_MAX_SPEED = PulpCliOption('--max-speed', d, required=False,
                              parse_func=parsers.parse_positive_int)

d = _('number of threads that will be used to synchronize the repo')
OPT_NUM_THREADS = PulpCliOption('--num-threads', d, required=False,
                                parse_func=parsers.parse_positive_int)

# -- ssl options --------------------------------------------------------------

d = _('full path to the CA certificate that should be used to verify the '
      'external repo server\'s SSL certificate')
OPT_FEED_CA_CERT = PulpCliOption('--feed-ca-cert', d, required=False)

d = _('if "true", the feed\'s SSL certificate will be verified against the '
      'feed_ca_cert; defaults to false')
OPT_VERIFY_FEED_SSL = PulpCliOption('--verify-feed-ssl', d, required=False,
                                    parse_func=parsers.parse_boolean)

d = _('full path to the certificate to use for authentication when '
      'accessing the external feed')
OPT_FEED_CERT = PulpCliOption('--feed-cert', d, required=False)

d = _('full path to the private key for feed_cert')
OPT_FEED_KEY = PulpCliOption('--feed-key', d, required=False)

# -- publish options ----------------------------------------------------------

d = _('if "true", on each successful sync the repository will automatically be '
      'published on the configured protocols; if "false" synchronized content '
      'will only be available after manually publishing the repository; '
      'defaults to "true"')
OPT_AUTO_PUBLISH = PulpCliOption('--auto-publish', d, required=False, parse_func=parsers.parse_boolean)

d = _('relative path the repository will be served from; defaults to relative '
      'path of the feed URL')
OPT_RELATIVE_URL = PulpCliOption('--relative-url', d, required=False)

d = _('if "true", the repository will be served over HTTP; defaults to false')
OPT_SERVE_HTTP = PulpCliOption('--serve-http', d, required=False, parse_func=parsers.parse_boolean)

d = _('if "true", the repository will be served over HTTPS; defaults to true')
OPT_SERVE_HTTPS = PulpCliOption('--serve-https', d, required=False, parse_func=parsers.parse_boolean)

d = _('type of checksum to use during metadata generation')
OPT_CHECKSUM_TYPE = PulpCliOption('--checksum-type', d, required=False)

d = _('GPG key used to sign and verify packages in the repository')
OPT_GPG_KEY = PulpCliOption('--gpg-key', d, required=False)

# -- publish security options -------------------------------------------------

d = _('full path to the CA certificate that signed the repository hosts\'s SSL '
      'certificate when serving over HTTPS')
OPT_HOST_CA = PulpCliOption('--host-ca', d, required=False)

d = _('full path to the CA certificate that should be used to verify client '
      'authentication certificates; setting this turns on client '
      'authentication for the repository')
OPT_AUTH_CA = PulpCliOption('--auth-ca', d, required=False)

d = _('full path to the entitlement certificate that will be given to bound '
      'consumers to grant access to this repository')
OPT_AUTH_CERT = PulpCliOption('--auth-cert', d, required=False)

# -- public methods -----------------------------------------------------------

def add_to_command(command):
    """
    Adds the repository configuration related options to the given command,
    organizing them into the appropriate groups.

    :param command: command to add options to
    :type  command: pulp.clients.extensions.extensions.PulpCliCommand
    """

    # Groups
    basic_group = PulpCliOptionGroup(NAME_BASIC)
    throttling_group = PulpCliOptionGroup(NAME_THROTTLING)
    ssl_group = PulpCliOptionGroup(NAME_FEED)
    proxy_group = PulpCliOptionGroup(NAME_PROXY)
    sync_group = PulpCliOptionGroup(NAME_SYNC)
    publish_group = PulpCliOptionGroup(NAME_PUBLISHING)
    repo_auth_group = PulpCliOptionGroup(NAME_AUTH)

    # Order added indicates order in usage, so pay attention to this order when
    # dorking with it to make sure it makes sense
    command.add_option_group(basic_group)
    command.add_option_group(sync_group)
    command.add_option_group(publish_group)
    command.add_option_group(ssl_group)
    command.add_option_group(repo_auth_group)
    command.add_option_group(proxy_group)
    command.add_option_group(throttling_group)

    # Metadata Options - Reorganized using standard commands
    basic_group.add_option(std_options.OPTION_REPO_ID)
    basic_group.add_option(std_options.OPTION_NAME)
    basic_group.add_option(std_options.OPTION_DESCRIPTION)
    basic_group.add_option(std_options.OPTION_NOTES)

    # Synchronization Options
    sync_group.add_option(OPT_FEED)
    sync_group.add_option(OPT_NEWEST)
    sync_group.add_option(OPT_SKIP)
    sync_group.add_option(OPT_VERIFY_SIZE)
    sync_group.add_option(OPT_VERIFY_CHECKSUM)
    sync_group.add_option(OPT_REMOVE_OLD)
    sync_group.add_option(OPT_RETAIN_OLD_COUNT)

    # Proxy Options
    proxy_group.add_option(OPT_PROXY_URL)
    proxy_group.add_option(OPT_PROXY_PORT)
    proxy_group.add_option(OPT_PROXY_USER)
    proxy_group.add_option(OPT_PROXY_PASS)

    # Throttling Options
    throttling_group.add_option(OPT_MAX_SPEED)
    throttling_group.add_option(OPT_NUM_THREADS)

    # SSL Options
    ssl_group.add_option(OPT_FEED_CA_CERT)
    ssl_group.add_option(OPT_VERIFY_FEED_SSL)
    ssl_group.add_option(OPT_FEED_CERT)
    ssl_group.add_option(OPT_FEED_KEY)

    # Publish Options

    # The server-side APIs don't allow this to be updated, so hide it as an
    # option entirely; RPM repos are always published automatically with our
    # CLI until we clean that up. jdob, Sept 24, 2012
    # publish_group.add_option(OPT_AUTO_PUBLISH)

    publish_group.add_option(OPT_RELATIVE_URL)
    publish_group.add_option(OPT_SERVE_HTTP)
    publish_group.add_option(OPT_SERVE_HTTPS)
    publish_group.add_option(OPT_CHECKSUM_TYPE)
    publish_group.add_option(OPT_GPG_KEY)

    # Publish Security Options
    repo_auth_group.add_option(OPT_HOST_CA)
    repo_auth_group.add_option(OPT_AUTH_CA)
    repo_auth_group.add_option(OPT_AUTH_CERT)
