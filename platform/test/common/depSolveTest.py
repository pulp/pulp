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
import os
import os.path
sys.path.insert(0,'/usr/share/yum-cli')

import yum
from yum.misc import getCacheDir, setup_locale
from yum.packages import parsePackages
from yum.Errors import RepoError
from utils import YumUtilBase

from urlparse import urljoin
from urlgrabber.progress import TextMeter
import shutil

import rpmUtils
import logging


class DepSolver(YumUtilBase):
    NAME = 'depsolver'
    VERSION = '1.0'
    USAGE = '"depsolver [options] package "'
    
    def __init__(self):
        YumUtilBase.__init__(self,
                             DepSolver.NAME,
                             DepSolver.VERSION,
                             DepSolver.USAGE)
        self.logger = logging.getLogger("yum.verbose.cli.depsolver")  
        
        self.main()

    def main(self):
                
        opts = {}
        
        # Setup yum (Ts, RPM db, Repo & Sack)
        self.doUtilYumSetup(opts)
        
        # Do the real action
        self.findDependencies(opts)
        
    def findDependencies(self,opts):
        
        toDownload = []
    
        pkg = sys.argv[3]
        if pkg:
            toActOn = []
                        
            pkgnames = [pkg]
            
            pos = self.pkgSack.returnPackages(patterns=pkgnames)
            exactmatch, matched, unmatched = parsePackages(pos, pkgnames)
            installable = yum.misc.unique(exactmatch + matched)
            if not installable: # doing one at a time, apart from groups
                self.logger.error('No Match for argument %s' % pkg)
                exit()
            
            for newpkg in installable:
                toActOn.extend([newpkg])
            
            if toActOn:
                pkgGroups = self._groupPackages(toActOn)
                for group in pkgGroups:
                    pkgs = pkgGroups[group]
                    toDownload.extend(self.bestPackagesFromList(pkgs))
                            
        # If the user supplies to --resolve flag, resolve dependencies for
        # all packages
        # note this might require root access because the headers need to be
        # downloaded into the cachedir (is there a way around this)
        print "\nDependencies: "
        if True:
            self.doTsSetup()
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
                url = urljoin(repo.urls[0]+'/',remote)
                print "Url: ", url
                      
                    
    def _groupPackages(self,pkglist):
        pkgGroups = {}
        for po in pkglist:
            na = '%s.%s' % (po.name,po.arch)
            if not na in pkgGroups:
                pkgGroups[na] = [po]
            else:
                pkgGroups[na].append(po)
        return pkgGroups
            
    # sligly modified from the one in YumUtilBase    
    def doUtilYumSetup(self,opts):
        """do a default setup for all the normal/necessary yum components,
           really just a shorthand for testing"""
        try:
            archlist = rpmUtils.arch.getArchList(sys.argv[2])
            print "Archlist:", archlist
            print "Existing repositories: ", self.repos
            self._getSacks(archlist=archlist, thisrepo=sys.argv[1])
        except yum.Errors.YumBaseError, msg:
            self.logger.critical(str(msg))
            sys.exit(1)


if __name__ == '__main__':
    setup_locale()
    util = DepSolver()
        
        
