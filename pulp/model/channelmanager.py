from pulp.model.base import get_page_control, get_new_channel
from pulp.model.systemmanager import SystemManager
from pulp.model.pulpserviceproxy import PulpServiceProxy 
import logging

log = logging.getLogger("pulp.model.channelmanager")

class ChannelManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ChannelManagerBean')
    
    def get_channel(self, subject, id):
        source = self.service.getChannel(subject, id)
        return source
    
    def list_all_channels(self, subject):
        log.debug("Calling list all channels")
        pagecontrol = get_page_control()
        pagecontrol['pageSize'] = -1
        return self.service.getAllChannels(subject, pagecontrol)
        
    def update_channel(self, subject, id, name, description):
                
        channel = self.service.getChannel(subject, id)
        log.debug("we got a channel : ", channel.id)
        channel.name = name
        channel.description = description
        self.service.updateChannel(subject, channel)
        return id

    def create_channel(self, subject, name, description):
        channel = get_new_channel(name, description)
        channel = self.service.createChannel(subject, channel)
        log.debug("we got a channel: ", channel.id)
        return channel.id
                
    def add_content_source(self, subject, id, contentSourceIds):
        self.service.addContentSourcesToChannel(subject, id, contentSourceIds)
            
    def list_packages_in_channel(self, subject, id, search):
        versions = self.service.getPackageVersionsInChannel(subject, id, \
                                                        get_page_control())
        # TODO: SORTING
        for v in versions:
            v.arch = v.architecture.name

        return versions

    def list_systems_subscribed(self, subject, id, search):
        return SystemManager().list_systems(subject)
    
    def subscribe_systems(self, subject, id, systemIds):
        self.service.subscribeResourceToChannels(subject, systemIds, id)
                    
    def get_package_count(self, subject, id):
        return self.service.getPackageVersionCountFromChannel(subject, id)                      

