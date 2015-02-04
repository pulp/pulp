from pulp.server.db.model.auth import User
from pulp.server.util import Singleton


SYSTEM_ID = '00000000-0000-0000-0000-000000000000'
SYSTEM_LOGIN = u'SYSTEM'


class SystemUser(User):
    """
    Singleton user class that represents the "system" user (i.e. no user).
    """

    __metaclass__ = Singleton

    def __init__(self):
        super(SystemUser, self).__init__(SYSTEM_LOGIN, None)
        self._id = self.id = SYSTEM_ID
