import datetime
import time
import optparse
import pymongo
import string
import logging
import os
import random
import rpm

from pymongo.binary import Binary
from pymongo import Connection
from pymongo.son_manipulator import SONManipulator

class CustomRepo(object):
    def __init__(self, url):
        self.__url = url

    def url(self):
        return self.__url

#def to_binary(custom):
#    return Binary(str(custom.x()), 128)
    
#def from_binary(binary):
#    return CustomRepo(int(binary))
    
def encode_custom(custom):
   return {"_type": "customrepo", "url": custom.url()}

def decode_custom(document):
    assert document["_type"] == "customrepo"
    return CustomRepo(document["url"])
  
class Transform(SONManipulator):
    def transform_incoming(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, CustomRepo):
                son[key] = encode_custom(value)
            elif isinstance(value, dict): # Make sure we recurse into sub-docs
                son[key] = self.transform_incoming(value, collection)
        return son

    def transform_outgoing(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, dict):
                if "_type" in value and value["_type"] == "customrepo":
                    son[key] = decode_custom(value)
                else: # Again, make sure to recurse into sub-docs
                    son[key] = self.transform_outgoing(value, collection)
        return son
    

#class TransformToBinary(SONManipulator):
    #def transform_incoming(self, son, collection):
        #for (key, value) in son.items():
            #if isinstance(value, CustomRepo):
                #son[key] = to_binary(value)
            #elif isinstance(value, dict):
                #son[key] = self.transform_incoming(value, collection)
        #return son

#def transform_outgoing(self, son, collection):
    #for (key, value) in son.items():
        #if isinstance(value, Binary) and value.subtype == 128:
            #son[key] = from_binary(value)
        #elif isinstance(value, dict):
            #son[key] = self.transform_outgoing(value, collection)
    #return son


class Test(object):
    def __init__(self):
        pass

class Base2(dict):
    def __init__(self):
        dict.__init__(self)
    def __getattr__(self, attr):
        return self[attr]
    def __setattr__(self, name, value):
        self[name] = value

class Base(dict):
    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__


class Repo(Base):
    def __init__(self, id, url):
        self.id = id
        self.url = url
        self.packages = dict()

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
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.packages = dict()
        self.packageids = []
    
    
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


def randomString():
    # The characters to make up the random password
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for x in range(random.randint(8, 16)))     

def translate_package(info):
    p = Package(info['name'], info['description'])
    vr = info['version'] + "-" + info['release']
    v = Version(randomString(), vr)
    p.versions.append(v)
    return p
 
##### MAIN #####

parser = optparse.OptionParser()
parser.add_option('--clean', dest='clean', action='store_true', help='Clean db')
parser.add_option('--skipcreate', dest='skipcreate', action='store_true', help='Skip object creation')
cmdoptions, args = parser.parse_args()
clean = cmdoptions.clean
skipcreate = cmdoptions.skipcreate
# skipcreate = True

####### Mongo DB ########
connection = Connection()
db = connection.test_database
collection = db.test_collection
repos = db.repos
packages = db.packages
versions = db.versions
consumers = db.consumers

r = Repo("test-repo", "http://example.com/foo")
p = Package("test-package", "some test package")
r.packages[p.id] = p
repos.insert(r)


consumers.create_index([("id", pymongo.DESCENDING)])

if (clean):
    # versions.remove()
    packages.remove()
    repos.remove()
    consumers.remove()
    connection.drop_database(db)
    print "Cleaned all old data"
    exit(0)
    

## have to insert packages first, otherwise the repo object will lose track
## of the associated package.  I think the rule may be insert leaf/child docs
## first then insert the parents.
# packages.insert(p)

# rs = repos.find()
# for i in range(rs.count()):
#    row = rs.next()
#    print "stored repo: [%s]" % row
    
last_desc = None
last_id = None

if (not skipcreate): 
    dir = "/opt/repo/sat-ng/"
    # dir = "/opt/repo/f11-i386/Packages/"
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
            r.packages[p.id] = p
            package_count = package_count + 1
            if (package_count % 500 == 0):
                    print "read [%s] packages" % package_count

    print "Read in [%s] packages" % package_count

    repos.update(
        {'id': r['id']}, 
        {'$set': {
            'packages': r.packages,
        }},
        safe=True
    )

    last_desc = None
    last_id = None
    for i in range(1000):
        c = Consumer(randomString(), randomString())
        # c.packages = r.packages
        for pid in r.packages:
            c.packages[pid] = r.packages[pid]
            c.packageids.append(pid)
        if (i % 100 == 0):
            print "Inserted [%s] consumers" % i
            p = Package('random-package', 'random package to be found')
            c.packages[p.id] = p
        consumers.insert(c)
        last_desc = c.description
        last_id = c.id
        

t1 = time.time()
rs = consumers.find()
print "Number of Consumers: %s" % rs.count()
t2 = time.time()
print "Elapsed time: [%s]" % (t2 - t1)

t1 = time.time()
print "Searching for specific id: [%s]" % last_id
rs = consumers.find({'id': last_id})
print "Number of Consumers found in id search %s" % rs.count()
t2 = time.time()
print "Elapsed time: [%s]" % (t2 - t1)

t1 = time.time()
print "Searching for specific description: [%s]" % last_desc
rs = consumers.find({'description': last_desc})
print "Number of Consumers found in desc search %s" % rs.count()
t2 = time.time()
print "Elapsed time: [%s]" % (t2 - t1)

tp = Package('tp1','tp1')
c = Consumer("search me", "searched")
c.packages[tp.id] = tp
consumers.insert(c)

list(consumers.find({"id":  "search me"}))
# 
## How to search for a package id in a consumer!
list(consumers.find({"packages.tp1.id":  {"$exists": True}}))

# Example doc from:
# http://stackoverflow.com/questions/2495932/filtering-documents-against-a-dictionary-key-in-mongodb
doc = {
    'category': 'Legislature', 
    'updated': datetime.datetime(2010, 3, 19, 15, 32, 22, 107000), 
    'byline': None, 
    'tags': {
        'party': ['Peter Hoekstra', 'Virg Bernero', 'Alma Smith', 'Mike Bouchard', 'Tom George', 'Rick Snyder'], 
        'geography': ['Michigan', 'United States', 'North America']
    }, 
    'subdoc': {'blippy': 'baz', 'foo': 'bar'},
    'headline': '2 Mich. gubernatorial candidates speak to students', 
    'text': [
        'BEVERLY HILLS, Mich. (AP) \u2014 Two Democratic and Republican gubernatorial candidates found common ground while speaking to private school students in suburban Detroit', 
        "Democratic House Speaker state Rep. Andy Dillon and Republican U.S. Rep. Pete Hoekstra said Friday a more business-friendly government can help reduce Michigan's nation-leading unemployment rate.", 
        "The candidates were invited to Detroit Country Day Upper School in Beverly Hills to offer ideas for Michigan's future.", 
        'Besides Dillon, the Democratic field includes Lansing Mayor Virg Bernero and state Rep. Alma Wheeler Smith. Other Republicans running are Oakland County Sheriff Mike Bouchard, Attorney General Mike Cox, state Sen. Tom George and Ann Arbor business leader Rick Snyder.', 
        'Former Republican U.S. Rep. Joe Schwarz is considering running as an independent.'
    ], 
    'dateline': 'BEVERLY HILLS, Mich.', 
    'published': datetime.datetime(2010, 3, 19, 8, 0, 31), 
    'keywords': "Governor's Race", 
    'article_id': 'urn:publicid:ap.org:0611e36fb084458aa620c0187999db7e', 
    'slug': "BC-MI--Governor's Race,2nd Ld-Writethr"
}
