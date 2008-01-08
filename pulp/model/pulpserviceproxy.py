from turbogears import config
from turbogears.util import load_class 

class PulpServiceProxy(object):

    def getServiceProxy(self, endpoint):
        c = config.get('pulp.config.serviceproxy', 'suds.serviceproxy.ServiceProxy')
        ServiceProxy = load_class(c)
        servicehost = config.get('pulp.config.servicehost', 'localhost')
        service = ServiceProxy(
            "http://%s:7080/on-on-enterprise-server-ejb./%s?wsdl" % (servicehost,
            endpoint))
        return service
