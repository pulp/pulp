#!/usr/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'nose==0.9.2','console_scripts','nosetests'
__requires__ = 'nose==0.9.2'
import sys
from turbogears import update_config
from pkg_resources import load_entry_point

if sys.path == "win32":
    sys.path.append("..\common\suds")
else:
    sys.path.append("../common/suds/")

update_config(configfile="test.cfg",modulename="pulp.config")

sys.exit(
   load_entry_point('nose==0.9.2', 'console_scripts', 'nosetests')()
)
