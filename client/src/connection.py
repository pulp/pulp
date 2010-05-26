#
# A proxy interface to initiate and interact communication with Pulp Server.
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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

import sys
import locale
import httplib
import simplejson as json
import base64
from M2Crypto import SSL, httpslib
from logutil import getLogger

import gettext
_ = gettext.gettext

log = getLogger(__name__)

class RestlibException(Exception):
    def __init__(self, code, msg = ""):
        self.code = code
        self.msg = msg

    def __str__(self):
        return self.msg

class Restlib(object):
    """
     A wrapper around httplib to make rest calls easier
    """
    def __init__(self, host, port, apihandler, cert_file=None, key_file=None,):
        self.host = host
        self.port = port
        self.apihandler = apihandler
        self.headers = {"Content-type":"application/json",
                        "Accept": "application/json",
                        "Accept-Language": locale.getdefaultlocale()[0].lower().replace('_', '-')}
        self.cert_file = cert_file
        self.key_file  = key_file

    def _request(self, request_type, method, info=None):
        handler = self.apihandler + method
        if self.cert_file:
            context = SSL.Context("sslv3")
            context.load_cert(self.cert_file, keyfile=self.key_file)
            conn = httpslib.HTTPSConnection(self.host, self.port, ssl_context=context)
        else:
            conn = httplib.HTTPConnection(self.host, self.port)
        conn.request(request_type, handler, body=json.dumps(info), \
                     headers=self.headers)
        response = conn.getresponse()
        self.validateResponse(response)
        rinfo = response.read()
        if not len(rinfo):
            return None
        return json.loads(rinfo)

    def validateResponse(self, response):
        print response.status
        if str(response.status) not in ["200", "204"]:
            parsed = json.loads(response.read())
            raise RestlibException(response.status,
                    parsed['exceptionMessage']['displayMessage'])

    def request_get(self, method):
        return self._request("GET", method)

    def request_post(self, method, params=""):
        return self._request("POST", method, params)

    def request_head(self, method):
        return self._request("HEAD", method)

    def request_put(self, method, params=""):
        return self._request("PUT", method, params)

    def request_delete(self, method):
        return self._request("DELETE", method)

class PulpConnection:
    """
    Proxy connection to Pulp Server
    """

    def __init__(self, host='localhost', port=8811, handler="", cert_file=None, key_file=None):
        self.host = host
        self.port = port
        self.handler = handler
        self.conn = None
        self.cert_file = cert_file
        self.key_file = key_file
        # initialize connection
        self.setUp()

    def setUp(self):
        self.conn = Restlib(self.host, self.port, self.handler, self.cert_file, self.key_file)
        log.info("Connection Established for cli: Host: %s, Port: %s, handler: %s" % (self.host, self.port, self.handler))

    def shutDown(self):
        self.conn.close()
        log.info("remote connection closed")

class RepoConnection(PulpConnection):
    """
    Connection class to access repo specific calls
    """
    def create(self, repodata):
        method = "/repositories/"
        return self.conn.request_post(method, params=repodata)

    def repositories(self):
        method = "/repositories/"
        return self.conn.request_get(method)

    def repository(self, repoid):
        method = "/repositories/%s/" % repoid
        return self.conn.request_get(method)

    def update(self, repoid, info):
        method = "/repositories/%s/" % repoid
        return self.conn.request_post(method, params=info)

    def delete(self, repoid):
        method = "/repositories/%s/" % repoid
        return self.conn.request_delete(method)

    def sync(self, repoid):
        method = "/repositories/%s/sync/" % repoid
        return self.conn.request_get(method)

    def packages(self, repoid):
        method = "/repositories/%s/list/" % repoid
        return self.conn.request_get(method)

class PackageConnection(PulpConnection):
    """
    Connection class to access repo specific calls
    """
    pass

if __name__ == '__main__':
    rconn = RepoConnection()
    repodata = {'id' : 'test-f12',
                'name' : 'f12',
                'arch' : 'i386',
                'feed' : 'yum:http://mmccune.fedorapeople.org/pulp/'}
    repo = rconn.create(repodata)
    print "create Repos", repo['id']
    print "list repos:", rconn.repositories()
    print "Get repo By Id: ",rconn.repository(repo['id'])
    newdata = {'id' : 'test-f12',
                'name' : 'f12',
                'arch' : 'noarch',
                'feed' : 'yum:http://mmccune.fedorapeople.org/pulp/'}
    #print "update Repo:",rconn.update(repo['id'], newdata)
    print "Sync Repos:", rconn.sync(repo['id'])
    print "list Repo Packages: ", rconn.packages(repo['id'])
    print "delete Repo:", rconn.delete(repo['id'])
