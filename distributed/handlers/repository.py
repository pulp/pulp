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
from pulp.common.bundle import Bundle as BundleImpl
from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import HandlerReport
from pulp.bindings.bindings import Bindings
from pulp.bindings.server import PulpConnection
from logging import getLogger

log = getLogger(__name__)

DISTRIBUTOR_ID = 'pulp_distributor'

class ConsumerConfig(INIConfig):
    def __init__(self):
        path = '/etc/pulp/consumer/consumer.conf'
        fp = open(path)
        try:
            INIConfig.__init__(self, fp)
        finally:
            fp.close()


class LocalBindings(Bindings):
    """
    Pulp (REST) API.
    """
    
    def __init__(self):
        host = 'localhost'
        port = 443
        cert = os.path.expanduser('~/.pulp/user-cert.pem')
        connection = PulpConnection(host, port, cert_filename=cert)
        Bindings.__init__(self, connection)


class RemoteBindings(Bindings):
    """
    Pulp (REST) API.
    """
    
    def __init__(self):
        cfg = ConsumerConfig()
        host = cfg.server.host
        port = int(cfg.server.port)
        cert = os.path.join(
            cfg.filesystem.id_cert_dir,
            cfg.filesystem.id_cert_filename)
        connection = PulpConnection(host, port, cert_filename=cert)
        Bindings.__init__(self, connection)


class Bundle(BundleImpl):
    """
    Consumer certificate (bundle)
    """

    def __init__(self):
        cfg = ConsumerConfig()
        path = os.path.join(
            cfg.filesystem.id_cert_dir,
            cfg.filesystem.id_cert_filename)
        BundleImpl.__init__(self, path)


class RepositoryHandler(ContentHandler):

    def update(self, units, options):
        """
        Update content unit(s).
        Unit key of {} or None indicates updates update all
        but only if (all) option is True.
        @param units: A list of content unit_keys.
        @type units: list
        @param options: Unit update options.
        @type options: dict
        @return: An update report.  See: L{Package.update}
        @rtype: L{HandlerReport}
        """
        report = HandlerReport()
        all = options.get('all', False)
        repoids = [key['repo_id'] for key in units if key]
        if all:
            bindings = self.all_bindings()
        else:
            bindings = self.bindings(repoids)
        details = self.synchronize(bindings)
        report.succeeded(details, len(details))
        return report
    
    def all_bindings(self):
        remote = RemoteBindings()
        bundle = Bundle()
        myid = bundle.cn()
        http = remote.bind.find_by_id(myid)
        if http.response_code == 200:
            return self.filtered(http.response_body)
        else:
            raise Exception('sync failed, http:%d', http.response_code)
        
    def bindings(self, repoids):
        bindings = []
        remote = RemoteBindings()
        bundle = Bundle()
        myid = bundle.cn()
        for repoid in repoids:
            http = remote.bind.find_by_id(myid, repoid)
            if http.response_code == 200:
                bindings.extend(self.filtered(http.response_body))
            else:
                raise Exception('sync failed, http:%d', http.response_code)
        return bindings
    
    def filtered(self, bindings):
        return [b for b in bindings if b['type_id'] == DISTRIBUTOR_ID]

    def synchronize(self, bindings):
        details = {}
        for b in bindings:
            repoid = b['repo_id']
            details[repoid] = b['details']
        return details

