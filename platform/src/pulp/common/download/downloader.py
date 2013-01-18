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

from pulp.common.download.backends.base import DownloadBackend
from pulp.common.download.backends.curl import CurlDownloadBackend
from pulp.common.download.backends.local import LocalCopyDownloadBackend
from pulp.common.download.requests.base import DownloadRequest

# download backends and management ---------------------------------------------

_BACKENDS = {
    'http': CurlDownloadBackend,
    'https': CurlDownloadBackend,
    'ftp': CurlDownloadBackend,
    'file': LocalCopyDownloadBackend,
}


def set_backend(protocol, backend):
    global _BACKENDS
    assert isinstance(backend, DownloadBackend)
    _BACKENDS[protocol] = backend


def clear_backend(protocol):
    global _BACKENDS
    if protocol not in _BACKENDS:
        return
    del _BACKENDS[protocol]

# downloads --------------------------------------------------------------------

