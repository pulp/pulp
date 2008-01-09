from turbogears import config
from turbogears.util import load_class 

class PulpServiceProxy(object):

    def getServiceProxy(self, endpoint):
        c = config.get('pulp.config.serviceproxy', 'suds.serviceproxy.ServiceProxy')
        ServiceProxy = load_class(c)
        servicehost = config.get('pulp.config.servicehost', 'localhost')
        serviceport = config.get('pulp.config.serviceport', '7080')
        service = ServiceProxy(
            "http://%s:%s/on-on-enterprise-server-ejb3/%s?wsdl" % (servicehost, 
                                                                serviceport,
                                                                endpoint))
        return service
