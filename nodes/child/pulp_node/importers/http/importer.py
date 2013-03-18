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

from pulp.plugins.importer import Importer
from pulp.common.download import factory
from pulp.common.download.config import DownloaderConfig

from pulp_node import constants
from pulp_node.progress import RepositoryProgress
from pulp_node.importers.reports import ProgressListener
from pulp_node.importers.strategies import find_strategy


log = getLogger(__name__)

# download concurrency
MAX_CONCURRENCY = 20


# --- i18n ------------------------------------------------------------------------------

PROPERTY_MISSING = _('Missing required configuration property: %(p)s')
STRATEGY_UNSUPPORTED = _('Strategy %(s)s not supported')


# --- plugin loading --------------------------------------------------------------------


DEFAULT_CONFIGURATION = {
    constants.STRATEGY_KEYWORD: constants.DEFAULT_STRATEGY,
}


def entry_point():
    """
    Entry point that pulp platform uses to load the importer.
    :return: importer class and its configuration
    :rtype:  Importer, {}
    """
    return NodesHttpImporter, DEFAULT_CONFIGURATION


# --- plugin ----------------------------------------------------------------------------


class NodesHttpImporter(Importer):
    """
    The nodes importer is used to synchronize repository content.
    """

    @classmethod
    def metadata(cls):
        return {
            'id' : constants.HTTP_IMPORTER,
            'display_name' : 'Pulp Nodes HTTP Importer',
            'types' : ['node', 'repository']
        }

    def __init__(self):
        self.strategy = None

    def validate_config(self, repo, config, related_repos):
        """
        Validate the configuration.
        :param repo: A repository object.
        :type repo: pulp.plugins.model.Repository
        :param config: The importer configuration to validate.
        :param config: pulp.plugins.config.PluginCallConfiguration
        :param related_repos: List of other repositories associated with this
            importer type.  Each item is: pulp.server.plugins.model.RelatedRepository
        :type related_repos: list
        :return: A tuple of: (is_valid, reason):
            is_valid : (bool) True when config if deemed valid.
            reason: (str) The reason of the validation failure.
        :rtype: tuple
        """
        errors = []

        for key in (constants.MANIFEST_URL_KEYWORD,
                    constants.PROTOCOL_KEYWORD,
                    constants.STRATEGY_KEYWORD):
            value = config.get(key)
            if not value:
                msg = PROPERTY_MISSING % dict(p=key)
                errors.append(msg)

        strategy = config.get(constants.STRATEGY_KEYWORD)
        if strategy not in constants.STRATEGIES:
            msg = STRATEGY_UNSUPPORTED % strategy
            errors.append(msg)

        valid = not bool(errors)
        return (valid, errors)

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
        try:
            downloader = self._downloader(config)
            strategy_name = config.get(constants.STRATEGY_KEYWORD)
            strategy_class = find_strategy(strategy_name)
            listener = ProgressListener(conduit)
            progress = RepositoryProgress(repo.id, listener)
            self.strategy = strategy_class(conduit, config, downloader, progress)
            progress.begin_importing()
            report = self.strategy.synchronize(repo.id)
            details = dict(report=report.dict())
        except Exception, e:
            msg = repr(e)
            log.exception(repo.id)
            details = dict(exception=msg)
        report = conduit.build_success_report({}, details)
        return report

    def _downloader(self, config):
        """
        Get a configured downloader.
        The integration between the importer configuration and the
        download package happens here.  The https downloader may be
        used for both http and https so always chosen for simplicity.
        :param config: The importer configuration.
        :param config: pulp.plugins.config.PluginCallConfiguration
        :return: A configured downloader
        :rtype: pulp.common.download.downloaders.base.PulpDownloader
        """
        ssl = config.get(constants.SSL_KEYWORD, {})
        conf = DownloaderConfig(
            'https',
            max_concurrent=MAX_CONCURRENCY,
            ssl_ca_cert_path=self._safe_str(ssl.get(constants.CA_CERT_KEYWORD)),
            ssl_client_cert_path=self._safe_str(ssl.get(constants.CLIENT_CERT_KEYWORD)),
            ssl_verify_host=0,
            ssl_verify_peer=0)
        downloader = factory.get_downloader(conf)
        return downloader

    def _safe_str(self, s):
        if s:
            return str(s)
        else:
            return s

