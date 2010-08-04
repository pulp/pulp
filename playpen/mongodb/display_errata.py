#!/usr/bin/env python
import time
from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from optparse import OptionParser


def findRelatedPackages(db, erratum):
    found_packages = []
    for pkgdict in erratum['pkglist']:
        for pkg in pkgdict['packages']:
            queryParams = {'name':pkg['name'], 'epoch':pkg['epoch'],
                'version':pkg['version'], 'release':pkg['release'], 'arch':pkg['arch']}
            if pkg.has_key('sum') and (pkg['sum'][0] == 'sha256'):
                # Pulp only has sha256 checksums in the db
                queryParams['checksum'] = {pkg['sum'][0]:pkg['sum'][1]}
            found = db.packages.find_one(queryParams)
            if found:
                found_packages.append(found)
    return found_packages

if __name__ == "__main__":

    parser = OptionParser(usage="%prog [OPTIONS]", description="Test how dbrefs look")
    parser.add_option('-a', '--autoref', action='store_true',
                help='Run with SON AutoReference Manipulators', default=False)
    parser.add_option('--all', action='store_true', help='Dump all errata info', default=False)
    parser.add_option('--id', action='store', help='Which errata to display', default=None)
    options, args = parser.parse_args()

    connection = Connection()
    db = connection._database
    if options.autoref:
        db.add_son_manipulator(NamespaceInjector())
        db.add_son_manipulator(AutoReference(db))

    found = []
    if options.id:
        f = db.errata.find_one({"id":options.id})
        found.append(f)
    else:
        found = db.errata.find()

    if options.all or options.id != None:
        for erratum in found:
            print "\n***"
            for key in erratum.keys():
                if key == "pkglist":
                    print "pkglist: "
                    for item in erratum['pkglist']:
                        for itemKey in item.keys():
                            print "\t%s = %s" % (itemKey, item[itemKey])
                else:
                    print "%s: %s" % (key, erratum[key])
            relatedPkgs = findRelatedPackages(db, erratum)
            print "(Lookup from mongo): These packages from pulp are related:"
            for p in relatedPkgs:
                print "\t%s" % (p)
    else:
        eids = []
        for erratatum in found:
            eids.append(erratatum['id'])
        print eids

