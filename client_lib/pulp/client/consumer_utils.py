import os

from M2Crypto import X509

from pulp.common.bundle import Bundle


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
