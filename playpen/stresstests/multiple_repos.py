#!/usr/bin/env python

import os
import sys
from optparse import OptionParser

def form_id(repo_id, index):
    return "%s_%s" % (repo_id, index)

def run_command(cmd):
    print cmd
    os.system(cmd)

def sync_multiple_repos(num_repos, repo_id):
    for i in range(0, num_repos):
        tmp_id = form_id(repo_id, i)
        cmd = "pulp-admin repo sync --id %s" % (tmp_id)
        run_command(cmd)

def cancel_multiple_repos(num_repos, repo_id):
    for i in range(0, num_repos):
        tmp_id = form_id(repo_id, i)
        cmd = "pulp-admin repo cancel_sync --id %s" % (tmp_id)
        run_command(cmd)

def delete_multiple_repos(num_repos, repo_id):
    for i in range(0, num_repos):
        tmp_id = form_id(repo_id, i)
        cmd = "pulp-admin repo delete --id %s" % (tmp_id)
        run_command(cmd)

def create_multiple_repos(num_repos, repo_id, feed_url=None, 
        feed_ca=None, feed_cert=None, feed_key=None, preserve_metadata=True):
    for i in range(0, num_repos):
        tmp_id = form_id(repo_id, i)
        cmd = "pulp-admin repo create --id %s --relativepath %s" % (tmp_id, tmp_id)
        if feed_url:
            cmd += " --feed=%s" % (feed_url)
        if feed_ca:
            cmd += " --feed_ca=%s" % (feed_ca)
        if feed_cert:
            cmd += " --feed_cert=%s" % (feed_cert)
        if feed_key:
            cmd += " --feed_key=%s" % (feed_key)
        if preserve_metadata:
            cmd += " --preserve_metadata"
        run_command(cmd)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--num", dest="num_repos", help="Number of Repos to create")
    parser.add_option("--repo_id", dest="repo_id", help="Base repo_id to use")
    parser.add_option("--feed", dest="feed", help="Repo Feed URL")
    parser.add_option("--feed_ca", dest="feed_ca", help="Repo Feed CA")
    parser.add_option("--feed_cert", dest="feed_cert", help="Repo Feed Cert")
    parser.add_option("--feed_key", dest="feed_key", help="Repo Feed Key")
    parser.add_option("--clean", dest="clean", action="store_true", help="Clean up and delete the associated repositories", default=False)
    parser.add_option("--cancel", dest="cancel", action="store_true", help="Cancel Syncs", default=False)
    parser.add_option("--sync", dest="sync", action="store_true", help="Initiate Sync", default=False)
    (options, args) = parser.parse_args()
    
    if options.num_repos == None:
        parser.print_help()
        print "Please re-run with number of repos specified"
        sys.exit(1)
    try:
        num_repos = int(options.num_repos)
    except:
        parser.print_help()
        print "Please re-run with a positive integer entered for number of repos"
        sys.exit(1)
    if options.repo_id == None:
        parser.print_help()
        print "Please re-run with a starting repo_id specified"
        sys.exit(1)
    if options.clean:
        delete_multiple_repos(int(options.num_repos), options.repo_id)
    else:
        if options.cancel:
            sync_multiple_repos(int(options.num_repos), options.repo_id)
        elif options.sync:
            cancel_multiple_repos(int(options.num_repos), options.repo_id)
        else:
            create_multiple_repos(int(options.num_repos), options.repo_id, options.feed, options.feed_ca, options.feed_cert, options.feed_key, True)
