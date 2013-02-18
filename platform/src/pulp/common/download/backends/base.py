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
    """
    Abstract backend base class for downloader implementations. This class
    provides the base APIs required of any concrete downloader class.

    Backend implementations are expected to override the ``download`` method.
    They can (optionally) download any other methods, but they are not required.

    :ivar config: downloader configuration
    :ivar event_listener: event listener providing life-cycle callbacks.
    :ivar is_cancelled: boolean showing if the cancel method has been called.
    """

    def __init__(self, config, event_listener=None):
        """
        :param config: configuration for this backend
        :type config: pulp.common.download.config.DownloaderConfig
        :param event_listener: event listener coupled to this backend
        :type event_listener: pulp.common.download.listener.DownloadEventListener
        """
        self.config = config
        self.event_listener = event_listener or DownloadEventListener()
        self.is_cancelled = False

    # download api -------------------------------------------------------------

    def download(self, request_list):
        """
        Download the files represented by the download requests in the provided
        request list.

        :param request_list: list of download requests
        :type request_list: list of pulp.common.download.request.DownloadRequest
        :return: list of download reports corresponding the the download requests
        :rtype: list of pulp.common.download.report.DownloadReport
        """
        raise NotImplementedError()

    def cancel(self):
        """
        Set the boolean is_cancelled flag to True.

        NOTE: it is up the ``download`` implementation to honor this flag.
        """
        self.is_cancelled = True

    # events api ---------------------------------------------------------------

    def fire_batch_started(self, report_list):
        """
        Fire the ``batch_started`` event using the list of download reports
        provided.

        :param report_list: list of download reports
        :type report_list: list of pulp.common.download.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.batch_started, report_list)

    def fire_batch_finished(self, report_list):
        """
        Fire the ``batch_finished`` event using the list of download reports
        provided.

        :param report_list: list of download reports
        :type report_list: list of pulp.common.download.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.batch_finished, report_list)

    def fire_download_started(self, report):
        """
        Fire the ``download_started`` event using the download report provided.

        :param report: download reports
        :type report: pulp.common.download.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_started, report)

    def fire_download_progress(self, report):
        """
        Fire the ``download_progress`` event using the download report provided.

        :param report: download reports
        :type report: pulp.common.download.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_progress, report)

    def fire_download_succeeded(self, report):
        """
        Fire the ``download_succeeded`` event using the download report provided.

        :param report: download reports
        :type report: pulp.common.download.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_succeeded, report)

    def fire_download_failed(self, report):
        """
        Fire the ``download_failed`` event using the download report provided.

        :param report: download reports
        :type report: pulp.common.download.report.DownloadReport
        """
        self._fire_event_to_listener(self.event_listener.download_failed, report)

    # events utility methods ---------------------------------------------------

    def _fire_event_to_listener(self, event_listener_callback, *args, **kwargs):
        try:
            event_listener_callback(*args, **kwargs)
        except Exception, e:
            _LOG.exception(e)
