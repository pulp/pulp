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
    """
    General Pulp downloader exception base class.
    """
    pass

# client-side problems ---------------------------------------------------------

class PulpDownloadClientException(PulpDownloaderException):
    """
    Base class for client-side downloader problems.
    """
    pass

# specific derived exceptions

class UnsupportedProtocol(PulpDownloadClientException):
    """
    Raised when the request URL is for a protocol not supported by the downloader.
    """
    pass


class MalformedRequest(PulpDownloadClientException):
    """
    Raised when the request cannot be parsed by the downloader.
    """
    pass


class ReadError(PulpDownloadClientException):
    """
    Raised when the downloader cannot read the response sent by the remote server.
    """
    pass


class HomeyDClownSaysTryAgain(PulpDownloadClientException):
    """
    Homey D. Clown
    don't mess around
    even though the man
    try to keep 'im down
    One day Homey will
    break all the chains
    then he'll fly away
    but until that day
    Homey don't play
    http://www.youtube.com/watch?v=_QhuBIkPXn0
    """
    pass

# remote server problems -------------------------------------------------------

class PulpRemoteServerException(PulpDownloaderException):
    """
    Base class for remote server-side downloader problems.
    """
    pass

# specific derived exceptions

class FileNotFound(PulpRemoteServerException):
    """
    Raised when the remote server cannot find the request file.
    """
    pass


class PartialFile(PulpRemoteServerException):
    """
    Raised when the remote server only returns part of the requested file.
    """
    pass


class RemoteServerResolutionError(PulpRemoteServerException):
    """
    Raised when the remote server's name cannot be resolved.
    (DNS lookup failure)
    """
    pass


class ServerTimedOut(PulpRemoteServerException):
    """
    Raised when the connection to the remote server times out.
    """
    pass


class AuthorizationFailure(PulpRemoteServerException):
    """
    Raised when the remote server denies access to the requested file due to
    invalid or missing credentials.
    """
    pass


class TooManyRedirects(PulpRemoteServerException):
    """
    Raised when the remote server tries to redirect the request too many times.
    """
    pass


class UnknownResponse(PulpRemoteServerException):
    """
    Raised when the remote server sends a response that cannot be parsed.
    """
    pass


class RemoteServerError(PulpRemoteServerException):
    """
    Raised when there is an internal remote server error.
    """
    pass

# proxy server problems --------------------------------------------------------

class PulpProxyException(PulpDownloaderException):
    """
    Base class for proxy server problems.
    """
    pass

# specific derived exceptions

class ProxyResolutionError(PulpProxyException):
    """
    Raised when the proxy server's name cannot be resolved.
    (DNS lookup failure)
    """
    pass


class ProxyConnectionTimedOut(PulpProxyException):
    """
    Raised when the connection to the proxy server times out.
    """
    pass


class ProxyAuthorizationFailure(PulpProxyException):
    """
    Raised when the connection to the proxy server cannot be established due to
    invalid or missing credentials.
    """
    pass

# ssl problems -----------------------------------------------------------------

class PulpSSLException(PulpDownloaderException):
    """
    Base class for SSL problems.
    """
    pass

# specific derived exceptions

class ServerSSLVerificationFailure(PulpSSLException):
    """
    Raised with the server's ssl certificate fails verification.
    """
    pass


class ClientSSLAuthorizationFailure(PulpSSLException):
    """
    Raised when the client's ssl certificate is rejected by the server.
    """
    pass

