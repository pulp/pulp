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

import urllib2

from concurrent import futures

import utils
from backend import TransportBackend


class FuturesThreadPoolTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):

        executor = futures.ThreadPoolExecutor(5)
        futures_list = [executor.submit(utils.fetch, url, self.storage_dir) for url in url_list]

        return [f.result() for f in futures.as_completed(futures_list)]


class FuturesProcessPoolTransportBackend(TransportBackend):

    def fetch_multiple(self, url_list):

        executor = futures.ProcessPoolExecutor(5)
        futures_list = [executor.submit(utils.fetch, url, self.storage_dir) for url in url_list]

        return [f.result() for f in futures.as_completed(futures_list)]

