#!/usr/bin/env python
import time
from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from optparse import OptionParser



if __name__ == "__main__":
    
    parser = OptionParser(usage="%prog [OPTIONS]", description="Test how dbrefs look")
    parser.add_option('-a', '--autoref', action='store_true', 
                help='Run with SON AutoReference Manipulators', default=False)
    parser.add_option('-r', '--num_repos', action='store', 
                help='How many repos to display, default is all', default=None)
    parser.add_option('-p', '--num_packages', action='store', 
                help='How many packages to display', default=5)
    options, args = parser.parse_args()

    connection = Connection()
    db = connection._database
    if options.autoref:
        db.add_son_manipulator(NamespaceInjector())
        db.add_son_manipulator(AutoReference(db))

    repos = db.repos
    found = repos.find()
    found_slice = found
    if options.num_repos:
        found_slice = found[:int(options.num_repos)]
    for r in found_slice:
        print "\nRepo: "
        print "\tid=%s name=%s arch=%s" % (r["id"], r["name"], r["arch"])
        print "\tsource=%s" % (r["source"])
        print "\t%s packages" % (len(r["packages"]))
        for key in r["packages"].keys()[:int(options.num_packages)]:
            pkg = r["packages"][key]
            print "\tPackage: <%s> in repo <%s>" % (pkg["packageid"], pkg["repoid"])
            print "\tversions = \n\t\t%s" % (pkg["versions"])


