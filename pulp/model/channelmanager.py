from suds.property import Property
from pulp.model.pulpserviceproxy import PulpServiceProxy 
import logging

class ChannelManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ContentSourceManagerBean')
    
    def get_channel(self, subject, id):
        source = self.service.getChannel(subject, id)
        return source
    
    def list_all_channels(self, subject):
        return self.service.getAllChannels(subject, PageControl())
        
    def update_channel(self, subject, id, name, displayName, description):
                
        channel = self.service.getChannel(subject, id)
        print "we got a channel : ", channel.id
        channel.name = name
        channel.displayName = displayName
        channel.description = description
        self.service.updateChannel(subject, channel)
        return id

    def create_channel(self, subject, name, displayName, description):
        channel = Property()
        channel.name = name
        channel.displayName = displayName
        channel.description = description
        channel = self.service.createChannel(subject, channel)
        print "we got a channel: ", channel.id
        return channel.id
                
    def add_content_source(self, subject, id, contentSourceIds):
        self.service.addContentSourcesToChannel(subject, id, contentSourceIds)
            
    def list_packages_in_channel(self, subject, id):
        versions = self.service.getPackageVersionsInChannel(subject, id, \
                                                        PageControl())
        for v in versions:
            v.arch = v.architecture.name
        #    print "Type: ", s.type

        return versions
                    
    def get_package_count(self, subject, id):
        return self.service.getPackageVersionCountFromChannel(subject, id)                      

class PageControl(Property):
    def __init__(self):
        Property.__init__(self)
        #super(PageControl).__init__()
        self.pageNumber = 0
        self.pageSize = 100


