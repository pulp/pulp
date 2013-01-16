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
import urllib2


import utils
from backend import TransportBackend


class DumbAssTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):
        total_bytes_written = 0 # literally to keep pycharm from complaining about an unused 'i'
        files = []

        for url in url_list:
            file_name = utils.file_name_from_url(url)
            file_path = os.path.abspath(os.path.join(self.storage_dir, file_name))
            files.append(file_path)

            for i in fetch_url_generator(url, file_path):
                total_bytes_written += i

        return files

# producer/consumer generators -------------------------------------------------

def network_content_generator(url):
    network_buffer = urllib2.urlopen(url)
    body = network_buffer.read()
    while body:
        yield body
        body = network_buffer.read()


def fetch_url_generator(url, file_path):
    file_handle = open(file_path, 'w')
    for part in network_content_generator(url):
        file_handle.write(part)
        yield len(part)


def fetch_multiples_url_generator(url_list):
    pass

