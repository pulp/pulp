#!/usr/bin/env python

import ConfigParser
import os
import sys

from base import get_parser, run_command

def get_repo_info(config_file="config_test_repos.cfg"):
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    repos = {}
    for repo_id in config.sections():
        repos[repo_id] = {"id":repo_id}
        for item,value in config.items(repo_id):
            repos[repo_id][item] = value
    return repos

def create_test_repo(repo_id, repo_feed, ca_cert, client_cert, client_key):
    cmd = "sudo pulp-admin repo create --id %s --feed %s --consumer_ca %s --consumer_cert %s --consumer_key %s" % \
            (repo_id, repo_feed, ca_cert, client_cert, client_key)
    return run_command(cmd)

def sync_test_repo(repo_id):
    cmd = "sudo pulp-admin repo sync --id %s -F" % (repo["id"])
    return run_command(cmd)

if __name__ == "__main__":
    parser = get_parser(description="Creat test repos", 
            limit_options=['ca_cert', 'client_key', 'client_cert'])
    (opts, args) = parser.parse_args()

    client_key = opts.client_key
    client_cert = opts.client_cert
    ca_cert = opts.ca_cert

    repos = get_repo_info()
    for repo in repos.values():
        if not create_test_repo(repo["id"], repo["feed"], ca_cert, client_cert, client_key):
            print "Failed to create repo <%s> with feed <%s>" % (repo["id"], repo["feed"])
            sys.exit(1)
        if not sync_test_repo(repo["id"]):
            print "Failed to sync repo <%s>" % (repo["id"])
            sys.exit(1)
