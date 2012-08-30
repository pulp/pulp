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
from logging import getLogger


_LOG = getLogger(__name__)


CONFIG_PATH = '/etc/pulp/consumer/consumer.conf'


 
class UnitKey:

    def __init__(self, unit):
        type_id = unit['type_id']
        unit_key = tuple(sorted(unit['unit_key'].items()))
        self.uid = (type_id, unit_key)
    
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

    def sync_repo(self, repo, conduit, config):
        baseurl = config.get('baseurl')
        if not baseurl:
            cfg = Config(CONFIG_PATH)
            host = cfg['server']['host']
            baseurl = 'http://%s/pulp/downstream/repos' % host
        reader = UnitsReader(baseurl, repo.id)
        upstream =  dict([(UnitKey(u), u) for u in reader.read()])
        units = dict([(UnitKey(u), u) for u in conduit.get_units()])
        downloader = UnitDownloader(baseurl, repo.id)
        for k,unit in upstream.items():
            if k in units:
                continue
            u = Unit(unit['type_id'],
                     unit['unit_key'],
                     unit['metadata'],
                     unit['storage_path'])
            conduit.save_unit(u)
            downloader.install(unit)

    def cancel_sync_repo(self, call_request, call_report):
        pass
    
    def unique_id(self, unit):
        type_id = unit['type_id']
        unit_key = sorted(unit['unit_key'].items())
        uid = (type_id, unit_key)
        return uid


class UnitsReader:
    
    def __init__(self, baseurl, repo_id):
        self.baseurl = baseurl
        self.repo_id = repo_id

    def read(self):
        url = '/'.join((self.baseurl, self.repo_id, 'units.json'))
        fp = urllib.urlopen(url)
        try:
            return json.load(fp)
        finally:
            fp.close()
            
            
class UnitDownloader:
    
    def __init__(self, baseurl, repo_id):
        self.baseurl = baseurl
        self.repo_id = repo_id
    
    def install(self, unit):
        m = hashlib.sha256()
        target = unit['storage_path']
        m.update(target)
        url = '/'.join((self.baseurl, self.repo_id, 'units', m.hexdigest()))
        fp_in = urllib.urlopen(url)
        try:
            self.__write(fp_in, target)
        finally:
            fp_in.close()
    
    def __write(self, fp_in, path):
        self.__mkdir(path)
        fp_out = open(path, 'w+')
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