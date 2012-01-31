#!/usr/bin/python

import sys
import time
from pulp.server.db import connection
connection.initialize()
#from pulp.server import auditing
#auditing.initialize()
from pulp.server.api.repo import RepoApi
from pulp.server.api.package import PackageApi
from pulp.server.api.depsolver import DepSolver

rapi = RepoApi()
papi = PackageApi()

def recursive_deps(pnames, repos):
    solved = papi.package_dependency(pnames, repos, recursive=0)
    print "========= Non Recursive Results ============\n"
    print_deps(solved['resolved'])
    print "========= Missing Dependencies =========\n"
    print(solved['unresolved'])
    solved = papi.package_dependency(pnames, repos, recursive=1, make_tree=1)
    print "========= Recursive Results ============\n"
    print_deps(solved['resolved'])
    print "========= Missing Dependencies =========\n"
    print(solved['unresolved'])
    print "========= Dependency Tree =========\n"
    print(solved['dependency_tree'])
    print(len(solved['dependency_tree']))
def print_deps(deps):
    print "# of deps: %s\n" % len(deps)
    for dep, pkgs in deps.items():
        for pkg in pkgs:
            print make_nvrea(pkg['name'], pkg['version'], pkg['release'], pkg['arch'])

def solve_deps(pnames, repos):
    solved = []
    to_solve = pnames
    previous_to_solve = []
    while to_solve:
        #print "Solving %s \n\n" % to_solve 
        deps = papi.package_dependency(to_solve, repos)['available_packages']
        for d in to_solve:
            previous_to_solve.append(d)
            if d not in solved:
                solved.append(d)
        to_solve = []
        for dep in deps:
            ndep = make_nvrea(dep['name'], dep['version'], dep['release'], dep['arch'])
            if ndep not in previous_to_solve:
                to_solve.append(ndep)
        #print "difference:: %s \n\n" % list(set(to_solve) - set(previous_to_solve))

    print "Solved list"
    print '\n'.join(solved[:])

def make_nvrea(n, v, r, a):
    return "%s-%s-%s.%s" % (n,v,r,a)

if __name__=='__main__':
    if len(sys.argv) < 3:
        print "USAGE: python deptest.py <repoid> <pkgname> <pkgname> ..."
        sys.exit(0)
    pnames = sys.argv[2:]
    #pnames = ["cas-server-1.0-0.fc13.noarch"] #, "cas-admin-1.0-0.fc13.noarch"]
    repos = [sys.argv[1]] #["deptest"]
    #print "starting dep solve %s" % time.ctime()
    #solve_deps(pnames, repos)
    #print "End dep solve %s" % time.ctime()
    print "starting recursive solve %s" % time.ctime()
    recursive_deps(pnames, repos)
    print "End recursive solve %s" % time.ctime()


