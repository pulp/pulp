from pulp.bindings.base import PulpAPI


class StaticRequest(PulpAPI):
    """
    Connection class to access static calls
    """

    def get_server_key(self):
        """
        Retrieve the server's public key.

        :return: rsa public key
        :rtype:  str
        """
        return self.server.GET('/pulp/static/rsa_pub.key', ignore_prefix=True)
