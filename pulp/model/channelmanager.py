from suds.property import Property
from pulp.model.pulpserviceproxy import PulpServiceProxy 
import logging

class ChannelManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ContentSourceManagerBean')
    
    def get_channel(self, subject, id):
        source = self.service.getChannel(id)
        return source
    
    def list_all_channels(self, subject):
        return self.service.getAllChannels(subject)
        
    def update_channel(self, subject, id, name, displayName, description):
                
        channel = self.service.getChannel(id)
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
                
    
