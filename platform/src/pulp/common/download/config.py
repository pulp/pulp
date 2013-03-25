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

     * max_concurrent:       maximum number of downloads to run concurrently
     * basic_auth_username:  http basic auth username (basic_auth_password must also be
                             provided)
     * basic_auth_password:  http basic auth password (basic_auth_username must also be
                             provided)
     * ssl_ca_cert:          certificate authority cert for secure connections (https
                             protocol only)
     * ssl_ca_cert_path:     path to a ssl ca cert (incompatible with ssl_ca_cert)
     * ssl_client_cert:      client certificate for secure connections (https protocol
                             only)
     * ssl_client_cert_path: path to a ssl client cert (incompatible with ssl_client_cert)
     * ssl_client_key:       client private key for secure connections (https protocol
                             only)
     * ssl_client_key_path:  path to a ssl client key (incompatible with ssl_client_key)
     * ssl_verify_host:      integer telling the downloader what level of verificaiton to
                             use. 0 means no verificaiton
     * ssl_verify_peer:      integer telling the downloader what level of verificaiton to
                             use. 0 means no verificaiton
     * proxy_url:            A string representing the URL of a proxy server that should
                             be used while retrieving content. It should be of the form
                             <scheme>://<hostname>/ where the scheme is http or https.
     * proxy_port:           The port on the proxy server to connect to. This should be
                             an integer value.
     * proxy_username:       The username to use when authenticating with the proxy server
     * proxy_password:       The password to use when authenticating with the proxy server
     * max_speed:            The maximum speed to be used during downloads. This should be an integer
                             value, and should be specified in units of bytes per second.
    """

    def __init__(self, **kwargs):
        """
        :param kwargs:   keyword arguments representing the downloader's configuration.
                         See the DownloaderConfig's docblock for a list of supported
                         options.
        :type  kwargs:   dict
        """
        max_concurrent = kwargs.pop('max_concurrent', None)
        if not (max_concurrent > 0 or max_concurrent is None):
            raise AttributeError('max_concurrent must be greater than 0')

        self.max_concurrent = max_concurrent

        # the open-ended nature of this will be solved with documentation
        self.__dict__.update(kwargs)

    def __getattr__(self, item):
        """
        This allows us to retrieve configuration parameters from this object with getattr()
        or by accessing the attributes by name.
        """
        return self.__dict__.get(item, None)
