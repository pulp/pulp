#!/usr/bin/python
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import sys
sys.path.insert(0,'/usr/share/yum-cli')

import yum
from yum.misc import getCacheDir

from cli import *
from utils import YumUtilBase

from urlparse import urljoin
from urlgrabber.progress import TextMeter
import shutil

import rpmUtils

class DepSolver(YumUtilBase):
    NAME = 'depsolver'
    VERSION = '1.0'
    USAGE = '"usage: depsolver [options] package"'

    def __init__(self):
        YumUtilBase.__init__(self,
                             DepSolver.NAME,
                             DepSolver.VERSION,
                             DepSolver.USAGE)
        self.logger = logging.getLogger("yum.verbose.cli.depsolver")
        self.main()

    def main(self):
        # Setup yum (Ts, RPM db, Repo & Sack)
        self.doUtilYumSetup()

        # Do the real action
        self.downloadPackages()

    def downloadPackages(self):

        toDownload = []

        pkg = sys.argv[1]
        print "Pkg to be installed: ",  pkg
        if pkg:
            toActOn = []
            exactmatch, matched, unmatched = parsePackages(self.pkgSack.returnPackages(), [pkg])
            print "exactmatch: ", exactmatch

            installable = yum.misc.unique(exactmatch + matched)

            if len(unmatched) > 0: # if we get back anything in unmatched, it fails
                self.logger.error('No Match for argument %s' % pkg)
                exit

            for newpkg in installable:
                toActOn.append(newpkg)

            if toActOn:
                pkgGroups = self._groupPackages(toActOn)
                for group in pkgGroups:
                    pkgs = pkgGroups[group]
                    toDownload.extend(self.bestPackagesFromList(pkgs))

        # If the user supplies to --resolve flag, resolve dependencies for
        # all packages
        # note this might require root access because the headers need to be
        # downloaded into the cachedir (is there a way around this)
        print "Dependencies\n"
        if True:
            self.doTsSetup()
            self.localPackages = []
            # Act as if we were to install the packages in toDownload
            for po in toDownload:
                self.tsInfo.addInstall(po)
                self.localPackages.append(po)
            # Resolve dependencies
            self.resolveDeps()
            # Add newly added packages to the toDownload list
            for pkg in self.tsInfo.getMembers():
                if not pkg in toDownload:
                    toDownload.append(pkg)
        if len(toDownload) == 0:
            self.logger.error('Nothing to download')
            sys.exit(1)

        for pkg in toDownload:
            n,a,e,v,r = pkg.pkgtup
            packages =  self.pkgSack.searchNevra(n,e,v,r,a)
            for download in packages:
                repo = self.repos.getRepo(download.repoid)
                print "Repo: ", repo
                remote = download.returnSimple('relativepath')
                print "Url: ", remote
                if True:
                    url = urljoin(repo.urls[0]+'/',remote)
                    self.logger.info('%s' % url)
                    continue
                local = os.path.basename(remote)




    def _groupPackages(self,pkglist):
        pkgGroups = {}
        for po in pkglist:
            na = '%s.%s' % (po.name,po.arch)
            if not na in pkgGroups:
                pkgGroups[na] = [po]
            else:
                pkgGroups[na].append(po)
        return pkgGroups

    # slightly modified from the one in YumUtilBase
    def doUtilYumSetup(self):
        """do a default setup for all the normal/necessary yum components,
           really just a shorthand for testing"""
        try:
            self._getRepos()
            archlist = rpmUtils.arch.getArchList()
            print "Archlist: ", archlist
            self._getSacks(archlist=archlist)
        except yum.Errors.YumBaseError, msg:
            self.logger.critical(str(msg))
            sys.exit(1)

    def _removeEnabledSourceRepos(self):
        ''' Disable all enabled *-source repos.'''
        for repo in self.repos.listEnabled():
            if repo.id.endswith('-source'):
                repo.close()
                self.repos.disableRepo(repo.id)
                srcrepo = repo.id


if __name__ == '__main__':
    import locale
    # This test needs to be before locale.getpreferredencoding() as that
    # does setlocale(LC_CTYPE, "")
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error, e:
        # default to C locale if we get a failure.
        print >> sys.stderr, 'Failed to set locale, defaulting to C'
        os.environ['LC_ALL'] = 'C'
        locale.setlocale(locale.LC_ALL, 'C')

    if True: # not sys.stdout.isatty():
        import codecs
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
        sys.stdout.errors = 'replace'

    util = DepSolver()


