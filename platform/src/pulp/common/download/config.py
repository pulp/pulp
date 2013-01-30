# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt


class DownloaderConfig(object):
    """
    Downloader configuration class that represents the type of download backend,
    as well as, it's configuration. Instances of this class are used by the
    download factory to determine which download backend to use.

    Currently supported configuration values are:

     * protocol: network protocol to use (http, https)
     * max_concurrent: maximum number of downloads to run concurrently
     * basic_auth_username: http basic auth username (basic_auth_password must also be provided)
     * basic_auth_password: http basic auth password (basic_auth_username must also be provided)
     * ssl_ca_cert: certificate authority cert for secure connections (https protocol only)
     * ssl_ca_cert_path: path to a ssl ca cert (incompatible with ssl_ca_cert)
     * ssl_client_cert: client certificate for secure connections (https protocol only)
     * ssl_client_cert_path: path to a ssl client cert (incompatible with ssl_client_cert)
     * ssl_client_key: client private key for secure connections (https protocol only)
     * ssl_client_key_path: path to a ssl client key (incompatible with ssl_client_key)
    """

    def __init__(self, protocol, **kwargs):
        """
        :param protocol: network protocol to use
        :type protocol: str
        :param kwargs: keyword arguments representing the downloader's configuration
        """

        self.protocol = protocol.lower()

        max_concurrent = kwargs.pop('max_concurrent', None)
        if not (max_concurrent > 0 or max_concurrent is None):
            raise AttributeError('max_concurrent must be greater than 0')

        self.max_concurrent = max_concurrent

        # the open-ended nature of this will be solved with documentation
        self.__dict__.update(kwargs)

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

