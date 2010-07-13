#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import logging
import web

log = logging.getLogger('pulp')


class RoleCheck(object):
    '''decorator class to check Roles of caller.  Copied and modified from:
       
       http://wiki.python.org/moin/PythonDecoratorLibrary#DifferentDecoratorForms
    '''
    
    def __init__(self, *dec_args, **dec_kw):
        '''The decorator arguments are passed here.  Save them for runtime.'''
        self.dec_args = dec_args
        self.dec_kw = dec_kw
        
    def __call__(self, f):
        def check_roles(*fargs, **kw):
            '''
              Strip off the decorator arguments so we can use those to check the
              Roles of the current caller.

              Note: the first argument cannot be "self" because we get a parse error
              "takes at least 1 argument" unless the instance is actually included in
              the argument list, which is redundant.  If this wraps a class instance,
              the "self" will be the first argument.
            '''
            # Check the roles
            log.error("Role checking start")
            for key in self.dec_kw.keys():
                log.debug("Role Name [%s], check? [%s]" % (key, self.dec_kw[key]))
            
            for arg in fargs:
                log.debug("Arg [%s]" % arg)

            environment = web.ctx
            log.error("check_roles env: %s" % str(environment))
            
            # Does this wrap a class instance?
            if fargs and getattr(fargs[0], '__class__', None):
                instance, fargs = fargs[0], fargs[1:]
                # call the method with just the fargs and kw for the original method
                ret=f(instance, *fargs, **kw)
            else:
                # just send in the give args and kw
                ret=f(*(fargs), **kw)
            return ret

        # Save wrapped function reference
        self.f = f
        check_roles.__name__ = f.__name__
        check_roles.__dict__.update(f.__dict__)
        check_roles.__doc__ = f.__doc__
        return check_roles
    