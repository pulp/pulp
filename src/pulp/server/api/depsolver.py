#!/usr/bin/env python
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
# in this software or its documentation

import sys
import shutil
import yum
import logging
from yum.packageSack import ListPackageSack

from pulp.server import util
from yum.misc import prco_tuple_to_string
from yum.repos import RepoStorage
log = logging.getLogger(__name__)

CACHE_DIR = "/var/lib/pulp/cache/"

class DepSolver:
    def __init__(self, repos, pkgs=[]):
        self.pkgs = pkgs
        self.repos  = repos
        self._repostore = RepoStorage(self)
        self.setup()
        self.loadPackages()

    def setup(self):
        """
         Load the repos into repostore to query package dependencies
        """
        for repo in self.repos:
            self.yrepo = yum.yumRepo.YumRepository(repo['id'])
            self.yrepo.baseurl = ["file://%s/%s" % (str(util.top_repos_location()), str(repo['relative_path']))]
            self.yrepo.basecachedir = CACHE_DIR
            self._repostore.add(self.yrepo)

    def loadPackages(self):
        """
         populate the repostore with packages
        """
        self._repostore._setup = True
        self._repostore.populateSack(which='all')
        
    def cleanup(self):
        """
         clean up the repo metadata cache from /var/lib/pulp/cache/
        """
        for repo in self._repostore.repos:
            shutil.rmtree(repo.cachedir)

    def getDependencylist(self):
        """
         Get dependency list and suggested packages for package names provided.
         The dependency lookup is only one level in this case.
         The package name format could be any of the following:
         name, name.arch, name-ver-rel.arch, name-ver, name-ver-rel,
         epoch:name-ver-rel.arch, name-epoch:ver-rel.arch
        """
        ematch, match, unmatch = self._repostore.pkgSack.matchPackageNames(self.pkgs)
        pkgs = []
        for po in ematch + match:
            pkgs.append(po)
        results = self.__locateDeps(pkgs)
        return results
    
    def getRecursiveDepList(self):
        """
         Get dependency list and suggested packages for package names provided.
         The dependency lookup is recursive. All available packages in the repo
         are returned matching whatprovides.
         The package name format could be any of the following:
         name, name.arch, name-ver-rel.arch, name-ver, name-ver-rel,
         epoch:name-ver-rel.arch, name-epoch:ver-rel.arch
         returns a dictionary of {'n-v-r.a' : [n,v,e,r,a],...}
        """
        solved = []
        to_solve = self.pkgs
        result_dict = {}
        while to_solve:
            log.debug("Solving %s \n\n" % to_solve)
            results = self.getDependencylist()
            deps = self.processResults(results)
            solved += to_solve
            to_solve = []
            for dep in deps:
                name, version, epoch, release, arch = dep
                ndep = "%s-%s-%s.%s" % (name, version, release, arch)
                result_dict[ndep] = dep
                solved = list(set(solved))
                if ndep not in solved:
                    to_solve.append(ndep)
            self.pkgs = to_solve
        log.debug("difference:: %s \n\n" % list(set(to_solve) - set(solved)))
        return result_dict
                
    def __locateDeps(self, pkgs):
        results = {}
        for pkg in pkgs:
            results[pkg] = {} 
            reqs = pkg.requires
            reqs.sort()
            pkgresults = results[pkg]
            for req in reqs:
                (r,f,v) = req
                if r.startswith('rpmlib('):
                    continue
                satisfiers = []
                for po in self.__whatProvides(r, f, v):
                    satisfiers.append(po)
                pkgresults[req] = satisfiers
        return results

    def __whatProvides(self, name, flags, version):
        return ListPackageSack(self._repostore.pkgSack.searchProvides((name, flags, version)))

    def processResults(self, results):
        reqlist = []
        for pkg in results:
            if len(results[pkg]) == 0:
                continue
            for req in results[pkg]:
                rlist = results[pkg][req]
                if not rlist:
                    # Unsatisfied dependency
                    continue
                reqlist.append(rlist)
        deps = []
        for res in reqlist:
            dep = [res[0].name, res[0].version, res[0].epoch, res[0].release, res[0].arch]
            if dep not in deps:
                deps.append(dep)
        return deps
    
    def printable_result(self, results):
        print_doc_str = ""
        for pkg in results:
            if len(results[pkg]) == 0:
                continue
            for req in results[pkg]:
                rlist = results[pkg][req]
                print_doc_str += "\n dependency: %s \n" % prco_tuple_to_string(req)
                if not rlist:
                    # Unsatisfied dependency
                    print_doc_str += "   Unsatisfied dependency \n"
                    continue
                
                for po in rlist:
                    print_doc_str += "   provider: %s\n" % po.compactPrint()
        return print_doc_str


if __name__=='__main__':
    if len(sys.argv) < 3:
        print "USAGE: python depsolver.py <repoid> <pkgname> <pkgname> ..."
        sys.exit(0)
    repo = [sys.argv[1]]
    pkgs = sys.argv[2:]
    dsolve = DepSolver(repo, pkgs)
    results =  dsolve.getDependencylist()
    print dsolve.processResults(results)

