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

import logging

from pulp.common.download.listener import DownloadEventListener


_LOG = logging.getLogger(__name__)


class DownloadBackend(object):

    def __init__(self, config, event_listener=None):
        self.config = config
        self.event_listener = event_listener or DownloadEventListener()
        self.is_cancelled = False

    # download api -------------------------------------------------------------

    def download(self, request_list):
        raise NotImplementedError()

    def cancel(self):
        self.is_cancelled = True

    # events api ---------------------------------------------------------------

    def fire_batch_started(self, report_list):
        self._fire_event_to_listener(self.event_listener.batch_started, report_list)

    def fire_batch_finished(self, report_list):
        self._fire_event_to_listener(self.event_listener.batch_finished, report_list)

    def fire_download_started(self, report):
        self._fire_event_to_listener(self.event_listener.download_started, report)

    def fire_download_progress(self, report):
        self._fire_event_to_listener(self.event_listener.download_progress, report)

    def fire_download_succeeded(self, report):
        self._fire_event_to_listener(self.event_listener.download_succeeded, report)

    def fire_download_failed(self, report):
        self._fire_event_to_listener(self.event_listener.download_failed, report)

    def _fire_event_to_listener(self, event_listener_callback, *args, **kwargs):
        try:
            event_listener_callback(*args, **kwargs)
        except Exception, e:
            _LOG.exception(e)

