#!/usr/bin/env python
import os
import sys
from optparse import OptionParser

def create_links(source_rpm, num_links, prefix):
    print "Create %s links to %s" % (num_links, source_rpm)
    for index in range(num_links):
        temp_name = "%s-%s.rpm" % (prefix, index)
        if not os.path.exists(temp_name):
            os.symlink(source_rpm, temp_name)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-n', '--num', action='store', help="Number of links to create", default=100)
    parser.add_option('-p', '--prefix', action='store', help="Prefix for link name", default="temp_link")
    parser.add_option('-s', '--source', action='store', help="Source RPM", default=None)
    options, args = parser.parse_args()
    if not options.source:
        print "Please re-run with --source"
        sys.exit(1)
    if not os.path.exists(options.source):
        print "Please re-run with RPM that exists for --source"
        sys.exit(1)
    try:
        num = int(options.num)
    except:
        print "Please re-run with an integer for --num"
        sys.exit(1)
    create_links(options.source, num, options.prefix)
