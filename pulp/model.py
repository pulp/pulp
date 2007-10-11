from turbogears.database import PackageHub
from sqlobject import *

hub = PackageHub('pulp')
__connection__ = hub

# class YourDataClass(SQLObject):
#     pass

