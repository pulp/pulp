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
import tempfile

import urls
from backend_curl import CurlTransportBackend
from backend_eventlets import EventletTransportBackend


BACKENDS = {
    'pycurl': CurlTransportBackend,
    'eventlets': EventletTransportBackend,
    }


def main():

    file_urls = urls.abrt_file_urls()

    print 'Downloading %d files from %s' % (len(file_urls), urls.ABRT_URL)

    for name, transport_backend_class in BACKENDS.items():
        prefix = name + '-'
        storage_dir = tempfile.mkdtemp(prefix=prefix)
        transport_backend = transport_backend_class(storage_dir)

        start = datetime.datetime.now()
        transport_backend.fetch_multiple(file_urls)
        run_time = datetime.datetime.now() - start

        print '%-11s %s' % (name + ':', str(run_time))


if __name__ == '__main__':
    main()
