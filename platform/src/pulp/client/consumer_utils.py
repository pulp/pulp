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

from M2Crypto import X509
import os

from pulp.common.bundle import Bundle

# -- public -------------------------------------------------------------------

def load_consumer_id(context):
    """
    Returns the consumer's ID if it is registered.

    @return: consumer id if registered; None when not registered
    @rtype:  str, None
    """
    filesystem_section = context.config.get('filesystem', None)
    if filesystem_section is None:
        return None

    consumer_cert_path = filesystem_section.get('id_cert_dir', None)
    consumer_cert_filename = filesystem_section.get('id_cert_filename', None)

    if None in (consumer_cert_path, consumer_cert_filename):
        return None

    full_filename = os.path.join(consumer_cert_path, consumer_cert_filename)
    bundle = Bundle(full_filename)

    if not bundle.valid():
        return None

    content = bundle.read()
    x509 = X509.load_cert_string(content)
    subject = _subject(x509)
    return subject['CN']

# -- private ------------------------------------------------------------------

def _subject(x509):
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
