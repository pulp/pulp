import os

from StringIO import StringIO
from unittest import TestCase

from mock import Mock, patch, call

from pulp.server.lazy.alias import AliasTable


class TestAliasTable(TestCase):

    FILE = """
    # Test
    Alias %s %s
    <Directory>
    </Directory>
    Alias %s %s
    <Directory>
    </Directory>
    # Ignore this Alias.
    Alias <malformed>
    """.replace('\n    ', '\n')

    @patch('os.listdir')
    @patch('__builtin__.open')
    def test_load(self, _open, listdir):
        files = [
            'a.conf',
            'b.conf',
            'c.other'
        ]

        fp0 = Mock()
        fp0.buffer = StringIO(self.FILE % tuple(range(0, 4)))
        fp0.readline.side_effect = fp0.buffer.readline
        fp0.__enter__ = Mock(return_value=fp0)
        fp0.__exit__ = Mock()

        fp1 = Mock()
        fp1.buffer = StringIO(self.FILE % tuple(range(4, 8)))
        fp1.readline.side_effect = fp1.buffer.readline
        fp1.__enter__ = Mock(return_value=fp1)
        fp1.__exit__ = Mock()

        _open.side_effect = [
            fp0,
            fp1
        ]

        listdir.return_value = files

        # test
        table = AliasTable()
        table.load()

        # validation
        for fp in (fp0, fp1):
            fp.__enter__.assert_called_once_with()
            fp.__exit__.assert_called_once_with(None, None, None)
        self.assertEqual(
            _open.call_args_list,
            [call('/etc/httpd/conf.d/{n}'.format(n=n)) for n in files[:-1]])
        self.assertEqual(table.table, {'0': '1', '2': '3', '4': '5', '6': '7'})

    def test_init(self):
        table = AliasTable()
        self.assertEqual(table.table, {})

    @patch('os.path.realpath')
    def test_translate(self, realpath):
        realpath.side_effect = lambda p: os.path.normpath(p.upper())
        table = AliasTable()
        table.table['A'] = '/tmp/test/path//a'
        table.table['B'] = '/tmp/test/path/b/'
        table.table['C'] = '/tmp/test///path/c'
        self.assertEqual(table.translate('A'), os.path.normpath(table.table['A']).upper())
        self.assertEqual(table.translate('B'), os.path.normpath(table.table['B']).upper())
        self.assertEqual(table.translate('C'), os.path.normpath(table.table['C']).upper())

    @patch('os.path.realpath')
    def test_translate_not_found(self, realpath):
        realpath.side_effect = lambda p: os.path.normpath(p.upper())
        table = AliasTable()
        path = '/my/unknown/path'
        self.assertEqual(table.translate(path), os.path.normpath(path).upper())