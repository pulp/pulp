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

from pulp.common.download.listener import DownloadEventListener


class DownloadBackend(object):

    def __init__(self, config, event_listener=None):
        self.config = config
        self.event_listener = event_listener or DownloadEventListener()
        self.is_cancelled = False

    def download(self, request_list):
        raise NotImplementedError()

    def cancel(self):
        self.is_cancelled = True

