# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from logging import getLogger
from gettext import gettext as _
from threading import Event

from nectar.downloaders.threaded import HTTPThreadedDownloader as Downloader

from pulp.server.compat import json
from pulp.plugins.importer import Importer
from pulp.plugins.util.nectar_config import importer_config_to_nectar_config

from pulp_node import constants
from pulp_node.error import CaughtException
from pulp_node.reports import RepositoryProgress
from pulp_node.importers.reports import SummaryReport, ProgressListener
from pulp_node.importers.strategies import find_strategy, Request


log = getLogger(__name__)


# --- constants -------------------------------------------------------------------------

PROPERTY_MISSING = _('Missing required configuration property: %(p)s')
STRATEGY_UNSUPPORTED = _('Strategy %(s)s not supported')

CONFIGURATION_PATH = '/etc/pulp/server/plugins.conf.d/nodes/importer/http.conf'


# --- plugin loading --------------------------------------------------------------------

def entry_point():
    """
    Entry point that pulp platform uses to load the importer.
    :return: importer class and its configuration
    :rtype:  Importer, dict
    """
    with open(CONFIGURATION_PATH) as fp:
        return NodesHttpImporter, json.load(fp)


# --- plugin ----------------------------------------------------------------------------


class NodesHttpImporter(Importer):
    """
    The nodes importer is used to synchronize repository content.
    :ivar cancel_event: Event used to signal that the last method called has been
        canceled by another thread.
    :type cancel_event: Event
    """

    @classmethod
    def metadata(cls):
        return {
            'id': constants.HTTP_IMPORTER,
            'display_name': 'Pulp Nodes HTTP Importer',
            'types': ['node', 'repository']
        }

    def __init__(self):
        self.cancel_event = Event()

    def validate_config(self, repo, config):
        """
        Validate the configuration.
        :param repo: A repository object.
        :type repo: pulp.plugins.model.Repository
        :param config: The importer configuration to validate.
        :param config: pulp.plugins.config.PluginCallConfiguration

        :return: A tuple of: (is_valid, reason):
            is_valid : (bool) True when config if deemed valid.
            reason: (str) The reason of the validation failure.
        :rtype: tuple
        """
        errors = []

        for key in (constants.MANIFEST_URL_KEYWORD,
                    constants.STRATEGY_KEYWORD):
            value = config.get(key)
            if not value:
                msg = PROPERTY_MISSING % dict(p=key)
                errors.append(msg)

        strategy = config.get(constants.STRATEGY_KEYWORD, constants.DEFAULT_STRATEGY)
        if strategy not in constants.STRATEGIES:
            msg = STRATEGY_UNSUPPORTED % dict(s=strategy)
            errors.append(msg)

        valid = not bool(errors)
        return valid, errors

    def sync_repo(self, repo, conduit, config):
        """
        Synchronize the content of the specified repository.
        The implementation is delegated to the strategy object which
        is selected based on the 'strategy' option passed specified in
        the configuration.
        :param repo: A repository object.
        :type repo: pulp.plugins.model.Repository
        :param conduit: Provides access to relevant Pulp functionality.
        :param config: pulp.server.conduits.repo_sync.RepoSyncConduit
        :return: A report describing the result.
        :rtype: pulp.server.plugins.model.SyncReport
        """
        summary_report = SummaryReport()
        downloader = None

        try:
            downloader = self._downloader(config)
            strategy_name = config.get(constants.STRATEGY_KEYWORD, constants.DEFAULT_STRATEGY)
            progress_report = RepositoryProgress(repo.id, ProgressListener(conduit))
            request = Request(
                self.cancel_event,
                conduit=conduit,
                config=config,
                downloader=downloader,
                progress=progress_report,
                summary=summary_report,
                repo=repo)
            strategy = find_strategy(strategy_name)()
            strategy.synchronize(request)
        except Exception, e:
            summary_report.errors.append(CaughtException(e, repo.id))
        finally:
            if downloader is not None:
                downloader.config.finalize()

        summary_report.errors.update(repo_id=repo.id)
        report = conduit.build_success_report({}, summary_report.dict())
        return report

    def cancel_sync_repo(self, call_request, call_report):
        """
        Cancel an in-progress repository synchronization.
        :param call_request:
        :param call_report:
        """
        self.cancel_event.set()

    def _downloader(self, config):
        """
        Get a configured downloader.
        The integration between the importer configuration and the
        download package happens here.  The https downloader may be
        used for both http and https so always chosen for simplicity.
        :param config: The importer configuration.
        :param config: pulp.plugins.config.PluginCallConfiguration
        :return: A configured downloader
        :rtype: nectar.downloaders.base.Downloader
        """
        configuration = importer_config_to_nectar_config(config.flatten())
        downloader = Downloader(configuration)
        return downloader
