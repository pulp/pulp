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
Taken from stackoverflow.com : http://tinyurl.com/2f6gx7s
"""

from hashlib import sha256
from hmac import HMAC
import random


NUM_ITERATIONS = 5000


def random_bytes(num_bytes):
    return "".join(chr(random.randrange(256)) for i in xrange(num_bytes))

def pbkdf_sha256(password, salt, iterations):
    result = password
    for i in xrange(iterations):
        result = HMAC(result, salt, sha256).digest() # use HMAC to apply the salt
    return result


def hash_password(plain_password):
    salt = random_bytes(8) # 64 bits
    hashed_password = pbkdf_sha256(plain_password, salt, NUM_ITERATIONS)
    # return the salt and hashed password, encoded in base64 and split with ","
    return salt.encode("base64").strip() + "," + hashed_password.encode("base64").strip()

def check_password(saved_password_entry, plain_password):
    salt, hashed_password = saved_password_entry.split(",")
    salt = salt.decode("base64")
    hashed_password = hashed_password.decode("base64")
    pbkdbf = pbkdf_sha256(plain_password, salt, NUM_ITERATIONS)
    return hashed_password == pbkdbf

