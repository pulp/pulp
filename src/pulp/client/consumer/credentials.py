# -*- coding: utf-8 -*-

# Copyright © 2010 Red Hat, Inc.
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
Module containing classes to manage client credentials.
"""

import os
from pulp.common.bundle import Bundle
from pulp.client.consumer.config import ConsumerConfig
from M2Crypto import X509
from logging import getLogger

log = getLogger(__name__)

class Consumer(Bundle):
    """
    The bundle for the consumer.
    @cvar ROOT: The default dir (path).
    @type ROOT: str
    @cvar CRT: The certificate file name.
    @type CRT: str
    """

    ROOT = '/etc/pki/pulp/consumer'
    CRT = 'cert.pem'

    @classmethod
    def path(cls):
        """
        Returns the consumer bundle path.
        First looks in configuration [client].consumer_cert
        @return: File path.
        @rtype: str
        """
        cfg = ConsumerConfig()
        path = cfg.client.consumer_cert
        if not isinstance(path, basestring):
            path = os.path.join(cls.ROOT, cls.CRT)
        return path

    def __init__(self):
        Bundle.__init__(self, self.path())

    def getid(self):
        """
        Get the consumer ID.
        @return: The consumer ID.
        @rtype: str
        """
        if self.valid():
            content = self.read()
            x509 = X509.load_cert_string(content)
            subject = self.subject(x509)
            return subject['CN']

    def subject(self, x509):
        """
        Get the certificate subject.
        note: Missing NID mapping for UID added to patch openssl.
        @return: A dictionary of subject fields.
        @rtype: dict
        """
        d = {}
        subject = x509.get_subject()
        subject.nid['UID'] = 458
        for key, nid in subject.nid.items():
            entry = subject.get_entries_by_nid(nid)
            if len(entry):
                asn1 = entry[0].get_data()
                d[key] = str(asn1)
                continue
        return d
