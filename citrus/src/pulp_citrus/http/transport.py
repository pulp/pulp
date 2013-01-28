# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


# PLACEHOLDER FOR HTTP/HTTPS TRANSPORT

import os
import urllib

class HttpTransport:

    def __init__(self):
        self.cancelled = False

    def download(self, requests):
        for request in requests:
            try:
                self._download(request)
                request.succeeded()
                if self.cancelled:
                    break
            except Exception, e:
                request.failed(e)

    def cancel(self):
        self.cancelled = True

    def _download(self, request):
        url = request.details()['url']
        fp_in = urllib.urlopen(url)
        try:
            storage_path = request.local_unit.storage_path
            self._mkdir(storage_path)
            fp_out = open(storage_path, 'w+')
            try:
                while True:
                    bfr = fp_in.read(0x100000)
                    if bfr:
                        fp_out.write(bfr)
                    else:
                        break
            finally:
                fp_out.close()
        finally:
            fp_in.close()

    def _mkdir(self, file_path):
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)