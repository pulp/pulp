from pulp.identity.webserviceprovider import WsUser
from random import shuffle, randint
from property import Property
from mockmodel import MockSubject, MockContentSource, MockChannel, MockSystem,\
                      MockPackageVersion

class MockServiceProxy(object):
    """ This class is a mockup of the remote service interface the pulp ui 
    expects to find.  It is organized into """
    def __init__(self, url, faults=True):
        self.faults = faults
        self.url = url

    def get_instance(self, name):
        return Property()
    
    
    # 
    # AUTHENTICATION METHODS
    #
    
    def login(self, username, password):
        '''
        Login a user.
        The Subject object is our concept of a User
        The MockSubject is a fake version of that user type object.  This method
        should validate the username and password combination to determine if
        the user is valid or not.  If the user is valid we return a Subject 
        object who's structure is defined below in MockSubject.
                
        If the login is invalid return None.
        
        @param username: username of user wanting to login
        @param password: password of user wanting to login
        @return: MockSubject object if correctly logged in or None if its an 
        invalid login 
        '''
        ms = MockSubject()
        ms.name = username
        return ms
   
    #    
    # CONTENTSOURCE METHODS
    #  
    
    def getAllContentSources(self, subject, pagecontrol):
        '''
        Get the list of all ContentSource objects defined 
        
        The PageControl is an object the backend expects that
        controls the pagination and sorting of a list of objects.  It contains
        the range of objects out of a greater set we are looking at.  See 
        base.py : PageControl 
        
        @param subject: The Subject (user) who is wanting the list of all the 
        ContentSource objects.  
        @param pagecontrol: PageControl object that dictates the range/subset
        of objects out of the greater set we are looking at.
        @return: list of ContentSource objects. 
        '''

        ret = []
        for i in range(15):
            source = MockContentSource(i)
            ret.append(source)
        return ret
    
    def getContentSource(self, subject, id):
        '''
        Get individual ContentSource.  Simple lookup.
        @param subject: user requesting ContentSource
        @param id: unique identifier of the ContentSource 
        '''
        source = MockContentSource(id)
        return source
                        
    def updateContentSource(self, subject, source):
        '''
        Update fields on an existing ContentSource object.  If you want to change
        the name, the URL or any of the settings on the ContentSource 
        '''
        return source
    
    def getPackageVersionCountFromContentSource(self, subject, id):
        '''
        This gets the count of Packages a ContentSource has defined.
        PackageVersion is an object that represents a distinct 
        version of a package: kernel-2.6.22.1-27.fc7
        
        @return count of unique packages in ContentSource
        '''
        return 1235
    
    def synchronizeAndLoadContentSource(self, subject, id):
        '''
        Tell the ContentSource you want to sync the content from its 
        epository NOW.  This is most likely a long running process so this
        should be async in nature
        
        @param subject: user wanting to sync
        @param id: unique id of ContentSource you want to sync 
        '''
        return

    #
    # CHANNEL METHODS
    #
    def getAllChannels(self, subject, pagecontrol):
        '''
        List of all Channels defined.
        '''
        ret = []
        for i in range(15):
            channel = MockChannel(i)
            ret.append(channel)
        return ret
    
    # Get individual Channel
    def getChannel(self, subject, id):
        channel = MockChannel(id)
        return channel
    
    # Update individual Channel
    def updateChannel(self, subject, channel):
        return channel.id
    
    # Create a Channel
    def createChannel(self, subject, channel):
        from random import randint
        return self.getChannel(subject, randint(1,1000))
    
    # Get the count of Packages definied in a Channel
    def getPackageVersionCountFromChannel(self, subject, filter, id):
        return 1235
    
    # This is a key method that associates a ContentSource to a Channel
    # A Channel can have many content sources associated with it.  For 
    # example you could have a base RHEL 5 yum repo + an EPEL yum repo as
    # 2 content sources.  With this method you could add both to create a 
    # single Channel organization of content.
    def addContentSourcesToChannel(self, subject, id, contentSourceIds):
        return
        
    # Get the list of Packages in a Channel.  
    def getPackageVersionsInChannel(self, subject, id, filter, pagecontrol):
        ret = []
        for i in range(1000):
            package = MockPackageVersion(i)
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
            system = MockSystem(i)
            ret.append(system)
        return ret
    
    # Subscribe a System to a set of Channels.
    def subscribeResourceToChannels(self, subject, systemIds, id):
        return
    
    def deployPackages(self, subject, systemIds, packageIds):
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
           
def get_mock_WsUser():
    subject = MockSubject()
    return WsUser(subject.name, subject)
        
