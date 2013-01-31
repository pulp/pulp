# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

from pulp_citrus.importer.strategies import find_strategy, StrategyUnsupported

log = getLogger(__name__)


class CitrusHttpImporter(Importer):
    """
    The citrus importer is used to synchronize repository content.
    """

    @classmethod
    def metadata(cls):
        return {
            'id':'citrus_http_importer',
            'display_name':'Pulp Citrus HTTP Importer',
            'types':['repository',]
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
        msg = _('Missing required configuration property: %(p)s')
        for key in ('manifest_url', 'protocol'):
            value = config.get(key)
            if not value:
                return (False, msg % dict(p=key))
        return (True, None)

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
            strategy_name = config.get('strategy')
            strategy_class = find_strategy(strategy_name)
            self.strategy = strategy_class(conduit, config, downloader)
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
        :rtype: pulp.common.download.backends.base.DownloadBackend
        """
        ssl = config.get('ssl', {})
        conf = DownloaderConfig(
            'https',
            ssl_ca_cert_path=str(ssl.get('ca_cert', '')),
            ssl_client_cert_path=str(ssl.get('client_cert', '')))
        downloader = factory.get_downloader(conf)
        return downloader

