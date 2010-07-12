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
"""
This had to be done...
"""

import functools


def is_awesome():
    return True


def is_bogus():
    return False


class BogusError(Exception):
    pass


def awesome(function):
    @functools.wraps(function)
    def make_more_awesome(*args, **kwargs):
        if is_awesome():
            return function(*args, **kwargs)
        raise BogusError('Your code is bogus')
    return make_more_awesome