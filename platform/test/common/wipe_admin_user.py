## Simple file you can run with ipython if you want to poke around the API ##
import sys
sys.path.append("../../src")
from pulp.server.api.user import UserApi

uapi = UserApi()
admin = uapi.user('admin')
print "Deleting Admin: %s" % admin
uapi.collection.remove(admin)
print "Admin deleted.  Restart apache and you will get a new one created."

