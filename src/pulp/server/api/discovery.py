# -*- coding: utf-8 -*-
#
# Copyright © 20102011 Red Hat, Inc.
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


# Python
import sys
import urllib2
import re
import urlparse
import BeautifulSoup
import logging

log = logging.getLogger(__name__)

class InvalidDiscoveryInput(Exception):
    pass

class BaseDiscovery(object):
    """
    Base discovery class.
    """
    def __init__(self):
        self.url = ""

    def setUrl(self, url):
        try:
            urllib2.urlopen(url)
        except:
            raise InvalidDiscoveryInput("Invalid input url %s" % url)
        self.url = url

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
            src = urllib2.urlopen(url).read()
        except Exception, e:
            log.error("An error occurred while reading url page [%s] : %s" % (url, e))
            return []
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
                urls.append(url + "/" + path)
        return urls

    def discovery(self):
        pass

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
                        urllib2.urlopen("%s/%s" % (result, 'repomd.xml'))
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
    Returns an instance of a pulp.server.api.repo_sync.BaseSynchronizer object
    '''
    if type not in DISCOVERY_MAP:
        raise InvalidDiscoveryInput('Could not find Discovery for type [%s]', type)
    discovery = DISCOVERY_MAP[type]()
    return discovery

DISCOVERY_MAP = {
    "yum" : YumDiscovery,
}

def main():
    if not len(sys.argv) == 2:
        print "USAGE:python discovery.py <url>"
        sys.exit(0)
    print("Discovering urls with yum metadata, This could take sometime..")
    d = get_discovery("yum")
    d.setUrl(sys.argv[1])
    repourls = d.discover()
    print('========================')
    print('Urls with repodata:\n')
    print( '=======================')
    print('\n'.join(repourls))

if __name__ == '__main__':
    main()
