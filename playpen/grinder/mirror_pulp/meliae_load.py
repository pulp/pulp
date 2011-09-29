#!/usr/bin/env python
import sys
from meliae import loader


if __name__ == "__main__":
    om = loader.load(sys.argv[1])
    om.remove_expensive_references()
    om.compute_referrers()
    s = om.summarize()
    print s

    max_addr = s.summaries[0].max_address
    print om[max_addr]

    print "om[%s].refs_as_dict() = %s" % (max_addr, om[max_addr].refs_as_dict())


