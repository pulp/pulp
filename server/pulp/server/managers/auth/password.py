# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Password Manager

Functions taken from stackoverflow.com : http://tinyurl.com/2f6gx7s
"""

import random
from hmac import HMAC

from pulp.server.compat import digestmod

# -- constants ----------------------------------------------------------------

NUM_ITERATIONS = 5000

# -- classes ------------------------------------------------------------------

class PasswordManager(object):
    """
    Performs password related functions.
    """
    
    def random_bytes(self, num_bytes):
        return "".join(chr(random.randrange(256)) for i in xrange(num_bytes))

    def pbkdf_sha256(self, password, salt, iterations):
        result = password
        for i in xrange(iterations):
            result = HMAC(result, salt, digestmod).digest() # use HMAC to apply the salt
        return result

    def hash_password(self, plain_password):
        salt = self.random_bytes(8) # 64 bits
        hashed_password = self.pbkdf_sha256(str(plain_password), salt, NUM_ITERATIONS)
        # return the salt and hashed password, encoded in base64 and split with ","
        return salt.encode("base64").strip() + "," + hashed_password.encode("base64").strip()

    def check_password(self, saved_password_entry, plain_password):
        salt, hashed_password = saved_password_entry.split(",")
        salt = salt.decode("base64")
        hashed_password = hashed_password.decode("base64")
        pbkdbf = self.pbkdf_sha256(plain_password, salt, NUM_ITERATIONS)
        return hashed_password == pbkdbf
    


