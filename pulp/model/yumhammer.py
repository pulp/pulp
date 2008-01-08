from pulp.model.base import PageControl
from pulp.identity.webserviceprovider import WsUser
from property import Property

import yaml
import os
import os.path

class YumHammer(object):
    """ 
    Yum Hammer is like the hammer of Thor, expect it is Yum, not Thor.
    You will take your packages and you will like them.
    """

    def __init__(self, url, faults=True):
        self.faults = faults
        self.url = url # not actually used, it is local
        self.__load()

    def __load(self):
        """
        Load data from saved configuration into memory.
        Called on init only.
        """
        fd = open("/var/lib/pulp/config")
        data = fd.read()
        datastruct = yaml.load(data).next()
        fd.close()
        self.config = Property(datastruct)

    def __save(self):
        """
        Save changes from memory into configuration.
        FIXME: eventually we'll want a storage backend that 
               allows single-record writes
        """
        if not os.path.exists("/var/lib/pulp/config"):
            os.makedirs("/var/lib/pulp")
        fd = open("/var/lib/pulp/config","w+")
        encoded = yaml.dump(self.config.dict())
        fd.write(encoded)
        fd.close()

    def get_instance(self, name):
        return Property()
    
    def login(self, username, password):
        ms = MockSubject()
        ms.name = username
        return ms
   
    def getAllContentSources(self, subject, pagecontrol):
        #ret = []
        #for i in range(15):
        #    source = Property()
        #    source.id = str(i)
        #    source.name = "YUMMATRON fake-source[%s]" % i
        #    source.displayName = "YUMMATRON fake display name [%s]" % i
        #    source.url = "http://some.fedora.org/url/%s" % i
        #    source.contentSourceType = Property()
        #    source.contentSourceType.displayName  = "Fake Type"
        #    ret.append(source)
        #return ret
        return self.config.contentSources    

    def getContentSource(self, subject, id):
        #source = Property()
        #source.id = str(id)
        #source.name = "YUMMATRON fake-source[%s]" % id
        #source.displayName = "YUMMATRON fake display name [%s]" % id
        #source.url = "http://some.redhat.com/url/%s" % id
        #source.contentSourceType = Property()
        #source.contentSourceType.displayName  = "Fake Type"
        #source.configuration = Property()
        #source.configuration.properties = Property()
        #source.configuration.properties.entry = []
        #source.configuration.properties.entry.append(Property())
        #source.configuration.properties.entry[0].value = Property()
        #source.configuration.properties.entry[0].value.stringValue = \
        #    "http://some.redhat.com/url/%s" % id
        #return source

        # FIXME: where does subject come in?
        return getattr(self.config.contentSources, id)               

    def updateContentSource(self, subject, source):
        
        # FIXME: add modification code
        # FIXME: add saving
        return source
    
    def getAllChannels(self, subject, pagecontrol):
        #ret = []
        #for i in range(15):
        #    channel = Property()
        #    channel.id = str(i)
        #    channel.name = self.random_string() + "fake-channel[%s]" % i
        #    channel.displayName = "YUMMATRON fake channel name [%s]" % i
        #    ret.append(channel)
        #return ret
        return self.config.channels    

    def getChannel(self, subject, id):
        #channel = Property()
        #channel.id = id
        #channel.name = self.random_string() + "[%s]" % id
        #channel.displayName = "fake channel name [%s]" % id
        #channel.description = \
        #    "a Fake YUMMATRON Channel created by a mock service implementation."
        #return channel
        return getattr(self.config.channels, id)    

    def updateChannel(self, subject, channel):
        # FIXME: modify things somehow
        # FIXME: save things
        # return channel.id
        return channel    

    def createChannel(self, subject, channel):
        #from random import randint
        
        # FIXME: create the channel
        # FIXME: save the channel
        id = 0
        return self.getChannel(subject, 0)
            
    def getPackageVersionCountFromChannel(self, subject, id):
        return 1235
    
    def getPackageVersionCountFromContentSource(self, subject, id):
        return 1235
    
    def addContentSourcesToChannel(self, subject, id, contentSourceIds):
        return
        
    def getPackageVersionsInChannel(self, subject, id, pagecontrol):
        #ret = []
        #for i in range(10):
        #    package = Property()
        #    package.id = str(i)
        #    package.fileName = 'fake-package-i386-' + str(i) + '.i386.rpm'
        #    package.name = 'fake-package-' + str(i)
        #    package.architecture = Property()
        #    package.architecture.name = 'i386'
        #    ret.append(package)
        #return ret
        
        # FIXME: for x in channels ...
        ret = []
        return ret
    

    def synchronizeAndLoadContentSource(self, subject, id):
        return
    
    def findResourceComposites(self, subject, category, type, parentResourceId,\
                               searchString, pageControl):
        ret = []
        #for i in range(100):
        #    system = Property()
        #    system.id = str(i)
        #    system.name = 'fake-system-' + str(i)
        #    system.resource = Property()
        #    system.resource.name = system.name
        #    system.description = 'Fake Linux System'
        #    ret.append(system)
        return ret
    
    def subscribeResourceToChannels(self, subject, systemIds, id):
        # FIXME:
        return 

    
    #def random_string(self):
    #    letters = 'abcdefghijklmnopqrstuvwxyz'
    #    l = list(letters)
    #    for i in range(10):
    #        shuffle(l)
    #    ret = ''
    #    for c in l:
    #        ret += c
    #    return ret
           
class MockSubject(object):
    # FIXME
    firstName = "Fake"
    lastName = "User"
    name = "jonadmin"  
    factive = True
    fsystem = False
    sessionId = (-1097805654)
    emailAddress = 'nobody@localhost'
    id = 2
    
    
def get_mock_WsUser():
    # FIXME
    subject = MockSubject()
    return WsUser(subject.name, subject)
        
