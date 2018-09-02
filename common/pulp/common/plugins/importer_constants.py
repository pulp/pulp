# -*- coding: utf-8 -*-
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
Contains the keys the pulp.client.commands.repo.importer_config.ImporterConfigMixin
will use to store the standard Pulp importer configuration values. See that class
docstring for more information.
"""

# -- basic sync ---------------------------------------------------------------

# Location of the external source to sync
KEY_FEED = 'feed'

# Boolean indicating if the synchronized units should be verified by size and checksum
KEY_VALIDATE = 'validate'

# -- ssl ----------------------------------------------------------------------

# PEM-encoded contents of a CA certificate used to verify its external feed
KEY_SSL_CA_CERT = 'ssl_ca_cert'

# Boolean indicating if the external feed's SSL certificate should be verified
KEY_SSL_VALIDATION = 'ssl_validation'

# PEM-encoded contents of a certificate the importer should use to connect to its
# external feed
KEY_SSL_CLIENT_CERT = 'ssl_client_cert'

# PEM-encoded contents of a private key the importer should use to connect to its
# external feed
KEY_SSL_CLIENT_KEY = 'ssl_client_key'

# -- proxy --------------------------------------------------------------------

# Hostname or IP of the proxy server
KEY_PROXY_HOST = 'proxy_host'

# Port used to contact the proxy server
KEY_PROXY_PORT = 'proxy_port'

# Username for an authenticated proxy server
KEY_PROXY_USER = 'proxy_username'

# Password for an authenticated proxy server
KEY_PROXY_PASS = 'proxy_password'

# -- basic auth

# Username for basic auth downloads
KEY_BASIC_AUTH_USER = 'basic_auth_username'

# Password for basic auth downloads
KEY_BASIC_AUTH_PASS = 'basic_auth_password'

# -- throttling ---------------------------------------------------------------

# Number of concurrent downloads to run
KEY_MAX_DOWNLOADS = 'max_downloads'

# Highest throughput in kB/s the sync should use
KEY_MAX_SPEED = 'max_speed'

# -- timeouts -----------------------------------------------------------------

# Number of seconds the Requests library will wait for nectar to establish a
# connection with a remote machine. From the Requests docs: 'It’s a good
# practice to set connect timeouts to slightly larger than a multiple of 3,
# which is the default TCP packet retransmission window.'
KEY_CONNECTION_TIMEOUT = 'connect_timeout'

# The number of seconds the client will wait for the server to send a response
# after an initial connection has already been made.
KEY_READ_TIMEOUT = 'read_timeout'

# -- unit policy --------------------------------------------------------------

# Boolean indicating if the importer should remove units that were previously
# syncced from the repo if they are no longer present in the external feed
KEY_UNITS_REMOVE_MISSING = 'remove_missing'

# Number of non-latest versions of a unit to leave in a repository
KEY_UNITS_RETAIN_OLD_COUNT = 'retain_old_count'


# Download policy (Lazy)
# IMMEDIATE  - Content is downloaded immediately.
# BACKGROUND - Content is downloaded in the background.
# ON_DEMAND  - Content is downloaded on demand.
DOWNLOAD_IMMEDIATE = 'immediate'
DOWNLOAD_ON_DEMAND = 'on_demand'
DOWNLOAD_BACKGROUND = 'background'
DOWNLOAD_POLICY = 'download_policy'
