from turbogears import config
from turbogears.util import load_class 

class PulpServiceProxy(object):

    def getServiceProxy(self, endpoint):
        c = config.get('pulp.config.serviceproxy', 'suds.serviceproxy.ServiceProxy')
        ServiceProxy = load_class(c)
        service = ServiceProxy(
            "http://localhost:7080/on-on-enterprise-server-ejb./%s?wsdl" % endpoint)
        return service
