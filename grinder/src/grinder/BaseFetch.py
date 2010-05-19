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
import httplib
import urlparse
import time
import pycurl
import logging
import traceback
import hashlib
import types
import unicodedata

LOG = logging.getLogger("grinder.BaseFetch")

class BaseFetch(object):
    STATUS_NOOP = 'noop'
    STATUS_DOWNLOADED = 'downloaded'
    STATUS_SIZE_MISSMATCH = 'size_missmatch'
    STATUS_MD5_MISSMATCH = 'md5_missmatch'
    STATUS_ERROR = 'error'
    STATUS_UNAUTHORIZED = "unauthorized"

    def __init__(self, cacert=None, clicert=None, clikey=None):
        self.sslcacert = cacert
        self.sslclientcert = clicert
        self.sslclientkey = clikey

    def validateDownload(self, filePath, size, hashtype, checksum, verbose=False):
        statinfo = os.stat(filePath)
        fileName = os.path.basename(filePath)
        calchecksum = getFileChecksum(hashtype, filename=filePath)
        # validate fetched data
        if statinfo.st_size != int(size):
            LOG.error("%s size mismatch, read: %s bytes, was expecting %s bytes" \
                      % (fileName, statinfo.st_size, size))
            os.remove(filePath)
            return BaseFetch.STATUS_SIZE_MISSMATCH
        elif calchecksum != checksum:
            LOG.error("%s md5sum mismatch, read md5sum of: %s expected md5sum of %s" \
                      %(fileName, calchecksum, checksum))
            os.remove(filePath)
            return BaseFetch.STATUS_MD5_MISSMATCH
        LOG.debug("Package [%s] is valid with checksum [%s] and size [%s]" % (fileName, checksum, size))
        return BaseFetch.STATUS_DOWNLOADED
    
    def fetch(self, fileName, fetchURL, itemSize, hashtype, checksum, savePath, headers=None, retryTimes=2):
        """
        Input:
            itemInfo = dict with keys: 'file_name', 'fetch_url', 'item_size', 'hashtype', 'checksum'
            retryTimes = how many times to retry fetch if an error occurs
        Will return a true/false if item was fetched successfully 
        """

        filePath = os.path.join(savePath, fileName)
        tempDirPath = os.path.dirname(filePath)
        if not os.path.isdir(tempDirPath):
            LOG.info("Creating directory: %s" % tempDirPath)
            try:
                os.makedirs(tempDirPath)
            except OSError, e:
                # Another thread may have created the dir since we checked,
                # if that's the case we'll see errno=17, so ignore that exception
                if e.errno != 17:
                    tb_info = traceback.format_exc()
                    LOG.debug("%s" % (tb_info))
                    LOG.critical(e)
                    raise e
                
        if os.path.exists(filePath) and \
            verifyChecksum(filePath, hashtype, checksum):
            LOG.info("%s exists with correct size and md5sum, no need to fetch." % (filePath))
            return BaseFetch.STATUS_NOOP

        try:
            f = open(filePath, "wb")
            curl = pycurl.Curl()
            curl.setopt(curl.VERBOSE,0)
            if type(fetchURL) == types.UnicodeType:
                #pycurl does not accept unicode strings for a URL, so we need to convert
                fetchURL = unicodedata.normalize('NFKD', fetchURL).encode('ascii','ignore')
            curl.setopt(curl.URL, fetchURL)
            if self.sslcacert and self.sslclientcert and self.sslclientkey:
                curl.setopt(curl.CAINFO, self.sslcacert)
                curl.setopt(curl.SSLCERT, self.sslclientcert)
                curl.setopt(curl.SSLKEY, self.sslclientkey)
            if headers:
                curl.setopt(pycurl.HTTPHEADER, curlifyHeaders(headers))
            curl.setopt(curl.WRITEFUNCTION, f.write)
            curl.setopt(curl.FOLLOWLOCATION, 1)
            LOG.info("Fetching %s bytes: %s from %s" % (itemSize, fileName, fetchURL))
            curl.perform()
            status = curl.getinfo(curl.HTTP_CODE)
            curl.close()
            f.close()
            
            if status == 401:
                LOG.warn("Unauthorized request from: %s" % (fetchURL))
                return BaseFetch.STATUS_UNAUTHORIZED
            if status != 200:
                LOG.critical("ERROR: Response = %s fetching %s." % (status, fetchURL))
                if retryTimes > 0:
                    retryTimes -= 1
                    LOG.warn("Retrying fetch of: %s with %s retry attempts left." % (fileName, retryTimes))
                    return self.fetch(fileName, fetchURL, itemSize, hashtype, checksum, savePath, headers, retryTimes)
                return BaseFetch.STATUS_ERROR
            # validate the fetched bits
            vstatus = self.validateDownload(filePath, int(itemSize), hashtype, checksum)
            if vstatus in [BaseFetch.STATUS_ERROR, BaseFetch.STATUS_SIZE_MISSMATCH, 
                BaseFetch.STATUS_MD5_MISSMATCH] and retryTimes > 0:
                #
                # Incase of a network glitch or issue with RHN, retry the rpm fetch
                #
                retryTimes -= 1
                LOG.warn("Retrying fetch of: %s with %s retry attempts left." % (fileName, retryTimes))
                return self.fetch(fileName, fetchURL, itemSize, hashtype, checksum, savePath, headers, retryTimes)
            LOG.debug("Successfully Fetched Package - [%s]" % filePath)
            return vstatus
        except Exception, e:
            tb_info = traceback.format_exc()
            LOG.debug("%s" % (tb_info))
            LOG.warn("Caught exception<%s> in fetch(%s, %s)" % (e, fileName, fetchURL))
            if retryTimes > 0:
                retryTimes -= 1
                LOG.warn("Retrying fetch of: %s with %s retry attempts left." % (fileName, retryTimes))
                return self.fetch(fileName, fetchURL, itemSize, hashtype, checksum, savePath, headers, retryTimes)
            return BaseFetch.STATUS_ERROR

def getFileChecksum(hashtype, filename=None, fd=None, file=None, buffer_size=None):
    """ Compute a file's checksum
    """
    if hashtype in ['sha', 'SHA']:
        hashtype = 'sha1'

    if buffer_size is None:
        buffer_size = 65536

    if filename is None and fd is None and file is None:
        raise ValueError("no file specified")
    if file:
        f = file
    elif fd is not None:
        f = os.fdopen(os.dup(fd), "r")
    else:
        f = open(filename, "r")
    # Rewind it
    f.seek(0, 0)
    m = hashlib.new(hashtype)
    while 1:
        buffer = f.read(buffer_size)
        if not buffer:
            break
        m.update(buffer)

    # cleanup time
    if file is not None:
        file.seek(0, 0)
    else:
        f.close()
    return m.hexdigest()

def verifyChecksum(filePath, hashtype, checksum):
    if getFileChecksum(hashtype, filename=filePath) == checksum:
        return True
    return False

def curlifyHeaders(headers):
    # pycurl drops empty header. Combining headers
    cheaders = ""
    for key,value in headers.items():
        cheaders += key +": "+ str(value) + "\r\n"
    return [cheaders]

if __name__ == "__main__":
    import GrinderLog
    GrinderLog.setup(True)
    systemId = open("/etc/sysconfig/rhn/systemid").read()
    baseURL = "http://satellite.rhn.redhat.com"
    bf = BaseFetch()
    itemInfo = {}
    fileName = "Virtualization-es-ES-5.2-9.noarch.rpm"
    fetchName = "Virtualization-es-ES-5.2-9:.noarch.rpm"
    channelLabel = "rhel-i386-server-vt-5"
    fetchURL = baseURL + "/SAT/$RHN/" + channelLabel + "/getPackage/" + fetchName;
    itemSize = "1731195"
    md5sum = "91b0f20aeeda88ddae4959797003a173" 
    hashtype = "md5"
    savePath = "./test123"
    from RHNComm import RHNComm
    rhnComm = RHNComm(baseURL, systemId)
    authMap = rhnComm.login()
    status = bf.fetch(fileName, fetchURL, itemSize, hashtype, md5sum, savePath, headers=authMap, retryTimes=2)
    print status
    assert(status in [BaseFetch.STATUS_DOWNLOADED, BaseFetch.STATUS_NOOP])
    print "Test Download or NOOP passed"
    status = bf.fetch(fileName, fetchURL, itemSize, hashtype, md5sum, savePath, headers=authMap, retryTimes=2)
    assert(status == BaseFetch.STATUS_NOOP)
    print "Test for NOOP passed"
    authMap['X-RHN-Auth'] = "Bad Value"
    fileName = "Virtualization-en-US-5.2-9.noarch.rpm"
    fetchName = "Virtualization-en-US-5.2-9:.noarch.rpm"
    status = bf.fetch(fileName, fetchURL, itemSize, hashtype, md5sum, savePath, headers=authMap, retryTimes=2)
    print status
    assert(status == BaseFetch.STATUS_UNAUTHORIZED)
    print "Test for unauthorized passed"
    print "Repo Sync Test"
    baseURL = "http://download.fedora.devel.redhat.com/pub/fedora/linux/releases/12/Everything/x86_64/os/"
    bf = BaseFetch(baseURL)
    itemInfo = {}
    
