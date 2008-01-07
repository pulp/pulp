from property import Property
from pulp.model.pulpserviceproxy import PulpServiceProxy 
import logging

log = logging.getLogger("pulp.model")

class ContentManager(object):
    
    def __init__(self):
        self.service = PulpServiceProxy().getServiceProxy('ContentSourceManagerBean')
    
    def get_content_source(self, subject, id):
        source = self.service.getContentSource(subject, id)
        return source
    
    def list_all_content_sources(self, subject):
        sources = self.service.getAllContentSources(subject, subject)
        for s in sources:
            s.type = s.contentSourceType.displayName
            log.debug("Type: ", s.type)
        return sources
        
    def update_content_source(self,                                
                              subject,
                              id, 
                              name, 
                              displayName, 
                              description, 
                              lazyLoad,
                              url):
                
        source = self.service.getContentSource(subject, id)
        log.debug("we got a content source: ", source.id)
        source.name = name
        source.displayName = displayName
        source.description = description
        source.lazyLoad = lazyLoad
        source.configuration.properties.entry[0].value.stringValue = url      
        self.service.updateContentSource(subject, source)
        return id

    def create_content_source(self, subject, name, displayName, description, lazyLoad, url):

        configuration = self.service.get_instance('configuration')
        entry = self.service.get_instance('configuration.properties.entry')
        simple = self.service.get_instance('propertySimple')
        entry.key = 'url'
        simple.name = 'url'
        simple.stringValue = url
        entry.value = simple
        configuration.properties.entry.append(entry)
        configuration.notes = name, ' configuration entry'
        
        #lazy = str(lazyLoad == 'on').lower()
        lazy = lazyLoad.lower()
        
        source = self.service.createContentSource(subject, 
                                                   name,
                                                   displayName,
                                                   description,
                                                   "YumSource",
                                                   configuration,
                                                   lazy)
        log.debug("we got a content source: ", source.id)
        
        return source.id
                
    def sync_content_source(self, subject, id):
        log.debug("synching id[%s]" % id)
        self.service.synchronizeAndLoadContentSource(subject, id) 


    def get_package_count(self, subject, id):
        pcount = self.service.getPackageVersionCountFromContentSource(subject, id)
        if pcount is None:
            pcount = 0
        return pcount                      
