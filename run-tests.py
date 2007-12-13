#!/usr/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'nose','console_scripts','nosetests'
__requires__ = 'nose'
import sys
from turbogears import update_config
from pkg_resources import load_entry_point

if sys.path == "win32":
    sys.path.append("..\common\suds")
else:
    sys.path.append("../common/suds/")

update_config(configfile="test.cfg",modulename="pulp.config")

sys.exit(
   load_entry_point('nose', 'console_scripts', 'nosetests')()
)
