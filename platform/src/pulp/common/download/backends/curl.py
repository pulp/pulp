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

import os

import pycurl

from pulp.common.download.backends.base import DownloadBackend


SELECT_TIMEOUT = 1.0


class HTTPCurlDownloadBackend(DownloadBackend):

    def download(self, request_list):

        multi_handle = pycurl.CurlMulti()

        requests = []
        files = []

        for request in request_list:

            file_handle = open(request.file_path, 'wb')

            files.append(request.file_path)

            easy_handle = pycurl.Curl()
            easy_handle.setopt(pycurl.URL, request.url)
            easy_handle.setopt(pycurl.WRITEFUNCTION, file_handle.write)

            req = (request.url, file_handle, easy_handle)
            multi_handle.add_handle(req[2])
            requests.append(req)

        num_handles = len(requests)

        while num_handles:
            ret = multi_handle.select(SELECT_TIMEOUT)
            if ret == -1:
                continue
            while True:
                ret, num_handles = multi_handle.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

        for req in requests:
            req[1].close()

        return files

