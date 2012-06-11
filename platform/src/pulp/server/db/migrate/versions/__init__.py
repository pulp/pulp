# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import re


_mod_regex = re.compile(r'(?!__init__).*\.py$')


def _import_module(name):
    mod = __import__(name)
    for sub in name.split('.')[1:]:
        mod = getattr(mod, sub, None)
        if mod is None:
            raise RuntimeError('cannot import module %s: module not found' %
                               name)
    return mod


def _get_migration_module_names():
    package = __name__
    mod_dir = os.path.dirname(__file__)
    # create a list of module names by joining the package name with the
    # name of python modules in this directory, except this one, sans the
    # .py[co] suffixes
    names = ['.'.join((package, n.rsplit('.', 1)[0]))
             for n in os.listdir(mod_dir)
             if _mod_regex.match(n)]
    return names


def get_migration_modules():
    # 1. auto-discover the migration modules in this package
    # 2. import the modules
    # 3. ensure that they have the necessary attributes to perform a migration
    # 4. order the modules by the version they migrate to
    modules = []
    for name in _get_migration_module_names():
        mod = _import_module(name)
        for attr in ('migrate', 'version'):
            if not hasattr(mod, attr):
                raise RuntimeError('module %s is missing %s attribute' %
                                   (name, attr))
            modules.append(mod)
    return sorted(modules, cmp=lambda x,y: cmp(x.version, y.version))
