#!/usr/bin/env python
import json
import sys

if __name__ == "__main__":
    raw_data = open(sys.argv[1]).read()
    repo_list = json.loads(raw_data)
    output = open("feed_urls", "w")
    for repo in repo_list:
        if repo["source"] and repo["source"]["url"]:
            output.write("%s, %s, %s, %s\n" % (repo["id"], repo["source"]["url"], repo["feed_ca"], repo["feed_cert"]))
    output.close()
