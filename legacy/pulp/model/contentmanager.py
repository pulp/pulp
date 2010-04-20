from pulp.model.pulpserviceproxy import PulpServiceProxy 
from pulp.model.mockmodel import MockContentSource
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
                              description, 
                              lazyLoad,
                              url):
                
        source = self.service.getContentSource(subject, id)
        log.debug("we got a content source: ", source.id)
        source.name = name
        source.description = description
        source.lazyLoad = lazyLoad
        source.configuration.properties.entry[0].value.stringValue = url      
        self.service.updateContentSource(subject, source)
        return id

    def create_content_source(self, subject, name, description, lazyLoad, url):

        configuration = self.service.get_instance('configuration')
        entry = self.service.get_instance('configuration.properties.entry')
        simple = self.service.get_instance('propertySimple')
        entry.key = 'location'
        simple.name = 'location'
        simple.stringValue = url
        entry.value = simple
        configuration.properties.entry.append(entry)
        configuration.notes = name, ' configuration entry'
        
        lazy = lazyLoad.lower()
        
        source = self.service.createContentSource(subject, 
                                                   name,
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



class DummyContentSourceContentManager(ContentManager):
    """
    Dummy class used currently to return some valid countent sources.
    Used in testing the repo sync command.

    TODO: Destroy this once the model and methods for testing against it are
    a little more clear.
    """

    def __init__(self):
        """ Overload to not do any networking. """
        pass

    def list_all_content_sources(self, subject):
        """
        Overload method in ContentManager to return real Yum repositories.
        """
        repos = []

        # TODO: Remove hard coded repository data here. Using packagekit
        # repository for testing until we have repository storage
        # straightened out.
        repos.append(MockContentSource(id=1, name="utopia", 
            url="http://people.freedesktop.org/~hughsient/fedora/8/i386/"))

        return repos



