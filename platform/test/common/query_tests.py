import sys
sys.path.append("../../src")
import random
import time
import re

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.package import PackageApi
from pulp.server.api.repo import RepoApi

TEST_PACKAGE_ID = 'random-package'

capi = ConsumerApi(dict())
papi = PackageApi(dict())
rapi = RepoApi(dict())

print "finding one consumer"
c = capi.collection.find_one()

start = time.time()
found = capi.consumer(c['id'])
cFindTime = time.time() - start

start = time.time()
print "finding consumers with package installed"
clist = capi.consumers_with_package_name(TEST_PACKAGE_ID)
print "Length: %s" % len(clist)
clist = [found]
packageFindTime = time.time() - start

consumerWithPackage = random.choice(clist)
repo = rapi.collection.find_one()
if repo['id'] in consumerWithPackage['repoids']:
    pass
else:
    consumerWithPackage['repoids'].append(repo['id'])
    capi.update(consumerWithPackage)

start = time.time()
regex = re.compile(".*%s" % repo['id'])
key = "package_profile.%s" % TEST_PACKAGE_ID
found = list(capi.collection.find({"repoids": regex, key: {"$exists": True}}))
packageAndRepoFind = time.time() - start
print "Num consumers found with repo: %s" % len(found)


print "time to find consumer by id                     : [%s]" % cFindTime
print "time to find consumers with a specific package  : [%s]" % packageFindTime
print "time to find consumer package + bound to repo   : [%s]" % packageAndRepoFind




