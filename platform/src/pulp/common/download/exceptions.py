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

    It's considered best practices not to raise or handle instances of this
    class, but of the derived classes below.

    :ivar report: pulp.common.download.report.DownloadReport instance
    """

    def __init__(self, report):
        self.report = report

# client-side problems ---------------------------------------------------------

class PulpDownloadClientException(PulpDownloaderException):
    """
    Base class for client-side downloader problems.
    """

# specific derived exceptions

class UnsupportedProtocol(PulpDownloadClientException):
    """
    Raised when the request URL is for a protocol not supported by the downloader.
    """


class MalformedRequest(PulpDownloadClientException):
    """
    Raised when the request cannot be parsed by the downloader.
    """


class ReadError(PulpDownloadClientException):
    """
    Raised when the downloader cannot read the response sent by the remote server.
    """

# remote server problems -------------------------------------------------------

class PulpRemoteServerException(PulpDownloaderException):
    """
    Base class for remote server-side downloader problems.
    """

# specific derived exceptions

class FileNotFound(PulpRemoteServerException):
    """
    Raised when the remote server cannot find the request file.
    """


class PartialFile(PulpRemoteServerException):
    """
    Raised when the remote server only returns part of the requested file.
    """


class RemoteServerResolutionError(PulpRemoteServerException):
    """
    Raised when the remote server's name cannot be resolved.
    (DNS lookup failure)
    """


class ServerTimedOut(PulpRemoteServerException):
    """
    Raised when the connection to the remote server times out.
    """


class AuthorizationFailure(PulpRemoteServerException):
    """
    Raised when the remote server denies access to the requested file due to
    invalid or missing credentials.
    """


class TooManyRedirects(PulpRemoteServerException):
    """
    Raised when the remote server tries to redirect the request too many times.
    """


class UnknownResponse(PulpRemoteServerException):
    """
    Raised when the remote server sends a response that cannot be parsed.
    """


class RemoteServerError(PulpRemoteServerException):
    """
    Raised when there is an internal remote server error.
    """

# proxy server problems --------------------------------------------------------

class PulpProxyException(PulpDownloaderException):
    """
    Base class for proxy server problems.
    """

# specific derived exceptions

class ProxyResolutionError(PulpProxyException):
    """
    Raised when the proxy server's name cannot be resolved.
    (DNS lookup failure)
    """


class ProxyConnectionTimedOut(PulpProxyException):
    """
    Raised when the connection to the proxy server times out.
    """


class ProxyAuthorizationFailure(PulpProxyException):
    """
    Raised when the connection to the proxy server cannot be established due to
    invalid or missing credentials.
    """

# ssl problems -----------------------------------------------------------------

class PulpSSLException(PulpDownloaderException):
    """
    Base class for SSL problems.
    """

# specific derived exceptions

class ServerSSLVerificationFailure(PulpSSLException):
    """
    Raised with the server's ssl certificate fails verification.
    """


class ClientSSLAuthorizationFailure(PulpSSLException):
    """
    Raised when the client's ssl certificate is rejected by the server.
    """

