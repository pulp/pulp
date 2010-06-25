#!/usr/bin/python
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
import rpm
import socket
import hashlib
import base64
import yum.packages as yumPackages

PGPHASHALGO = {
  1: 'md5',
  2: 'sha1',
  3: 'ripemd160',
  5: 'md2',
  6: 'tiger192',
  7: 'haval-5-160',
  8: 'sha256',
  9: 'sha384',
 10: 'sha512',
}
# need this for rpm-pyhon < 4.6 (e.g. on RHEL5)
rpm.RPMTAG_FILEDIGESTALGO = 5011


def getVersionRelease():
    ts = rpm.TransactionSet()
    for h in ts.dbMatch('Providename', "redhat-release"):
        version = h['version']
        versionRelease = (h['name'], version, h['release'])
        return versionRelease

def getArch():
    arch = os.uname()[4]
    replace = {"i686": "i386"}
    if replace.has_key(arch):
        arch = replace[arch]
    return arch

def getHostname():
    return socket.gethostname()

def getFQDN():
    return socket.getfqdn() 

def writeToFile(filename, message, overwrite=True):
    dir_name = os.path.dirname(filename)
    if not os.access(dir_name, os.W_OK):
        os.mkdir(dir_name)
    if os.access(filename, os.F_OK) and not overwrite:
        # already have file there; let's back it up
        try:
            os.rename(filename, filename + '.save')
        except:
            return False

    fd = os.open(filename, os.O_WRONLY | os.O_CREAT, 0644)
    msgFile = os.fdopen(fd, 'w')
    try:
        msgFile.write(message)
    finally:
        msgFile.close()

    return True

def listdir(directory):
    directory = os.path.abspath(os.path.normpath(directory))
    if not os.access(directory, os.R_OK | os.X_OK):
        raise Exception("Cannot read from directory %s" % directory)
    if not os.path.isdir(directory):
        raise Exception("%s not a directory" % directory)
    # Build the package list
    packagesList = []
    for f in os.listdir(directory):
        packagesList.append("%s/%s" % (directory, f))
    return packagesList

def processDirectory(dirpath, ftype):
    dirfiles = []
    for file in listdir(dirpath):
        # only add packages
        if file[-3:] in ftype:
            dirfiles.append(file)
    return dirfiles

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


class FileError(Exception):
    pass

def processFile(filename, relativeDir=None, source=None):
    # Is this a file?
    if not os.access(filename, os.R_OK):
        raise FileError("Could not stat the file %s" % filename)
    if not os.path.isfile(filename):
        raise FileError("%s is not a file" % filename)

    # Size
    size = os.path.getsize(filename)
    hash = {'size' : size}
    if relativeDir:
        # Append the relative dir too
        hash["relativePath"] = "%s/%s" % (relativeDir,
            os.path.basename(filename))

    # Read the header
    try:
        ts = rpm.TransactionSet()
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
        h = readRpmHeader(ts, filename)
    except:
        return hash

    # Get the name, version, release, epoch, arch
    lh = []
    for k in ['name', 'version', 'release', 'epoch']:
        lh.append(h[k])
    # Fix the epoch
    if lh[3] is None:
        lh[3] = ""
    else:
        lh[3] = str(lh[3])

    if source:
        lh.append('src')
    else:
        lh.append(h['arch'])

    hash['nvrea'] = tuple(lh)
    hash['hashtype'] = getChecksumType(h)
    hash['checksum'] = getFileChecksum(hash['hashtype'], filename=filename)
    hash['pkgname'] = os.path.basename(filename)
    return hash

def getChecksumType(header):
    if header[rpm.RPMTAG_FILEDIGESTALGO] \
       and PGPHASHALGO.has_key(header[rpm.RPMTAG_FILEDIGESTALGO]):
        checksum_type = PGPHASHALGO[header[rpm.RPMTAG_FILEDIGESTALGO]]
    else:
        checksum_type = 'md5'
    return checksum_type

def readRpmHeader(ts, rpmname):
    fd = os.open(rpmname, os.O_RDONLY)
    h = ts.hdrFromFdno(fd)
    os.close(fd)
    return h

def generatePkgMetadata(pkgFile):
    ts = rpm.TransactionSet()
    yumPkg = yumPackages.YumLocalPackage(ts, filename=pkgFile)
    primary_xml = yumPkg.xml_dump_primary_metadata()
    return base64.b64encode(primary_xml)

def generatePakageProfile(rpmHeaderList):
    """ Accumulates list of installed rpm info """
    
    pkgList = []
    for h in rpmHeaderList:
        if h['name'] == "gpg-pubkey":
            #dbMatch includes imported gpg keys as well
            # skip these for now as there isnt compelling 
            # reason for server to know this info
            continue
        info = {
            'name'          : h['name'],
            'version'       : h['version'],
            'release'       : h['release'],
            'epoch'         : h['epoch'] or 0,
            'arch'          : h['arch'],
        }
        pkgList.append(info)
    return pkgList
 
def getRpmName(pkg):
    return pkg["name"] + "-" + pkg["version"] + "-" + \
           pkg["release"] + "." + pkg["arch"]


