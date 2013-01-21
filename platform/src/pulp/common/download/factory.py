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

from gettext import gettext as _

from pulp.common.download.backends.base import DownloadBackend
from pulp.common.download.backends.curl import HTTPCurlDownloadBackend

# download backends and management ---------------------------------------------

class NoBackendForProtocol(Exception):

    def __init__(self, protocol):
        Exception.__init__(self, protocol)
        self.protocol = protocol

    def __str__(self):
        return _('No downloader backend found for: %(p)s') % {'p': self.protocol}


_BACKENDS = {
    'http': HTTPCurlDownloadBackend,
    'https': HTTPCurlDownloadBackend,
}


def set_backend(protocol, backend):
    global _BACKENDS
    assert isinstance(backend, DownloadBackend)
    _BACKENDS[protocol] = backend


def clear_backend(protocol):
    global _BACKENDS
    return _BACKENDS.pop(protocol, None)

# downloader factory methods ---------------------------------------------------

def _get_downloader_class(protocol):
    downloader_class = _BACKENDS.get(protocol, None)
    if downloader_class is None:
        raise NoBackendForProtocol(protocol)
    return downloader_class


def http_downloader(max_concurrent=None, event_listener=None):
    downloader_class = _get_downloader_class('http')
    downloader = downloader_class(max_concurrent, event_listener)
    return downloader


def https_downloader(max_concurrent=None, event_listener=None):
    downloader_class = _get_downloader_class('https')
    downloader = downloader_class(max_concurrent, event_listener)
    return downloader

