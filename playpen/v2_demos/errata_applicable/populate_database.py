#!/usr/bin/env python
import random
import sys

from optparse import OptionParser
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.db import connection
from pulp.server.db.model.consumer import UnitProfile
from pulp.server.exceptions import DuplicateResource, MissingResource
from pulp.server.managers import factory
from pulp_rpm.common.ids import TYPE_ID_RPM, TYPE_ID_DISTRIBUTOR_YUM

SerialNumber.PATH = '/tmp/sn.dat'
connection.initialize()
factory.initialize()
CONSUMER_MGR = factory.consumer_manager()
PROFILE_MGR = factory.consumer_profile_manager()
CONSUMER_BIND_MGR = factory.consumer_bind_manager()

def get_consumer_id(prefix, index, count):
    value = str(index)
    desired_length = len(str(count))
    num_length = len(value)
    needed_padding = desired_length - num_length
    for i in range(0, needed_padding):
        value = "0"+value
    return "%s_%s" % (prefix, value)

def get_even_profile():
    random_num = random.randint(0,1000)
    profile = [{
            "vendor": "Pulp Team",
            "name": "test-package",
            "epoch": 0,
            "version": "0.0.%s" % (random_num),
            "release": "1.el6",
            "arch": "noarch",
            }]
    return profile

def get_odd_profile():
    profile = [{
            "vendor": "Pulp Team",
            "name": "somethingelse",
            "epoch": 0,
            "version": "0.1",
            "release": "1.el6",
            "arch": "noarch",
            }]
    return profile

def delete_consumers(prefix, num):
    print "Consumers will be deleted with consumer id prefix <%s> from 0-%s" % (prefix, num)
    for index in range(0, num):
        consumer_id = get_consumer_id(prefix, index, num)
        try:
            consumer = CONSUMER_MGR.get_consumer(consumer_id)
            CONSUMER_MGR.unregister(consumer_id)
            PROFILE_MGR.consumer_deleted(consumer_id)
            print "Removed consumer: [%s]" % (consumer_id)
        except MissingResource, e:
            # skip deleting this consumer, it doesn't exists
            pass

def create_consumers(prefix, num, repo_id):
    print "Create Consumers with id prefix <%s> from 0-%s" % (prefix, num)
    for index in range(0, num):
        consumer_id = get_consumer_id(prefix, index, num)
        try:
            CONSUMER_MGR.register(consumer_id)
        except DuplicateResource:
            # Consumer already exists
            pass
        profile = None
        if index % 2 == 0:
            profile = get_even_profile()
        else:
            profile = get_odd_profile()
        PROFILE_MGR.update(consumer_id, TYPE_ID_RPM, profile)
        CONSUMER_BIND_MGR.bind(consumer_id, repo_id, TYPE_ID_DISTRIBUTOR_YUM)
        print "Created consumer: [%s] bound to [%s]" % (consumer_id, repo_id)

if __name__ == "__main__":
    factory.initialize()
    # Parse args and determine how many consumers
    # What is the prefix of each consumer id
    consumer_id_prefix = "test_consumer"
    parser = OptionParser()
    parser.add_option('--id', action='store', 
            help="Consumer ID Prefix %s" % consumer_id_prefix, default=consumer_id_prefix)
    parser.add_option('--num', action='store', 
            help="Number of consumers to create", default=1)
    parser.add_option('--repo-id', action='store', 
            help="Repo ID to bind to consumer", default=None)
    parser.add_option('--delete', action='store_true', 
            help="Delete consumers matching the passed in parameters")
    (opts, args) = parser.parse_args()
    consumer_id_prefix = opts.id
    if not consumer_id_prefix:
        print "Missing required option of --id"
        sys.exit()
    num_consumers = int(opts.num)
    if opts.delete:
        delete_consumers(consumer_id_prefix, num_consumers)
        sys.exit()

    repo_id = opts.repo_id
    if not repo_id:
        print "Missing required option of --repo-id"
        sys.exit()
    create_consumers(consumer_id_prefix, num_consumers, repo_id)
