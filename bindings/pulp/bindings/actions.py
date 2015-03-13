from pulp.bindings.base import PulpAPI


class ActionsAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def __init__(self, pulp_connection):
        super(ActionsAPI, self).__init__(pulp_connection)

    def login(self, username, password):
        path = '/v2/actions/login/'

        # Will overwrite the username/password already set on the connection.
        # This should make sense; if you're authenticating with credentials
        # you probably want to continue using them.
        self.server.username = username
        self.server.password = password

        return self.server.POST(path)
