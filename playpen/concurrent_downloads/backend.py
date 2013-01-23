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


class TransportBackend(object):
    """
    Abstract base transit backend class providing the transit API
    """

    def __init__(self, storage_dir):
        assert os.access(storage_dir, os.R_OK | os.W_OK)
        self.storage_dir = storage_dir

    def fetch_multiple(self, url_list):
        raise NotImplementedError()

    def fetch_single(self, url):
        return self.fetch_multiple([url])

    def cancel_fetch(self):
        raise NotImplementedError()

