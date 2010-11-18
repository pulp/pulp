#!/usr/bin/env python
import sys
from optparse import OptionParser

from pulp.client.connection import RepoConnection

def remove_category_names(entry):
        entries = entry.split(",")
        groups = []
        for e in entries:
            x = e.split(";")
            if len(x) < 2:
                groups.append(x)
            else:
                for group_name in x[1:]:
                    groups.append(group_name)
        return groups

def parse_packagekit_group_file(in_file):
    #based on yumComps.py of PackageKit
    groupMap = {}
    f = open(in_file, 'r')
    lines = f.readlines()
    for line in lines:
        line = line.replace('\n', '')
        if len(line) == 0:
            continue
        # fonts=base-system;fonts,base-system;legacy-fonts
        split = line.split('=')
        if len(split) < 2:
            continue
        entries = split[1].split(',')
        groupMap[split[0]] = []
        for entry in entries:
            groupMap[split[0]].extend(remove_category_names(entry))
    return groupMap

def add_pulp_categories(conn, repo_id, category_info):
    """
    conn - repo connection instance used to communicate to pulp
    repo_id - repository id to store category/group info in
    category_info - mapping of category name as key to group names as value
    """
    existing_pkggrpcats = conn.packagegroupcategories(repo_id)
    for key in category_info:
        if key not in existing_pkggrpcats:
            print "Creating package group category [%s] in repo [%s]" % (key, repo_id)
            conn.create_packagegroupcategory(repo_id,
                key, key, "%s created from package kit group data" % (key))
        for group in category_info[key]:
            print "Adding package group [%s] to category [%s] in repo [%s]" % (group, key, repo_id)
            conn.add_packagegroup_to_category(repo_id, key, group)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                  help="PackageKit Group information file",
                  default="/usr/share/PackageKit/helpers/yum/yum-comps-groups.conf")
    parser.add_option("--host", dest="host", default="localhost",
                  help="Hostname of pulp server")
    parser.add_option("--port", dest="port", default="443",
                  help="Port of pulp server")
    parser.add_option("-r", "--repo", dest="repo_id", default=None,
                  help="Pulp repository id")
    (options, args) = parser.parse_args()

    filename = options.filename
    host = options.host
    port = int(options.port)
    repo_id = options.repo_id
    if not repo_id:
        print "No repository id was specified.  Please re-run with a repository id"
        sys.exit(1)
    print "Connecting to pulp at %s:%s using repository id [%s]" % (host, port, repo_id)
    repo_connection = RepoConnection(host, port)
    repositories = [x["id"] for x in repo_connection.repositories()]
    if repo_id not in repositories:
        print "The repository id specified [%s] does not exist." % (repo_id)
        sys.exit(1)
    print "Parsing PackageKit file at [%s]" % (filename)
    category_info = parse_packagekit_group_file(filename)
    add_pulp_categories(repo_connection, repo_id, category_info)
