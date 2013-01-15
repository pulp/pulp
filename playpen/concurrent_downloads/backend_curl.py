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

from cStringIO import StringIO

import pycurl

import utils
from backend import TransportBackend


class CurlTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):

        curl_multi = pycurl.CurlMulti()

        files = []

        for url in url_list:

            file_name = utils.file_name_from_url(url)
            file_path, file_handle = utils.file_path_and_handle(self.storage_dir, file_name)

            files.append(file_path)

            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.WRITEFUNCTION, file_handle.write)
            curl.setopt(pycurl.HEADERFUNCTION, StringIO().write)

            curl_multi.add_handle(curl)

        num_handles = None

        while True:
            ret, num_handles = curl_multi.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

        while num_handles:
            ret = curl_multi.select(1.0)
            if ret == -1:
                continue
            while True:
                ret, num_handles = curl_multi.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

        return files


