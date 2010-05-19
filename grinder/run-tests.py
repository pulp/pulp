#!/usr/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'nose','console_scripts','nosetests'
__requires__ = 'nose'
import sys
from pkg_resources import load_entry_point

sys.path.append("src/")

sys.exit(
   load_entry_point('nose', 'console_scripts', 'nosetests')()
)
