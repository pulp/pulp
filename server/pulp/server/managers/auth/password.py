"""
Password Manager

Functions taken from stackoverflow.com : http://tinyurl.com/2f6gx7s
"""

from hmac import HMAC
import random

from pulp.server.compat import digestmod


NUM_ITERATIONS = 5000


class PasswordManager(object):
    """
    Performs password related functions.
    """
    def random_bytes(self, num_bytes):
        return "".join(chr(random.randrange(256)) for i in xrange(num_bytes))

    def pbkdf_sha256(self, password, salt, iterations):
        result = password
        for i in xrange(iterations):
            result = HMAC(result, salt, digestmod).digest()  # use HMAC to apply the salt
        return result

    def hash_password(self, plain_password):
        salt = self.random_bytes(8)  # 64 bits
        hashed_password = self.pbkdf_sha256(str(plain_password), salt, NUM_ITERATIONS)
        # return the salt and hashed password, encoded in base64 and split with ","
        return salt.encode("base64").strip() + "," + hashed_password.encode("base64").strip()

    def check_password(self, saved_password_entry, plain_password):
        salt, hashed_password = saved_password_entry.split(",")
        salt = salt.decode("base64")
        hashed_password = hashed_password.decode("base64")
        pbkdbf = self.pbkdf_sha256(plain_password, salt, NUM_ITERATIONS)
        return hashed_password == pbkdbf
