from pulp.model.base import PageControl
from pulp.identity.webserviceprovider import WsUser
from random import shuffle, randint
from property import Property

class MockServiceProxy(object):
    """ This class is a mockup of the remote service interface the pulp ui 
    expects to find.  It is organized into """
    def __init__(self, url, faults=True):
        self.faults = faults
        self.url = url

    def get_instance(self, name):
        return Property()
    
    
    # AUTHENTICATION METHODS
    def login(self, username, password):
        ms = MockSubject()
        ms.name = username
        return ms
   
    #CONTENTSOURCE METHODS  
    def getAllContentSources(self, subject, pagecontrol):
        ret = []
        for i in range(15):
            source = Property()
            source.id = str(i)
            source.name = "fake-source[%s]" % i
            source.url = "http://some.redhat.com/url/%s" % i
            source.contentSourceType = Property()
            source.contentSourceType.displayName  = "Fake Type"
            ret.append(source)
        return ret
    
    def getContentSource(self, subject, id):
        source = Property()
        source.id = str(id)
        source.name = "fake-source[%s]" % id
        source.url = "http://some.redhat.com/url/%s" % id
        source.contentSourceType = Property()
        source.contentSourceType.displayName  = "Fake Type"
        source.configuration = Property()
        source.configuration.properties = Property()
        source.configuration.properties.entry = []
        source.configuration.properties.entry.append(Property())
        source.configuration.properties.entry[0].value = Property()
        source.configuration.properties.entry[0].value.stringValue = \
            "http://some.redhat.com/url/%s" % id
        return source
                        
    def updateContentSource(self, subject, source):
        return source
    
    def getPackageVersionCountFromContentSource(self, subject, id):
        return 1235
    
    def synchronizeAndLoadContentSource(self, subject, id):
        return

    # CHANNEL METHODS
    def getAllChannels(self, subject, pagecontrol):
        ret = []
        for i in range(15):
            channel = Property()
            channel.id = str(i)
            channel.name = self.random_string() + "fake-channel[%s]" % i
            ret.append(channel)
        return ret
    
    def getChannel(self, subject, id):
        channel = Property()
        channel.id = id
        channel.name = self.random_string() + "[%s]" % id
        channel.description = \
            "a Fake Channel created by a mock service implementation."
        return channel
    
    def updateChannel(self, subject, channel):
        return channel.id
    
    def createChannel(self, subject, channel):
        from random import randint
        return self.getChannel(subject, randint(1,1000))
    
    def getPackageVersionCountFromChannel(self, subject, id):
        return 1235
    
    def addContentSourcesToChannel(self, subject, id, contentSourceIds):
        return
        
    def getPackageVersionsInChannel(self, subject, id, pagecontrol):
        ret = []
        for i in range(10):
            package = Property()
            package.id = str(i)
            package.fileName = 'fake-package-i386-' + str(i) + '.i386.rpm'
            package.name = 'fake-package-' + str(i)
            package.architecture = Property()
            package.architecture.name = 'i386'
            ret.append(package)
        return ret
    
    # RESOURCE METHODS
    def findResourceComposites(self, subject, category, type, parentResourceId,\
                               searchString, pageControl):
        ret = []
        for i in range(100):
            system = Property()
            # system.id = str(i)
            # system.name = 'fake-system-' + str(i)
            system.resource = Property()
            system.resource.name = 'fake-system-' + str(i)
            system.resource.id = str(i)
            system.resource.description = 'Fake Linux System'
            system.packageCount = randint(1000,2000)
            ret.append(system)
        return ret
    
    def subscribeResourceToChannels(self, subject, systemIds, id):
        return
    
    def random_string(self):
        letters = 'abcdefghijklmnopqrstuvwxyz'
        l = list(letters)
        for i in range(10):
            shuffle(l)
        ret = ''
        for c in l:
            ret += c
        return ret
           
class MockSubject(object):
    firstName = "Fake"
    lastName = "User"
    name = "jonadmin"
    factive = True
    fsystem = False
    sessionId = (-1097805654)
    emailAddress = 'nobody@localhost'
    id = 2
    
    
def get_mock_WsUser():
    subject = MockSubject()
    return WsUser(subject.name, subject)
        
