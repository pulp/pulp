from property import Property

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
    def __init__(self):
        property.Property.__init__(self)
