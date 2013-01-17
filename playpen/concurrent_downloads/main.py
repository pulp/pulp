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

import datetime
import sys
import tempfile

import urls
from backend_curl import CurlTransportBackend
from backend_eventlets import EventletEmbeddedTransportBackend, EventletTransportBackend
from backend_futures import FuturesProcessPoolTransportBackend, FuturesThreadPoolTransportBackend
from backend_jconnor import DumbAssTransportBackend, BadAssTransportBackend


BACKENDS = {
    'pycurl': CurlTransportBackend,
    'eventlets-embedded': EventletEmbeddedTransportBackend,
    'eventlets-pymagic': EventletTransportBackend,
    'futures-processes': FuturesProcessPoolTransportBackend,
    'futures-threads': FuturesThreadPoolTransportBackend,
    'jconnor-dumbass': DumbAssTransportBackend,
    'jconnor-badass': BadAssTransportBackend,
    }


def main():

    #file_urls = urls.abrt_file_urls()
    #print 'Downloading %d files from %s' % (len(file_urls), urls.ABRT_URL)

    #file_urls = urls.epel_6_file_urls()
    #print 'Downloading %d files from %s' % (len(file_urls), urls.EPEL_6_URL)

    file_urls = urls.fedora_18_iso_url()
    print 'Downloading %d files from %s' % (len(file_urls), urls.FEDORA_18_ISO)

    available_backends = set(BACKENDS.keys())
    requested_backends = set(sys.argv[1:])

    if not requested_backends:
        backends = available_backends
    else:
        backends = requested_backends.intersection(available_backends)

    for name, transport_backend_class in dict((k, BACKENDS[k]) for k in backends).items():
        prefix = name + '-'
        storage_dir = tempfile.mkdtemp(prefix=prefix)
        transport_backend = transport_backend_class(storage_dir)

        start = datetime.datetime.now()
        transport_backend.fetch_multiple(file_urls)
        run_time = datetime.datetime.now() - start

        print '%-20s %s' % (name + ':', str(run_time))


if __name__ == '__main__':
    main()
