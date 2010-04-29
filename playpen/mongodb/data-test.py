import pymongo
import string
import logging
import os
import random
import rpm

from pymongo import Connection

class Base(dict):
    def __init__(self):
        dict.__init__(self)
    def __getattr__(self, attr):
        return self[attr]
    def __setattr__(self, name, value):
        self[name] = value


class Repo(Base):
    def __init__(self, id, url):
        self.id = id
        self.url = url
        self.packages = []

class Package(Base):
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.versions = []

    
class Version(Base):
    def __init__(self, id, version_str):
        self.id = id
        self.version_str = version_str
        
class Consumer(Base):
    def __init__(self, id):
        self.id = id
        self.packages = []
    
    
def getRPMInformation (rpmPath):
    long_variable_name = rpm.ts();
    try:
        file_descriptor_number = os.open(rpmPath, os.O_RDONLY)
        rpmInfo = long_variable_name.hdrFromFdno(file_descriptor_number);
        os.close(file_descriptor_number)
    except:
        print "error trying to get rpm info"
        return False
    return rpmInfo


def random_string():
    # The characters to make up the random password
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for x in range(random.randint(8, 16)))     

def translate_package(info):
    p = Package(info['name'], info['description'])
    vr = info['version'] + "-" + info['release']
    v = Version(random_string(), vr)
    p.versions.append(v)
    return p
    
     
r = Repo("test-repo", "http://example.com/foo")
p = Package("test-package", "some test package")
r.packages.append(p)

####### Mongo DB ########

connection = Connection()
db = connection.test_database
collection = db.test_collection
repos = db.repos
packages = db.packages
versions = db.versions
consumers = db.consumers

## have to insert packages first, otherwise the repo object will lose track
## of the associated package.  I think the rule may be insert leaf/child docs
## first then insert the parents.
packages.insert(p)
repos.insert(r)

rs = repos.find()

for i in range(rs.count()):
    row = rs.next()
    print "stored repo: [%s]" % row
    

info = getRPMInformation("/opt/repo/sat-ng/qpidc-devel-0.1-5.M2.i386.rpm")

dir = "/opt/repo/sat-ng/"
dir = "/opt/repo/f11-i386/Packages/"
dirList=os.listdir(dir)
versions = []
package_count = 0
for fname in dirList:
    if (fname.endswith(".rpm")):
        info = getRPMInformation(dir + fname)
        # print "rpm name: %s" % info['name']
        p = translate_package(info)
        v = p.versions[0]
        # print "Got back version: %s" % v
        # versions.insert(v)
        packages.insert(p)
        r.packages.append(p)
        package_count = package_count + 1

print "Read in [%s] packages" % package_count

repos.update(
    {'id': r['id']}, 
    {'$set': {
        'packages': r.packages,
    }},
    safe=True
)

for i in range(1000):
    c = Consumer(random_string())
    c.packages = r.packages
    consumers.insert(c)

rs = consumers.find()
print "Number of Consumers: %s" % rs.count()

# versions.remove()
packages.remove()
repos.remove()
consumers.remove()



