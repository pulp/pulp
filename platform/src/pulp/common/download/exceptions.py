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

"""
Exception classes thrown by downloader implementations under error conditions.
"""


class PulpDownloaderException(Exception):
    pass

# client-side problems ---------------------------------------------------------

class PulpDownloadClientException(PulpDownloaderException):
    pass

# specific derived exceptions

class UnsupportedProtocol(PulpDownloadClientException):
    pass


class MalformedRequest(PulpDownloadClientException):
    pass


class ReadError(PulpDownloadClientException):
    pass


class HomieTheClownSaysTryAgain(PulpDownloadClientException):
    pass

# remote server problems -------------------------------------------------------

class PulpRemoteServerException(PulpDownloaderException):
    pass

# specific derived exceptions

class FileNotFound(PulpRemoteServerException):
    pass


class PartialFile(PulpRemoteServerException):
    pass


class RemoteServerResolutionError(PulpRemoteServerException):
    pass


class AuthorizationFailure(PulpRemoteServerException):
    pass


class TooManyRedirects(PulpRemoteServerException):
    pass


class UnknownResponse(PulpRemoteServerException):
    pass


class RemoteServerError(PulpRemoteServerException):
    pass

# proxy server problems --------------------------------------------------------

class PulpProxyException(Exception):
    pass

# specific derived exceptions

class ProxyResolutionError(PulpProxyException):
    pass


class ProxyConnectionTimedOut(PulpProxyException):
    pass


class ProxyAuthorizationFailure(PulpProxyException):
    pass

# ssl problems -----------------------------------------------------------------

class PulpSSLException(Exception):
    pass

# specific derived exceptions

class ServerSSLVerificationFailure(PulpSSLException):
    pass


class ClientSSLAuthorizationFailure(PulpSSLException):
    pass

