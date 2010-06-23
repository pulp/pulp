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

import locale
import httplib
import simplejson as json
from M2Crypto import SSL, httpslib
from pulptools.logutil import getLogger

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
        if str(response.status) not in ["200", "202", "204"]:
            raise RestlibException(response.status, response.read())
            #parsed = json.loads(response.read())

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
    def create(self, id, name, arch, feed, sync_schedule=None):
        method = "/repositories/"
        repodata = {"id"   : id,
                    "name" : name,
                    "arch" : arch,
                    "feed" : feed,
                    "sync_schedule" : sync_schedule,}
        return self.conn.request_put(method, params=repodata)

    def repository(self, id):
        method = "/repositories/%s/" % str(id)
        return self.conn.request_get(method)

    def repositories(self):
        method = "/repositories/"
        return self.conn.request_get(method)

    def update(self, repo):
        method = "/repositories/%s/" % repo['id']
        return self.conn.request_put(method, params=repo)

    def delete(self, id):
        method = "/repositories/%s/" % id
        return self.conn.request_delete(method)

    def clean(self):
        method = "/repositories/"
        return self.conn.request_delete(method)

    def sync(self, repoid):
        method = "/repositories/%s/sync/" % repoid
        return self.conn.request_post(method)

    def add_package(self, repoid, packageid):
        addinfo = {'repoid' : repoid,
                      'packageid' : packageid}
        method = "/repositories/%s/add_package/" % repoid
        print "Add info: %s" % addinfo
        return self.conn.request_post(method, params=addinfo)
    
    # XXX no supporting server-side call
    def get_package(self, repoid, pkg_name):
        method = "/repositories/%s/package/%s/" % (repoid, pkg_name)
        return self.conn.request_get(method)

    def packages(self, repoid):
        method = "/repositories/%s/list/" % repoid
        return self.conn.request_post(method)

    def upload(self, id, pkginfo, pkgstream):
        uploadinfo = {'repo' : id,
                      'pkginfo' : pkginfo,
                      'pkgstream' : pkgstream}
        method = "/repositories/%s/upload/" % id
        return self.conn.request_post(method, params=uploadinfo)

    def all_schedules(self):
        method = "/repositories/schedules/"
        return self.conn.request_get(method)
    
    def sync_status(self, status_path):
        return self.conn.request_get(status_path)


class ConsumerConnection(PulpConnection):
    """
    Connection class to access repo specific calls
    """
    def create(self, id, description):
        consumerdata = {"id"   : id, "description" : description}
        method = "/consumers/"
        return self.conn.request_put(method, params=consumerdata)
    
    def update(self, consumer):
        method = "/consumers/%s/" % consumer['id']
        return self.conn.request_put(method, params=consumer)

    def bulkcreate(self, consumers):
        method = "/consumers/bulk/"
        return self.conn.request_post(method, params=consumers)

    def delete(self, id):
        method = "/consumers/%s/" % id
        return self.conn.request_delete(method)

    def clean(self):
        method = "/consumers/"
        return self.conn.request_delete(method)

    def consumer(self, id):
        method = "/consumers/%s/" % str(id)
        return self.conn.request_get(method)

    def packages(self, id):
        method = "/consumers/%s/packages/" % str(id)
        return self.conn.request_post(method)

    def consumers(self):
        method = "/consumers/"
        return self.conn.request_get(method)

    def consumers_with_package_name(self, name):
        method = '/consumers/?name=%s' % name
        return self.conn.request_get(method)

    def bind(self, id, repoid):
        method = "/consumers/%s/bind/" % id
        return self.conn.request_post(method, params=repoid)

    def unbind(self, id, repoid):
        method = "/consumers/%s/unbind/" % id
        return self.conn.request_post(method, params=repoid)
    
    def profile(self, id, profile):
        method = "/consumers/%s/profile/" % id
        return self.conn.request_post(method, params=profile)

    def installpackages(self, id, packagenames):
        method = "/consumers/%s/installpackages/" % id
        body = dict(packagenames=packagenames)
        return self.conn.request_post(method, params=body)

class PackageConnection(PulpConnection):

    def clean(self):
        method = "/packages/"
        return self.conn.request_delete(method)

    def create(self, name, epoch, version, release, arch, description, 
            checksum_type, checksum, filename):
        method = "/packages/"
        repodata = {"name"   : name,
                    "epoch" : epoch,
                    "version" : version,
                    "release" : release,
                    "arch" : arch,
                    "description" : description,
                    "checksum_type" : checksum_type,
                    "checksum": checksum,
                    "filename": filename,}
        return self.conn.request_put(method, params=repodata)

    def packages(self):
        method = "/packages/"
        return self.conn.request_get(method)

    def package(self, id, filter=None):
        method = "/packages/%s/" % id
        return self.conn.request_get(method)

    def delete(self, packageid):
        method = "/packages/%s/" % packageid
        return self.conn.request_delete(method)

    def package_by_ivera(self, name, version, release, epoch, arch):
        method = "/packages/%s/%s/%s/%s/%s/" % (name, version, release, epoch, arch)
        return self.conn.request_get(method)

class PackageGroupConnection(PulpConnection):

    def clean(self):
        pass


class PackageGroupCategoryConnection(PulpConnection):

    def clean(self):
        pass


if __name__ == '__main__':
    rconn = RepoConnection()
    print "+--------------------------------+"
    print "   Repo API Tests                "
    print "+--------------------------------+"
    
    repo = rconn.create('test-f12', 'f12','i386', 'yum:http://mmccune.fedorapeople.org/pulp/')
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
    print "+--------------------------------+"
    print "   Consumer API Tests             "
    print "+--------------------------------+"
    cconn = ConsumerConnection()
    print "Create Consumer", cconn.create("test", 'prad.rdu.redhat.com')
    print "List Consumers", cconn.consumers()
