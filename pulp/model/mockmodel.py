from property import Property
from random import shuffle, randint

# Fake User/Subject object.
class MockSubject(object):
    firstName = "Fake"
    lastName = "User"
    name = "admin"
    factive = True
    fsystem = False
    sessionId = (-1097805654)
    emailAddress = 'nobody@localhost'
    id = 2
    
    
class MockContentSource(Property):
    '''
    ContentSource is a class representing a location to fetch packages from.
    Examples of this would be a http served yum repository or a mounted DVD drive
    '''
    def __init__(self, id):
        Property.__init__(self)
        self.id = str(id)
        self.name = "fake-source[%s]" % id
        self.url = "http://some.redhat.com/url/%s" % id
        self.contentSourceType = Property()
        self.contentSourceType.displayName  = "Fake Type"
        self.configuration = Property()
        self.configuration.properties = Property()
        self.configuration.properties.entry = []
        self.configuration.properties.entry.append(Property())
        self.configuration.properties.entry[0].value = Property()
        self.configuration.properties.entry[0].value.stringValue = \
            "http://some.redhat.com/url/%s" % id


class MockChannel(Property):
    '''
    A Channel is a collection of ContentSources.  Channels allow you to group
    ContentSources and thus repositories of packages into a logical grouping.
    
    Systems can be 'subscribed' to a Channel which implies the packages 
    contained within the Channel apply to that system.  
    '''
    def __init__(self, id):
        Property.__init__(self)
        self.id = str(id)
        self.name = "fake-channel[%s]" % id
        self.description = "mock channel description"


class MockPackageVersion(Property):
    '''
    A class representing a concrete package with a version  
    '''
    def __init__(self, id):
        Property.__init__(self)
        self.id = id
        self.name = "fake-channel[%s]" % id
        self.description = "mock channel description"
        self.id = str(id)
        self.fileName = 'fake-package-i386-' + str(id) + '.i386.rpm'
        self.name = 'fake-package-' + str(id)
        self.architecture = Property()
        self.architecture.name = 'i386'



class MockSystem(Property):
    '''
    A fake System class.  This represents a System that gets packages installed
    on it and is associated with Channels.
    '''
    def __init__(self, id):
        Property.__init__(self)
        self.resource = Property()
        self.resource.name = 'fake-system-' + str(id)
        self.resource.id = str(id)
        self.resource.description = 'Fake Linux System'
        self.packageCount = randint(1000,2000)

