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


class DownloadBackend(object):

    def __init__(self, request_list, max_concurrent=None):
        assert max_concurrent is None or max_concurrent > 0

        self.request_list = request_list
        self.max_concurrent = max_concurrent or len(request_list)

    # batch downloads api

    def download_all(self):
        raise NotImplementedError()

    def cancel_all(self):
        raise NotImplementedError()

    # individual download management

    def add_request(self, request):
        raise NotImplementedError()

    def remove_request(self, request):
        raise NotImplementedError()

    def cancel_request(self, request):
        raise NotImplementedError()

