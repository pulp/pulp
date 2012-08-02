#!/usr/bin/env python

import json
import sys

if __name__ == "__main__":
    applicable = []
    non_applicable = []
    data = json.load(sys.stdin)
    for consumer_id in data:
        item = data[consumer_id][0]
        if item["applicable"]:
            old_rpms = []
            for pkg_name, info in item["details"]["upgrade_details"].items():
                old_rpm = info["installed"]
                old_nevra = "%s:%s-%s-%s.%s" % (old_rpm["name"], old_rpm["epoch"], old_rpm["version"], old_rpm["release"], old_rpm["arch"])
                new_rpm = info["available"]
                new_nevra = "%s:%s-%s-%s.%s" % (new_rpm["name"], new_rpm["epoch"], new_rpm["version"], new_rpm["release"], new_rpm["arch"])
                old_rpms.append((old_nevra, new_nevra))
            applicable.append((consumer_id, old_rpms))
        else:
            non_applicable.append(consumer_id)
    print "Applicable to below consumers:"
    for item in applicable:
        consumer_id = item[0]
        print "\n%s" % (consumer_id)
        for rpm_info in item[1]:
            old_rpm = rpm_info[0]
            new_rpm = rpm_info[1]
            print "\tNew RPM: %s would upgrade %s" % (new_rpm, old_rpm)

