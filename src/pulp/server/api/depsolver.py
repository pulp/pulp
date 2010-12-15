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
from yum.packageSack import ListPackageSack

from pulp.server import util
from yum.misc import prco_tuple_to_string
from yum.repos import RepoStorage

CACHE_DIR = "/var/lib/pulp/cache/"

class DepSolver:
    def __init__(self, repos, pkgs=[]):
        self.pkgs = pkgs
        self.repos  = repos
        self._repostore = RepoStorage(self)
        self.setup()
        self.loadPackages()

    def setup(self):
        for repo in self.repos:
            self.yrepo = yum.yumRepo.YumRepository(repo['id'])
            self.yrepo.baseurl = ["file://%s/%s" % (str(util.top_repos_location()), str(repo['relative_path']))]
            self.yrepo.basecachedir = CACHE_DIR
            self._repostore.add(self.yrepo)

    def loadPackages(self):
        self._repostore._setup = True
        self._repostore.populateSack(which='all')
        
    def cleanup(self):
        shutil.rmtree(self.yrepo.cachedir)

    def getDependencylist(self):
        ematch, match, unmatch = self._repostore.pkgSack.matchPackageNames(self.pkgs)
        pkgs = []
        for po in ematch + match:
            pkgs.append(po)
        results = self.locateDeps(pkgs)
        return results

    def locateDeps(self, pkgs):
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
                for po in self.whatProvides(r, f, v):
                    satisfiers.append(po)
                pkgresults[req] = satisfiers
        return results

    def whatProvides(self, name, flags, version):
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

