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

import os
import urllib
import hashlib
from pulp.server.compat import json
from pulp.common.config import Config
from pulp.plugins.model import Unit
from pulp.plugins.importer import Importer


class UnitKey:

    def __init__(self, unit):
        type_id = unit['type_id']
        unit_key = sorted(unit['unit_key'].items())
        self.uid (type_id, unit_key)
    
    def __hash__(self):
        return hash(self.uid)
    
    def __eq__(self, other):
        return self.uid == other.uid
    
    def __ne__(self, other):
        return self.uid != other.uid
    

class PulpImporter(Importer):

    @classmethod
    def metadata(cls):
        return {
            'id':'pulp_importer',
            'display_name':'Pulp Importer',
            'types':['rpm',]
        }

    def validate_config(self, repo, config, related_repos):
        return (True, None)

    def sync_repo(self, repo, sync_conduit, config):
        reader = UnitsReader()
        upstream =  dict([UnitKey(u) for u in reader.read()])
        units = dict([UnitKey(u) for u in publish_conduit.get_units()])
        downloader = UnitDownloader(repo.id)
        for k,unit in upstream.items():
            if k in units:
                continue
            u = Unit(unit['type_id'],
                     unit['unit_key'],
                     unit['metadata'],
                     unit['storage_path'])
            sync_conduit.save_unit(u)
            downloader.install(unit)

    def cancel_sync_repo(self, call_request, call_report):
        pass
    
    def unique_id(self, unit):
        type_id = unit['type_id']
        unit_key = sorted(unit['unit_key'].items())
        uid = (type_id, unit_key)
        return uid


class UnitsReader:
    
    CONFIG_PATH = '/etc/pulp/consumer/consumer.conf'
    URL = 'http://%s:%d/pulp/downstream/repos/%s/units.json'
    
    def __init__(self, configpath=CONFIG_PATH):
        cfg = Config(configpath)
        server = cfg['server']
        self.host = server['host']
        self.port = int(server['port'])

    def read(self, repo_id):
        url = self.URL % (self.server, self.port, repo_id)
        fp = url.urlopen(url)
        try:
            return json.load(fp)
        finally:
            fp.close()
            
            
class UnitDownloader:

    CONFIG_PATH = '/etc/pulp/consumer/consumer.conf'
    URL = 'http://%s:%d/pulp/downstream/repos/%s/units/%s'
    
    def __init__(self, repo_id, configpath=CONFIG_PATH):
        cfg = Config(configpath)
        server = cfg['server']
        self.host = server['host']
        self.port = int(server['port'])
        self.repo_id = repo_id
    
    def install(self, unit):
        url = self.URL % (self.server, self.port, self.repo_id)
        m = hashlib.sha256()
        target = unit['storage_path']
        m.update(target)
        url = URL % (self.server, self.port, m.hexdigest())
        fp_in = httplib.urlopen(url)
        try:
            self.write(fp_in, target)
        finally:
            fp_in.close()
    
    def __write(self, fp_in, path):
        fp_out = open(target, 'w+')
        try:
            while True:
                bfr = fp_in.read(0x100000)
                if bfr:
                    fp_out.write(bfr)
                else:
                    break
        finally:
            fp_out.close()

    def __mkdir(self, path):
        path = os.path.dirname(path)
        if not os.path.exists(path):
            os.makedirs(path)