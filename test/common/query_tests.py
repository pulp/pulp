import sys
sys.path.append("../../src")
import random
import time
import re

from pulp.api.consumer import ConsumerApi
from pulp.api.package import PackageApi
from pulp.api.package_group import PackageGroupApi
from pulp.api.package_group_category import PackageGroupCategoryApi
from pulp.api.package_version import PackageVersionApi
from pulp.api.repo import RepoApi

from pulp.model import Package
from pulp.model import PackageGroup
from pulp.model import PackageGroupCategory
from pulp.model import Consumer

TEST_PACKAGE_ID = 'random-package'

capi = ConsumerApi(dict())
papi = PackageApi(dict())
rapi = RepoApi(dict())

print "finding one consumer"
c = capi.objectdb.find_one()

start = time.time()
found = capi.consumer(c['id'])
cFindTime = time.time() - start

start = time.time()
print "finding consumers with package installed"
clist = capi.consumers_with_package_name(TEST_PACKAGE_ID)
clist = [found]
packageFindTime = time.time() - start

consumerWithPackage = random.choice(clist)
repo = rapi.objectdb.find_one()
if repo['id'] in consumerWithPackage['repoids']:
    pass
else:
    consumerWithPackage['repoids'].append(repo['id'])
    capi.update(consumerWithPackage)

start = time.time()
regex = re.compile(".*%s" % repo['id'])
key = "package_profile.%s" % TEST_PACKAGE_ID
found = list(capi.objectdb.find({"repoids": regex, key: {"$exists": True}}))
packageAndRepoFind = time.time() - start
print "Num consumers found with repo: %s" % len(found)


print "time to find consumer by id                     : [%s]" % cFindTime
print "time to find consumers with a specific package  : [%s]" % packageFindTime
print "time to find consumer package + bound to repo   : [%s]" % packageAndRepoFind



  
