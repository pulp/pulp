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
    
    # Login a user.
    # The Subject object is the Java backend's concept of a User
    # The MockSubject is a fake version of that user type object.
    def login(self, username, password):
        ms = MockSubject()
        ms.name = username
        return ms
   
    #CONTENTSOURCE METHODS  
    
    # Get the list of all ContentSource objects defined 
    # The PageControl is an object the Java backend expects that
    # controls the pagination and sorting of a list of objects.  It contains
    # the range of objects out of a greater set we are looking at. 
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
    
    # Get individual ContentSource.  Simple lookup
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
    
    # This gets the count of Packages a ContentSource has defined.
    # PackageVersion is an object that represents a distinct 
    # version of a package: kernel-2.6.22.1-27.fc7
    def getPackageVersionCountFromContentSource(self, subject, id):
        return 1235
    
    # Tell the ContentSource you want to sync the content from its 
    # repository NOW
    def synchronizeAndLoadContentSource(self, subject, id):
        return

    # CHANNEL METHODS
    # List of all Channels defined
    def getAllChannels(self, subject, pagecontrol):
        ret = []
        for i in range(15):
            channel = Property()
            channel.id = str(i)
            channel.name = self.random_string() + "fake-channel[%s]" % i
            ret.append(channel)
        return ret
    
    # Get individual Channel
    def getChannel(self, subject, id):
        channel = Property()
        channel.id = id
        channel.name = self.random_string() + "[%s]" % id
        channel.description = \
            "a Fake Channel created by a mock service implementation."
        return channel
    
    # Update individual Channel
    def updateChannel(self, subject, channel):
        return channel.id
    
    # Create a Channel
    def createChannel(self, subject, channel):
        from random import randint
        return self.getChannel(subject, randint(1,1000))
    
    # Get the count of Packages definied in a Channel
    def getPackageVersionCountFromChannel(self, subject, id):
        return 1235
    
    # This is a key method that associates a ContentSource to a Channel
    # A Channel can have many content sources associated with it.  For 
    # example you could have a base RHEL 5 yum repo + an EPEL yum repo as
    # 2 content sources.  With this method you could add both to create a 
    # single Channel organization of content.
    def addContentSourcesToChannel(self, subject, id, contentSourceIds):
        return
        
    # Get the list of Packages in a Channel.  
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
    # NOTE: Resource is the Java backend's abstract name for a System
    
    # List all the Resources defined in the system. Basically the list of
    # Systems.
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
    
    # Subscribe a System to a set of Channels.
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
           
# Fake User/Subject object.
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
        
