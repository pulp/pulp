#!/usr/bin/env python
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
import os
import logging
import httplib
import urllib
import xmlrpclib
import urlparse

LOG = logging.getLogger("grinder.RHNComm")

from GrinderExceptions import GetRequestException

class RHNComm(object):
    """
        This class is responsible for handling communication to RHN APIs.
    It uses a mixture of XMLRPC calls as well as wrappers around regular 'GET' calls
    """
    def __init__(self, satelliteURL, systemId):
        self.baseURL = satelliteURL
        self.authMap = None
        self.systemId = systemId

    def login(self, refresh=False):
        """
        Input: refresh  default value is False
          if refresh is True we will force a login call and refresh the 
          cached authentication map
        Output: dict of authentication credentials to be placed in header 
          for future package fetch 'GET' calls
        Note:
          The authentication data returned is cached, it is only updated on the
          first call, or when "refresh=True" is passed.
        Background:
            If we make too many login calls to RHN we could make the referring
            systemid be flagged as abusive.  Current metrics allow ~100 logins a day
        """
        if self.authMap and not refresh:
            return self.authMap
        client = xmlrpclib.Server(self.baseURL+"/SAT/", verbose=0)
        self.authMap = client.authentication.login(self.systemId)
        self.authMap["X-RHN-Satellite-XML-Dump-Version"] = "3.5"
        return self.authMap


    def __getRequest(self, relativeURL, headers={}):
        """
        Input:
            relativeURL - url for request
            headers - dictionary of key/value pairs to add to header
        Output:
            data from response
        Exception:
            GetRequestException is thrown if response is anything other than 200
        """
        authMap = self.login()
        for key in authMap:
            headers[key] = self.authMap[key]
        r = urlparse.urlsplit(self.baseURL)
        if hasattr(r, 'netloc'):
            netloc = r.netloc
        else:
            netloc = r[1]
        conn = httplib.HTTPConnection(netloc)
        conn.request("GET", relativeURL, headers=headers)
        resp = conn.getresponse()
        if resp.status == 401:
            LOG.warn("Got a response of %s:%s, Will refresh authentication credentials and retry" \
                % (resp.status, resp.reason))
            authMap = self.login(refresh=True)
            conn.request("GET", relativeURL, params=params, headers=headers)
            resp = conn.getresponse()
        if resp.status != 200:
            LOG.critical("ERROR: Response = %s 'GET' %s.  Our Authentication Info is : %s" \
                % (resp.status, relativeURL, authMap))
            conn.close()
            raise GetRequestException(relativeURL, resp.status)
        data = resp.read()
        conn.close()
        return data

    def getRepodata(self, channelLabel, fileName):
        url = "/SAT/$RHN/" + channelLabel + "/repodata/" + fileName
        data = self.__getRequest(url)
        return data

if __name__ == "__main__":
    systemId = open("/etc/sysconfig/rhn/systemid").read()
    downldr = RHNComm("http://satellite.rhn.redhat.com", systemId)
    d = downldr.getRepodata("rhel-i386-server-5", "comps.xml")
    print d

    
