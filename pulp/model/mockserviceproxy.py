from pulp.identity.webserviceprovider import WsUser
from suds.property import Property

class MockServiceProxy(object):
    """ a mock service proxy"""
    def __init__(self, url, faults=True):
        self.faults = faults
        self.url = url

    def login(self, username, password):
        ms = MockSubject()
        ms.name = username
        return ms
    
    def getAllContentSources(self, subject):
        ret = []
        for i in range(15):
            source = Property()
            source.id = str(i)
            source.name = "fake-source[%s]" % i
            source.displayName = "fake display name [%s]" % i
            source.url = "http://some.redhat.com/url/%s" % i
            source.contentSourceType = Property()
            source.contentSourceType.displayName  = "Fake Type"
            ret.append(source)
        return ret
    
    def getContentSource(self, id):
        source = Property()
        source.id = str(id)
        source.name = "fake-source[%s]" % id
        source.displayName = "fake display name [%s]" % id
        source.url = "http://some.redhat.com/url/%s" % id
        source.contentSourceType = Property()
        source.contentSourceType.displayName  = "Fake Type"
        source.configuration = Property()
        source.configuration.properties = Property()
        source.configuration.properties.entry = Property()
        source.configuration.properties.entry.value = Property()
        source.configuration.properties.entry.value.stringValue = "http://some.redhat.com/url/%s" % id
        return source
                        
    def updateContentSource(self, subject, source):
        return source
    
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
        