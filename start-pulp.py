#!/usr/bin/python
import pkg_resources
pkg_resources.require("TurboGears")

from turbogears import update_config, start_server
import cherrypy
cherrypy.lowercase_api = True
from os.path import *
import sys

if sys.platform == "win32":
    sys.path.append("..\common\suds")
else:
    sys.path.append("../common/suds/")

# Check suds dep
try:
    from suds.property import Property
except Exception:
    print("error importing suds module.  you need this module to run pulp.")
    exit(2)
    


# first look on the command line for a desired config file,
# if it's not on the command line, then
# look for setup.py in this directory. If it's not there, this script is
# probably installed
if len(sys.argv) > 1:
    update_config(configfile=sys.argv[1], 
        modulename="pulp.config")
elif exists(join(dirname(__file__), "setup.py")):
    update_config(configfile="dev.cfg",modulename="pulp.config")
else:
    update_config(configfile="prod.cfg",modulename="pulp.config")

from pulp.controllers import Root

start_server(Root())
