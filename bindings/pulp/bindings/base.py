class PulpAPI(object):
    """
    Base api class that allows an internal server object to be set at instantiation
    @ivar server: L{PulpConnection} instance
    """
    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """
        self.server = pulp_connection
