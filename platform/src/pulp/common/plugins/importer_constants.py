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

# -- throttling ---------------------------------------------------------------

# Number of concurrent downloads to run
KEY_MAX_DOWNLOADS = 'max_downloads'

# Highest throughput in kB/s the sync should use
KEY_MAX_SPEED = 'max_speed'

# -- unit policy --------------------------------------------------------------

# Boolean indicating if the importer should remove units that were previously
# syncced from the repo if they are no longer present in the external feed
KEY_UNITS_REMOVE_MISSING = 'remove_missing'

# Number of non-latest versions of a unit to leave in a repository
KEY_UNITS_RETAIN_OLD_COUNT = 'retain_old_count'
