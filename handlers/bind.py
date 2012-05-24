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
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
from iniparse import INIConfig
from pulp.gc_client.agent.lib.handler import BindHandler
from pulp.gc_client.agent.lib.report import BindReport, CleanReport
from pulp.gc_client.lib import repolib
from logging import getLogger, Logger

log = getLogger(__name__)


# TODO: Pass-in instaed of hard code
class ConsumerConfig(INIConfig):
    def __init__(self):
        path = '/etc/pulp/consumer/v2_consumer.conf'
        fp = open(path)
        try:
            INIConfig.__init__(self, fp)
        finally:
            fp.close()


class RepoHandler(BindHandler):
    """
    A yum repository bind request handler.
    Manages the /etc/yum.repos.d/pulp.repo based on bind requests.
    """

    def bind(self, definitions):
        """
        Bind a repository.
        @param definitions: A list of bind definitions.
        Definition:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @type definitions: list
        @return: A bind report.
        @rtype: L{BindReport}
        """
        log.info('bind: %s', definitions)
        report = BindReport()
        cfg = ConsumerConfig()
        for definition in definitions:
            details = definition['details']
            repository = definition['repository']
            repoid = repository['id']
            urls = self.__urls(details)
            repolib.bind(
                cfg.filesystem.repo_file,
                os.path.join(cfg.filesystem.mirror_list_dir, repoid),
                cfg.filesystem.gpg_keys_dir,
                cfg.filesystem.cert_dir,
                repoid,
                repository,
                urls,
                details.get('gpg_keys', []),
                details.get('ca_cert'),
                details.get('client_cert'),
                len(urls) > 0,)
        report.succeeded()
        return report

    def rebind(self, definitions):
        """
        (Re)bind a repository.
        @param definitions: A list of bind definitions.
        Definition:
            {consumer_id:<str>,
             repo_id:<str>,
             distributor_id:<str>,
             href:<str>,
             type_id:<str>,
             details:<dict>}
        @type definitions: list
        @return: A rebind report.
        @rtype: L{BindReport}
        """
        log.info('(re)bind: %s', definitions)
        self.clean()
        return self.bind(definitions)

    def unbind(self, repoid):
        """
        Bind a repository.
        @param repoid: A repository ID.
        @type repoid: str
        @return: An unbind report.
        @rtype: L{BindReport}
        """
        log.info('unbind: %s', repoid)
        report = BindReport()
        cfg = ConsumerConfig()
        repolib.unbind(
            cfg.filesystem.repo_file,
            os.path.join(cfg.filesystem.mirror_list_dir, repoid),
            cfg.filesystem.gpg_keys_dir,
            cfg.filesystem.cert_dir,
            repoid)
        report.succeeded()
        return report

    def clean(self):
        """
        Clean up artifacts associated with the handler.
        @return: A clean report.
        @rtype: L{CleanReport}
        """
        log.info('clean')
        report = CleanReport()
        # TODO: revist this **
        report.succeeded()
        return report

    def __urls(self, details):
        """
        Construct a list of URLs.
        @param details: The bind details (payload).
        @type details: dict
        @return: A list of URLs.
        @rtype: list
        """
        urls = []
        protocol = self.__protocol(details)
        if not protocol:
            # not enabled
            return urls
        hosts = details['server_name']
        if not isinstance(hosts, list):
            hosts = [hosts,]
        path = details['relative_path']
        for host in hosts:
            url = '://'.join((protocol, host))
            urls.append(url+path)
        return urls

    def __protocol(self, details):
        """
        Select the protcol based on preferences.
        @param details: The bind details (payload).
        @type details: dict
        @return: The selected protocol.
        @rtype: str
        """
        ordering = ('https', 'http')
        selected = details['protocols']
        for p in ordering:
            if p.lower() in selected:
                return p
