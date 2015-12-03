#!/usr/bin/env python2
#
# Diagnostic tool used to inspect the content catalog.
#

from time import time
from optparse import OptionParser

from pulp.server.db import connection


class RPM(object):

    TEMPLATE = '[RPM] %(name)-40s %(version)-10s %(release)-15s %(arch)-8s %(checksum)s'

    def __call__(self, entry):
        return RPM.TEMPLATE % entry['unit_key']


FORMATTER = {
    'rpm': RPM(),
}


class Catalog(object):

    def __init__(self):
        connection.initialize()
        self.collection = connection.get_collection('content_catalog')

    @staticmethod
    def render(entry):
        type_id = entry['type_id']
        formatter = FORMATTER.get(type_id)
        if formatter:
            return formatter(entry)
        else:
            return 'Formatter not found for: %s' % type_id

    def get_all(self):
        return self.collection.find({'expiration': {'$gt': time()}})

    def get_selected(self, source_id):
        return self.collection.find(
            {
                'source_id': source_id,
                'expiration': {'$gt': time()}
            })

    def dump(self, source_id=None):
        if source_id:
            print '\nSOURCE: %s\n' % source_id
            cursor = self.get_selected(source_id)
        else:
            print '\nSOURCE: ALL\n'
            cursor = self.get_all()
        self._print(cursor)

    def _print(self, cursor):
        output = []
        for entry in cursor.sort('source_id'):
            source_id = entry['source_id']
            output.append((source_id, self.render(entry)))
        for source_id, description in sorted(output):
            print '(%s) %s' % (source_id, description)


if __name__ == '__main__':
    catalog = Catalog()
    parser = OptionParser(description='Dump Content Catalog')
    parser.add_option('-s', '--source-id', help='A content source ID')
    options, arguments = parser.parse_args()
    catalog.dump(options.source_id)
