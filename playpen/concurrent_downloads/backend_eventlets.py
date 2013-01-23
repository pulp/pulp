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

import functools

import eventlet
from eventlet.green import urllib2

import utils
from backend import TransportBackend


class EventletTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):
        pool = eventlet.GreenPool()
        fetch = functools.partial(utils.fetch, storage_dir=self.storage_dir)
        return [file_name for file_name in pool.imap(fetch, url_list)]


class EventletEmbeddedTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):

        def embedded_fetch(url):
            name = utils.file_name_from_url(url)
            path, handle = utils.file_path_and_handle(self.storage_dir, name)

            body = urllib2.urlopen(url).read()

            handle.write(body)
            handle.close()

            return name

        pool = eventlet.GreenPool()
        return [file_name for file_name in pool.imap(embedded_fetch, url_list)]

