#
# This module establishes and retrieves listing files from CDN for 
# versions and arches substitutions
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import logging
from M2Crypto import SSL, httpslib

log = logging.getLogger(__name__)

class CDNConnection:
    def __init__(self, hostname, port=443, cacert=None, cert=None, key=None):
        self.hostname = hostname
        self.port = port
        self.cacert = cacert
        self.cert = cert
        self.key = key
        self.httpServ = None

    def connect(self):
        context = SSL.Context("sslv3")
        context.load_cert(self.cert, keyfile=self.key)
        context.load_verify_locations(self.cacert)
        context.set_verify(SSL.verify_peer | SSL.verify_fail_if_no_peer_cert, depth=9)

        self.httpServ = httpslib.HTTPSConnection(self.hostname, port=self.port,
                ssl_context=context)
        self.httpServ.connect()

    def _request_get(self, URI):
        """
         Fetch the listings file from CDN
         @param URI: relative url for the listings file
         @type  URI: str (ex: "/content/dist/rhel/server/listing")
        """
        self.httpServ.request('GET', URI)
        response = self.httpServ.getresponse()
        if response.status != 200:
            raise Exception(response.status, response.read())
        return response.read()
    
    def fetch_urls(self, content_sets):
        version_arch_urls = {}
        for content_set in content_sets:
            label = content_set['content_set_label']
            uri   = content_set['content_rel_url']
            try:
                versions = self._request_get(uri[:uri.find("$releasever")] + "/listing").split('\n')
                for version in versions:
                    ver_uri = uri.replace("$releasever", version)
                    arches = self._request_get(ver_uri[:ver_uri.find("$basearch")] + "/listing").split('\n')
                    for arch in arches:
                        full_uri = ver_uri.replace("$basearch", arch)
                        version_arch_urls[label + '-' + version + '-' + arch] = full_uri
            except Exception:
                log.error("Unable to fetch the listings file for relative url %s" % uri)
                    
        return version_arch_urls

    def disconnect(self):
        self.httpServ.close()
        