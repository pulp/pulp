
class MockServiceProxy(object):
    """ a mock service proxy"""
    def __init__(self, url, faults=True):
        self.faults = faults
        self.url = url

    def login(self, username, password):
        ms = MockSubject()
        ms.name = username
        return ms
    
class MockSubject(object):
    firstName = "Fake"
    lastName = "User"
    name = "jonadmin"
    factive = True
    fsystem = False
    sessionId = (-1097805654)
    emailAddress = 'nobody@localhost'
    id = 2
    
        