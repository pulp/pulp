# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

import logging
import re
import shutil
import yum
from yum.misc import prco_tuple_to_string
from yum.packageSack import ListPackageSack
from yum.packages import parsePackages
from yum.repos import RepoStorage

log = logging.getLogger(__name__)

CACHE_DIR="/tmp/pulp/cache"

class DepSolver:
    def __init__(self, repos, pkgs=[]):
        self.pkgs = pkgs
        self.repos = repos
        self._repostore = RepoStorage(self)
        self.setup()
        self.loadPackages()

    def setup(self):
        """
         Load the repos into repostore to query package dependencies
        """
        for repo in self.repos:
            self.yrepo = yum.yumRepo.YumRepository(repo.id) # repo['id'])
            self.yrepo.baseurl = ["file://%s" % str(repo.importer_working_dir)]  #repo['importer_working_dir'])]
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
            cachedir = "%s/%s" % (CACHE_DIR, repo)
            shutil.rmtree(cachedir)

    def getDependencylist(self):
        """
         Get dependency list and suggested packages for package names provided.
         The dependency lookup is only one level in this case.
         The package name format could be any of the following:
         name, name.arch, name-ver-rel.arch, name-ver, name-ver-rel,
         epoch:name-ver-rel.arch, name-epoch:ver-rel.arch
        """
        ematch, match, unmatch = parsePackages(self._repostore.pkgSack, self.pkgs)
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
        all_results = {}
        while to_solve:
            log.debug("Solving %s \n\n" % to_solve)
            results = self.getDependencylist()
            all_results.update(results)
            found = self.processResults(results)[0]
            solved += to_solve
            to_solve = []
            for dep, pkgs in found.items():
                for pkg in pkgs:
                    name, version, epoch, release, arch, checksumtype, checksum = pkg
                    ndep = "%s-%s-%s.%s" % (name, version, release, arch)
                    solved = list(set(solved))
                    if ndep not in solved:
                        to_solve.append(ndep)
            self.pkgs = to_solve
#        log.debug("difference:: %s \n\n" % list(set(to_solve) - set(solved)))
        return all_results

    def __locateDeps(self, pkgs):
        results = {}
        regex_filename_match = re.compile('[/*?]|\[[^]]*/[^]]*\]').match
        for pkg in pkgs:
            results[pkg] = {}
            reqs = pkg.requires
            reqs.sort()
            pkgresults = results[pkg]
            for req in reqs:
                (r, f, v) = req
                if r.startswith('rpmlib('):
                    continue
                satisfiers = []
                for po in self.__whatProvides(r, f, v):
                    # verify this po indeed provides the dep,
                    # el5 version could give some false positives
                    if regex_filename_match(r) or \
                       po.checkPrco('provides', (r, f, v)):
                        satisfiers.append(po)
                pkgresults[req] = satisfiers
        return results

    def __whatProvides(self, name, flags, version):
        try:
            return ListPackageSack(self._repostore.pkgSack.searchProvides((name, flags, version)))
        except:
            #perhaps we're on older version of yum try old style
            return ListPackageSack(self._repostore.pkgSack.searchProvides(name))

    def processResults(self, results):
        reqlist = {}
        notfound = {}
        for pkg in results:
            if len(results[pkg]) == 0:
                continue
            for req in results[pkg]:
                rlist = results[pkg][req]
                if not rlist:
                    # Unsatisfied dependency
                    notfound[prco_tuple_to_string(req)] = []
                    continue
                reqlist[prco_tuple_to_string(req)] = rlist
        found = {}
        for req, rlist in reqlist.items():
            found[req] = []
            for r in rlist:
                checksums = r.checksums
                for (checksumtype, checksum, num) in checksums:
                    dep = (r.name, r.epoch, r.version, r.release, r.arch, checksumtype, checksum)
                    if dep not in found[req]:
                        found[req].append(dep)
        return found, notfound

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

    def make_tree(self, pkgs, requires_set, results):
        """
         Returns a dependency tree structure for the requested packages

        """
        for pkg in pkgs:
            pkg_hash = {}
            ematch, match, unmatch = self._repostore.pkgSack.matchPackageNames([pkg])
            po = (ematch + match)[0]
            if not po:
                continue
            preq = po.requires
            pname = "%s-%s-%s.%s" % (po.name, po.version, po.release, po.arch)
            for req in preq:
                (r, f, v) = req
                if r.startswith('rpmlib(') or req in requires_set.values()[0]:
                    pkg_hash[req] = requires_set.values()[0][req]
                    continue
                else:
                    satisfiers = []
                    new_pkgs=[]
                    for new_po in self.__whatProvides(r, f, v):
                        new_pkgs.append("%s-%s-%s.%s" % (new_po.name, new_po.version, new_po.release, new_po.arch))
                        satisfiers.append(po)
                        requires_set[po] = req
                    pkg_hash[req] = new_pkgs
                    self.make_tree(new_pkgs, requires_set, results)
            results[pname] = pkg_hash

if __name__ == '__main__':

    repos = [{'id' : 'testrepo', 'importer_working_dir' : '/var/lib/pulp/working/testrepo/importers/yum_importer/testrepo/'}]
    dsolve = DepSolver(repos, pkgs=['pulp-server'])
    results = dsolve.getDependencylist()
    print dsolve.processResults(results)
    #print dsolve.printable_result(results)
    results = dsolve.getRecursiveDepList()
    print dsolve.processResults(results)
    #print dsolve.printable_result(results)
    dsolve.cleanup()
