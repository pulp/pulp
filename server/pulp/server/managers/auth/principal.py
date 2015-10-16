import threading

from pulp.server.db import model


_PRINCIPAL_STORAGE = threading.local()


class PrincipalManager(object):
    """
    Manager that tracks the current user of the model.
    """

    # reference system attributes here for convenience
    system_id = model.SYSTEM_ID
    system_login = model.SYSTEM_LOGIN

    def get_principal(self):
        """
        Get the current user of the system,
        returning the default system user if there isn't one.
        @return: current user of the system
        @rtype: User or dict
        """
        return getattr(_PRINCIPAL_STORAGE, 'principal', model.SystemUser())

    def set_principal(self, principal=None):
        """
        Set the current user of the system to the provided principal,
        if no principal is provided, set the current user to the system user.
        @param principal: current user
        @type principal: User or None
        """
        _PRINCIPAL_STORAGE.principal = principal or model.SystemUser()

    def clear_principal(self):
        """
        Clear the current user of the system.
        """
        _PRINCIPAL_STORAGE.principal = model.SystemUser()

    def is_system_principal(self):
        """
        Determine if the current user is the default system user.
        @return: true if the current user is the system user, false otherwise
        @rtype: bool
        """
        return self.get_principal() is model.SystemUser()
