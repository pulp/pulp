# -*- coding: utf-8 -*-
#
# Copyright © 20102011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


# Python
import re
import sys
import StringIO
import pycurl
import urlparse
import types
import BeautifulSoup
import logging
import unicodedata

log = logging.getLogger(__name__)

class InvalidDiscoveryInput(Exception):
    pass

class BaseDiscovery(object):
    """
    Base discovery class.
    """
    def __init__(self):

        self.url = None
        self.sslcacert = None
        self.sslclientcert = None
        self.sslclientkey = None
        self.sslverify = 0
        self._redirected = None

    def setup(self, url, ca=None, cert=None, key=None, sslverify=False):
        '''
        setup for discovery
        @param url: url link to be discovered
        @type url: string
        @param ca: optional ca certificate to access the url
        @type ca: string
        @param cert: optional certificate to access the url(this could include both cert and key)
        @type cert: string
        @param key: optional certificate key to access the url
        @type key: string
        @param sslverify: use this to enforce ssl verification of the server cert
        @type sslverify: boolean
        '''
        proto = urlparse.urlparse(url)[0]
        if proto not in ['http', 'https', 'ftp']:
             raise InvalidDiscoveryInput("Invalid input url %s" % url)
        self.url = url
        self.sslcacert = ca
        self.sslclientcert = cert
        self.sslclientkey = key
        self.sslverify = sslverify

    def _get_header(self, buf):
        '''
        callback function for pycurl.HEADERFUNCTION to get
        the header info and parse the location.
        '''
        if buf.lower().startswith('location:'):
            self._redirected = buf[9:].strip()

    def initiate_request(self, url=None):
        '''
         Initialize the curl object; loads the url and fetches the page.
         in case of redirects[301,302], the redirection is followed and
         new url is set.
         @param url: url link to be parse.
         @type url: string
         @return: html page source
         @rtype: string
        '''
        if not url:
            url = self.url
        page_info = StringIO.StringIO()
        curl = pycurl.Curl()
        curl.setopt(curl.VERBOSE,0)
        fetchURL = url
        if type(url) == types.UnicodeType:
            fetchURL = unicodedata.normalize('NFKD', url).encode('ascii','ignore')
        curl.setopt(curl.URL, fetchURL)
        if self.sslcacert:
            curl.setopt(curl.CAINFO, self.sslcacert)
        if self.sslclientcert:
            curl.setopt(curl.SSLCERT, self.sslclientcert)
        if self.sslclientkey:
            curl.setopt(curl.SSLKEY, self.sslclientkey)
        if not self.sslverify:
            curl.setopt(curl.SSL_VERIFYPEER, 0)
        curl.setopt(curl.WRITEFUNCTION, page_info.write)
        curl.setopt(curl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.HEADERFUNCTION, self._get_header)
        curl.perform()
        page_data = page_info.getvalue()
        curl.close()
        if self._redirected:
            # request has been redirected with a 301 or 302, grab the new url
            self.url = self._redirected
        return page_data

    def parse_url(self, url):
        """
        Extract and parses a url; looks up <a> tags and
        finds matching sub urls.
        @param url: url link to be parse.
        @type url: string
        @param regex: regular expression to match ythe url.
        @type regex: string
        @return: list of matching urls
        @rtype: list
        """
        try:
            log.debug("Processing URL : %s" % url)
            src = self.initiate_request(url=url)
        except Exception, e:
            log.debug("An error occurred while reading url page [%s] : %s" % (url, e))
            return []
        # we have redirection set, lets use the new url
        if self._redirected:
            url = self._redirected
        try:
            soup = BeautifulSoup.BeautifulSoup(src)
        except Exception, e:
            log.error("An error occurred while loading url source: %s" % e)
            return []
        matches = soup.fetch('a')[1:]
        urls = []
        for item in matches:
            link = urlparse.urlparse(item['href'])
            proto, netloc, path, params, query, frag = link
            if not path or path == '/':
                continue
            rex = re.compile('.')
            if rex.match(path) and path.endswith('/'):
                if not url.endswith('/'):
                    url += '/'
                urls.append(url + path)
        #reset the redirection for next request
        self._redirected = None
        return urls

    def discover(self):
        raise NotImplementedError('base discovery class method called')

class YumDiscovery(BaseDiscovery):
    '''
    Yum discovery class to perform 
    '''
    def discover(self):
        '''
        Takes a root url and traverses the tree to find all the sub urls
        that has repodata in them.
        @param url: url link to be parse.
        @type url: string
        @return: list of matching urls
        @rtype: list
        '''
        repourls = []
        urls = self.parse_url(self.url)
        while urls:
            uri = urls.pop()
            results = self.parse_url(uri)
            for result in results:
                if not "href=" in result:
                    urls.append(result)
                if result.endswith('/repodata/'):
                    try:
                        self.initiate_request(url="%s/%s" % (result, 'repomd.xml'))
                        repourls.append(result[:result.rfind('/repodata/')])
                    except:
                        # repomd.xml could not be found, skip
                        continue
        return repourls


def get_discovery(type):
    '''
    Returns an instance of a Discovery object
    @param type: discovery type
    @type type: string
    Returns an instance of a Discovery object
    '''
    if type not in DISCOVERY_MAP:
        raise InvalidDiscoveryInput('Could not find Discovery for type [%s]', type)
    discovery = DISCOVERY_MAP[type]()
    return discovery

DISCOVERY_MAP = {
    "yum" : YumDiscovery,
}

def main():
    if len(sys.argv) < 2:
        print "USAGE:python discovery.py <url>"
        sys.exit(0)
    print("Discovering urls with yum metadata, This could take sometime..")
    type = "yum"
    url = sys.argv[1]
    ca =  None
    cert = None
    key = None
    d = get_discovery(type)
    d.setup(url, ca, cert, key)
    repourls = d.discover()
    print('========================')
    print('Urls with repodata:\n')
    print( '=======================')
    print('\n'.join(repourls))

if __name__ == '__main__':
    main()
