import cherrypy
import logging
import os, os.path
from elementtree.ElementTree import parse

log = logging.getLogger("pulp.perspectives")

class PerspectiveManager(object):
    
    # Returns the currently used perspetive by the user
    # or will return 'root' as the root perspective if none is
    # in use.
    def get_current_perspective(self):
        if "perspective" in cherrypy.session:
            session_pers = cherrypy.session['perspective']
            log.debug("pers in session: %s", session_pers) 
            return session_pers
        else:
            return self.get_perspective("root")
    
    def set_current_perspective(self, perspective):
        cherrypy.session['perspective'] = perspective
            
    # list of all Perspective objects available
    # TODO:  Cache this, currently its re-parsing every page turn!
    def get_all_perspectives(self):
        retval = dict()
        retval = self._parse_perspectives()
        return retval
            
    def get_perspective(self, name):
        all = self.get_all_perspectives()
        return all[name]
    
    def _parse_perspectives(self):
        retval = dict()
        path = "pulp/perspectives/definitions"
        for name in os.listdir(path):
            fullpath = path + "/" + name
            log.debug("_parse_perspectives : Working with ", fullpath)
            if os.path.isfile(fullpath):
                log.debug("Found file: ", fullpath)
                root = parse(fullpath).getroot()
                perspective = root.find("perspective")
                url = root.attrib['url']
                name = root.attrib['name']
                desc = root.attrib['description']
                log.debug("_parse_perspectives : Name: ", name)
                perspective = Perspective(name, url, desc)
                # Parse the Tasks and add them to the Perspective
                tasknode = root.find("tasks")
                if (tasknode is not None):
                    tasks = tasknode.findall("task")
                    for t in tasks:
                        task = Task(t.attrib['name'], t.attrib['url'], t.attrib['display'])
                        urlmatches = t.findall('url-match')
                        for u in urlmatches:
                            task.add_url_path(u.text)  
                        perspective.add_task(task)
                retval[name] = perspective
        return retval                    
        

class Perspective(object):
    # Perspective class stores the name and the initial URL
    # to take the user to when switching to that Perspective
    def __init__(self, name, url, description):
        self.name = name
        self.url = url
        self.description = description
        self.tasks = []
    
    def add_task(self, task):
        # Add a Task object to this Perspective
        self.tasks.append(task)
        
class Task(object):
    # Represents a UI Task that the user can perform.   
    def __init__(self, name, url, display):
        self.name = name
        self.url = url
        self.display = display
        self.urlmatches = []

    def add_url_path(self, url):        
        self.urlmatches.append(url)
        
    def is_visible(self):
        path = cherrypy.request.path
        for u in self.urlmatches:
            log.debug("is_visible : url-match: " + u)
            log.debug("is_visible : path: " + path)
            if u.endswith("/*"):
                u = u.rstrip("/*")
                log.debug("is_visible : stripping /*")
            elif u.endswith("/"):
                u = u.rstrip("/")
                log.debug("is_visible : stripping /")
            log.debug("is_visible : u after massage: " + u)
            if path.startswith(u):
                log.debug("is_visible : startswith matches, returning True")
                return True 
        log.debug("is_visible : no matches, returning false")
        return False

    