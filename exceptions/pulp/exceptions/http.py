import http.client

from pulp.common import error_codes

from .base import PulpExecutionException


class MissingResource(PulpExecutionException):
    """"
    Base class for exceptions raised due to requesting a resource that does not
    exist.
    """
    http_status_code = http.client.NOT_FOUND

    def __init__(self, *args, **resources):
        """
        @param args: backward compatibility for for positional resource_id argument
        @param resources: keyword arguments of resource_type=resource_id
        """
        # backward compatibility for for previous 'resource_id' positional argument
        if args:
            resources['resource_id'] = args[0]

        super(MissingResource, self).__init__(resources)
        self.error_code = error_codes.PLP0009
        self.resources = resources
        self.error_data = {'resources': resources}

    def __str__(self):
        resources_str = ', '.join('%s=%s' % (k, v) for k, v in self.resources.items())
        msg = self.error_code.message % {'resources': resources_str}
        return msg.encode('utf-8')

    def data_dict(self):
        return {'resources': self.resources}