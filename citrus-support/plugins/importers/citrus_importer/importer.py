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
    """
    A unique unit key consisting of the unit's
    type_id & unit_key to be used in unit dictonaries.
    The unit key is sorted to ensure consistency.
    @ivar uid: The unique ID.
    @type uid: tuple
    """

    def __init__(self, unit):
        """
        @param unit: A content unit.
        @type unit: dict
        """
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
            'id':'citrus_importer',
            'display_name':'Pulp Citrus Importer',
            'types':['rpm',]
        }

    def validate_config(self, repo, config, related_repos):
        return (True, None)

    def sync_repo(self, repo, conduit, config):
        # url
        baseurl = config.get('baseurl')
        if not baseurl:
            cfg = Config(CONFIG_PATH)
            host = cfg['server']['host']
            baseurl = 'http://%s/pulp/citrus/repos' % host
        # read upstream units (json) document
        reader = UnitsReader(baseurl, repo.id)
        upstream =  dict([(UnitKey(u), u) for u in reader.read()])
        # fetch local units
        units = dict([(UnitKey(u), u) for u in conduit.get_units()])
        downloader = UnitDownloader(baseurl, repo.id)
        # add missing units
        for k,unit in upstream.items():
            if k in units:
                continue
            unit['metadata'].pop('_id')
            unit['metadata'].pop('_ns')
            u = Unit(unit['type_id'],
                     unit['unit_key'],
                     unit['metadata'],
                     unit['storage_path'])
            conduit.save_unit(u)
            downloader.install(unit)

    def cancel_sync_repo(self, call_request, call_report):
        pass


class UnitsReader:
    """
    An http based upstream units (json) document reader.
    Download the document and perform the JSON conversion.
    @ivar baseurl: The base URL.
    @type baseurl: str
    @ivar repo_id: A repository ID.
    @type repo_id: str
    """
    
    def __init__(self, baseurl, repo_id):
        """
        @param baseurl: The base URL.
        @type baseurl: str
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        self.baseurl = baseurl
        self.repo_id = repo_id

    def read(self):
        """
        Fetch the document.
        @return: The downloaded json document.
        @rtype: str
        """
        url = '/'.join((self.baseurl, self.repo_id, 'units.json'))
        fp = urllib.urlopen(url)
        try:
            return json.load(fp)
        finally:
            fp.close()
            
            
class UnitDownloader:
    """
    An http based unit (bits) downloader.
    Used to download & install bits associated with content units.
    @ivar baseurl: The base URL.
    @type baseurl: str
    @ivar repo_id: A repository ID.
    @type repo_id: str
    """
    
    def __init__(self, baseurl, repo_id):
        """
        @param baseurl: The base URL.
        @type baseurl: str
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        self.baseurl = baseurl
        self.repo_id = repo_id
    
    def install(self, unit):
        """
        Download & install the (bits) associated with the specified unit.
        @param unit: The content unit to install
        @type unit: Unit
        """
        m = hashlib.sha256()
        target = unit['storage_path']
        m.update(target)
        url = '/'.join((self.baseurl, self.repo_id, 'content', m.hexdigest()))
        fp_in = urllib.urlopen(url)
        try:
            self.__write(fp_in, target)
        finally:
            fp_in.close()
    
    def __write(self, fp_in, path):
        """
        Write contents of the open file to the specified path.
        Ensure the directory exists.
        @param fp_in: An open file descriptor.
        @type fp_in: file-like
        @param path: The fully qualified path.
        @type path: str 
        """
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
        """
        Ensure the specified directory exists.
        @param path: The directory path.
        @type path: str
        """
        path = os.path.dirname(path)
        if not os.path.exists(path):
            os.makedirs(path)