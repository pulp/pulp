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


BUFFER_SIZE = 1024
MAX_CONCURRENT = 8


class DumbAssTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):
        total_bytes_written = 0 # literally to keep pycharm from complaining about an unused 'i'
        files = []

        for url in url_list:
            file_name = utils.file_name_from_url(url)
            file_path = os.path.abspath(os.path.join(self.storage_dir, file_name))
            files.append(file_path)

            for i in fetch_url_generator(url, file_path, BUFFER_SIZE):
                total_bytes_written += i

        return files


class BadAssTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):
        files = []
        generators = []

        for url in url_list:
            file_name = utils.file_name_from_url(url)
            file_path = os.path.abspath(os.path.join(self.storage_dir, file_name))
            files.append(file_name)

            generators.append(fetch_url_generator(url, file_path, BUFFER_SIZE))

        loop = DownloadGeneratorLoop(generators, MAX_CONCURRENT)
        loop.loop()

        return files


class DownloadGeneratorLoop(object):

    class DoublyLinkedGenerators(object):

        @classmethod
        def from_iterable(cls, iterable):
            head_node = None
            previous_node = None
            for i in iterable:
                node = cls(i)
                node.previous_node = previous_node
                if previous_node is not None:
                    previous_node.next_node = node
                if head_node is None:
                    head_node = node
                previous_node = node
            return head_node

        def __init__(self, generator=None):
            self.generator = generator
            self.previous_node = None
            self.next_node = None

        def remove(self):
            if self.previous_node is not None:
                self.previous_node.next_node = self.next_node
            if self.next_node is not None:
                self.next_node.previous_node = self.previous_node


    def __init__(self, generator_list, max_concurrency=None):
        assert max_concurrency is None or max_concurrency > 0
        self.generator_list = generator_list
        self.max_concurrency = max_concurrency or len(generator_list)

    def loop(self):
        head = self.DoublyLinkedGenerators.from_iterable(self.generator_list)
        current = head
        count = 0

        while head is not None:
            count += 1

            try:
                current.generator.next()

            except StopIteration:
                current.remove()
                if current is head:
                    head = head.next_node

            current = current.next_node

            if current is None or count == self.max_concurrency:
                current = head
                count = 0

# producer/consumer generators -------------------------------------------------

def network_content_generator(url, buffer_size=None):
    network_buffer = urllib2.urlopen(url)
    info = network_buffer.info()
    content_length = int(info['content-length'])

    while content_length:
        body = network_buffer.read(buffer_size)
        content_length -= len(body)
        yield body


def fetch_url_generator(url, file_path, buffer_size=None):
    file_handle = open(file_path, 'w')

    for part in network_content_generator(url, buffer_size):
        if part:
            file_handle.write(part)
        yield len(part)


