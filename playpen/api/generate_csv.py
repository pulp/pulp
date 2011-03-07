#!/usr/bin/env python

import hashlib
import os
import sys
from optparse import OptionParser

import pulp.server.util


def get_rpm_checksums(path):
    rpms = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".rpm"):
                fname = os.path.join(root, f)
                checksum = pulp.server.util.get_file_checksum(hashtype="sha256", filename=fname)
                rpms.append((fname,checksum))
    return rpms

def write_csv_file(data, csv_file_path):
    out_file = open(csv_file_path, "w")
    for d in data:
        out_file.write("%s,%s\n" % (d[0],d[1]))
    out_file.close()

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-d", "--dir", dest="dirpath",
                  help="Directory containing rpms to associate",
                  default=None)
    parser.add_option("-o", "--outfile", dest="outfile",
                  help="CVS file to write output to",
                  default=None)
    (options, args) = parser.parse_args()
    if not options.dirpath:
        print "Please re-run with a directory to read for rpm files"
        parser.print_help()
        sys.exit(1)
    if not options.outfile:
        print "Please re-run with an output file specified."
        parser.print_help()
        sys.exit(1)
    print "Will read %s and write to %s" % (options.dirpath, options.outfile)
    rpm_checksums = get_rpm_checksums(options.dirpath)
    write_csv_file(rpm_checksums, options.outfile)
    print "Processed %s rpms." % (len(rpm_checksums))


