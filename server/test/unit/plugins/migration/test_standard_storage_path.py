import os

from unittest import TestCase
from itertools import izip, chain

from mock import patch, Mock, call

from pulp.plugins.migration.standard_storage_path import Batch, Plan, Migration, Unit, Item


MODULE = 'pulp.plugins.migration.standard_storage_path'


class TestBatch(TestCase):

    def test_add(self):
        unit = Mock(plan=1, id=2, storage_path=3, new_path=4)

        # test
        batch = Batch()
        batch.add(unit)

        # validation
        item = batch.items.values()[0]
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch.items.keys()[0], unit.storage_path)
        self.assertEqual(item.plan, unit.plan)
        self.assertEqual(item.unit_id, unit.id)
        self.assertEqual(item.storage_path, unit.storage_path)

    def test_reset(self):
        # test
        batch = Batch()
        batch.items = {'A': 1}
        batch.reset()

        # validation
        self.assertEqual(batch.items, {})

    @patch('os.walk')
    @patch('os.readlink')
    @patch('os.unlink')
    @patch('os.symlink')
    @patch('os.path.islink')
    def test_relink(self, islink, symlink, unlink, readlink, walk):
        def read_link(path):
            return path.upper()

        readlink.side_effect = read_link

        def is_link(path):
            return os.path.basename(path)[0] == 'l'

        islink.side_effect = is_link

        items = {
            'D0/L2': Item(1, '1', 'd0/l2', 'new-path-1'),
            'D1/L3': Item(2, '2', 'd1/l3', 'new-path-2'),
            'D2/L6': Item(3, '3', 'd2/l6', 'new-path-3'),
        }

        walk.return_value = [
            ('d0', ['d1', 'd2'], ['f1', 'l2']),
            ('d1', [], ['l3', 'f4']),
            ('d2', [], ['f5', 'l6', 'l7'])
        ]

        # test
        batch = Batch()
        batch.items = items
        batch._relink()

        # validation
        self.assertEqual(
            unlink.call_args_list,
            [
                call(items[k].storage_path) for k in sorted(items)
            ])
        self.assertEqual(
            symlink.call_args_list,
            [
                call(items[k].new_path, k.lower()) for k in sorted(items)
            ])

    @patch(MODULE + '.Unit.migrate')
    def test_migrate(self, unit_migrate):
        items = [
            Item(Mock(), '1', 'path-1', 'new-path-1'),
            Item(Mock(), '2', 'path-2', 'new-path-2'),
            Item(Mock(), '3', 'path-3', 'new-path-3'),
        ]
        _dict = Mock()
        _dict.itervalues.return_value = iter(items)

        # test
        batch = Batch()
        batch.items = _dict
        batch._migrate()

        # validate
        self.assertEqual(
            unit_migrate.call_args_list,
            [
                call(i.plan, i.unit_id, i.storage_path, i.new_path) for i in items
            ])

    @patch(MODULE + '.Batch.reset')
    @patch(MODULE + '.Batch._relink')
    @patch(MODULE + '.Batch._migrate')
    def test_call(self, relink, migrate, reset):
        # test
        batch = Batch()
        batch.items['A'] = 12
        batch()

        # validate
        relink.assert_called_once_with()
        migrate.assert_called_once_with()
        reset.assert_called_once_with()

    def test_len(self):
        # test
        batch = Batch()
        batch.items['A'] = 12
        batch.items['B'] = 18

        # validation
        self.assertEqual(len(batch), len(batch.items))


class TestPlan(TestCase):

    def test_init(self):
        collection = Mock()
        key_fields = ('name', 'version')
        join_leaf = Mock()

        # test
        plan = Plan(collection, key_fields, join_leaf)

        # validation
        self.assertEqual(plan.collection, collection)
        self.assertEqual(plan.key_fields, key_fields)
        self.assertEqual(plan.join_leaf, join_leaf)
        self.assertEqual(plan.fields, set())

    @patch(MODULE + '.Migration.content_dir')
    def test_new_path(self, content_dir):
        digest = '0123456789'
        content_dir.return_value = '/tmp/path_1'
        unit = Mock(type_id='iso', storage_path='/tmp/path_1/foo.iso')
        unit.key_digest.return_value = digest

        # test
        plan = Plan(Mock(), tuple())
        path = plan._new_path(unit)

        # validation
        expected_path = os.path.join(
            os.path.join(content_dir.return_value, 'units'),
            unit.type_id,
            digest[0:2],
            digest[2:],
            os.path.basename(unit.storage_path))
        self.assertEqual(path, expected_path)

    @patch(MODULE + '.Migration.content_dir')
    def test_new_path_directory(self, content_dir):
        digest = '0123456789'
        content_dir.return_value = '/tmp/path_1'
        unit = Mock(type_id='iso', storage_path='/tmp/path_1/foo.iso')
        unit.key_digest.return_value = digest

        # test
        plan = Plan(Mock(), tuple(), False)
        path = plan._new_path(unit)

        # validation
        expected_path = os.path.join(
            os.path.join(content_dir.return_value, 'units'),
            unit.type_id,
            digest[0:2],
            digest[2:])
        self.assertEqual(path, expected_path)

    @patch(MODULE + '.Unit')
    @patch(MODULE + '.Plan._new_path')
    def test_iter(self, new_path, unit):
        collection = Mock()
        key_fields = ('name', 'version')
        documents = [
            Mock(_id='1'),
            Mock(_id='2'),
            Mock(_id='3'),
            Mock(_id='4')
        ]
        collection.find.return_value = documents
        units = [
            Mock(id='1', needs_migration=Mock(return_value=True)),
            Mock(id='2', needs_migration=Mock(return_value=False)),
            Mock(id='3', needs_migration=Mock(return_value=True)),
            Mock(id='4', needs_migration=Mock(return_value=False)),
        ]
        unit.side_effect = units
        new_paths = [
            'p1',
            'p2',
            'p3',
            'p4'
        ]
        new_path.side_effect = new_paths

        # test
        plan = Plan(collection, key_fields)
        plan.fields.add('release')
        _list = list(plan)

        # validation
        collection.find.assert_called_once_with(
            projection={
                '_storage_path': True,
                '_content_type_id': True,
                'version': True,
                'release': True,
                'name': True,
            })
        self.assertEqual(
            unit.call_args_list,
            [
                call(plan, d) for d in documents
            ])
        for unit, new_path in izip(units, new_paths):
            self.assertEqual(unit.new_path, new_path)
        self.assertEqual(_list, [u for u in units if u.needs_migration()])


class TestMigration(TestCase):

    def test_init(self):
        # test
        migration = Migration()

        # validation
        self.assertEqual(migration.plans, [])

    @patch(MODULE + '.config')
    def test_storage_dir(self, config):
        # test
        path = Migration.storage_dir()

        # validation
        config.get.assert_called_once_with('server', 'storage_dir')
        self.assertEqual(path, config.get.return_value)

    @patch(MODULE + '.Migration.storage_dir')
    def test_content_dir(self, storage_dir):
        storage_dir.return_value = '/tmp/p1'

        # test
        path = Migration.content_dir()

        # validation
        self.assertEqual(path, os.path.join(storage_dir.return_value, 'content'))

    @patch(MODULE + '.Migration.storage_dir')
    def test_publish_dir(self, storage_dir):
        storage_dir.return_value = '/tmp/p1'

        # test
        path = Migration.publish_dir()

        # validation
        self.assertEqual(path, os.path.join(storage_dir.return_value, 'published'))

    @patch('os.rmdir')
    @patch('os.walk')
    @patch('os.listdir')
    @patch(MODULE + '.Migration.content_dir')
    def test_prune(self, content_dir, listdir, walk, rmdir):
        def list_dir(path):
            if path.endswith('_'):
                return []
            else:
                return [1, 2]
        listdir.side_effect = list_dir
        walk.return_value = [
            ('r', ['d1', 'd2'], ['f1', 'f2']),
            ('d1_', [], []),
            ('d2', ['d3'], []),
            ('d4_', [], [])
        ]

        # test
        Migration._prune()

        # validation
        walk.assert_called_once_with(content_dir.return_value, topdown=False)
        self.assertEqual(
            rmdir.call_args_list,
            [
                call('d1_'),
                call('d4_')
            ])

    def test_add(self):
        plan = Mock()

        # test
        migration = Migration()
        migration.add(plan)

        # validation
        self.assertEqual(migration.plans, [plan])

    @patch(MODULE + '.Batch')
    def test_call(self, batch):
        plans = [
            range(0, 3),
            range(4, 7),
            range(8, 12)
        ]
        batch.LIMIT = 5
        batch.return_value.__len__.side_effect = chain(range(1, 6), range(1, 6))

        # test
        migration = Migration()
        migration.plans = plans
        migration()

        # validation
        self.assertEqual(
            batch.return_value.call_args_list,
            [
                call(),  # hit limit
                call(),  # hit limit
                call(),  # partial at end
            ])


class TestUnit(TestCase):

    def test_init(self):
        plan = Mock()
        document = Mock()

        # test
        unit = Unit(plan, document)

        # validation
        self.assertEqual(unit.plan, plan)
        self.assertEqual(unit.document, document)

    def test_properties(self):
        unit_key = {
            'name': 'Elmer Fudd',
            'version': '2.0'
        }
        plan = Mock(key_fields=unit_key.keys())
        document = {
            '_id': '12434',
            '_content_type_id': 'iso',
            '_storage_path': '/tmp/path_1'
        }
        document.update(unit_key)

        # test
        unit = Unit(plan, document)

        # validation
        self.assertEqual(unit.id, document['_id'])
        self.assertEqual(unit.type_id, document['_content_type_id'])
        self.assertEqual(unit.storage_path, document['_storage_path'])
        self.assertEqual(unit.key, unit_key)

    def test_key_digest(self):
        unit_key = {
            'name': 'Elmer Fudd',
            'version': '2.0',
            'age': 147,
        }
        document = {
            '_id': '12434',
            '_content_type_id': 'iso',
            '_storage_path': '/tmp/path_1'
        }
        document.update(unit_key)
        plan = Mock(key_fields=sorted(unit_key.keys(), reverse=True))

        # test
        unit = Unit(plan, document)
        digest = unit.key_digest()

        # validation
        # the digest is the sha256.hexdigest() of the sorted unit.key.items()
        self.assertEqual(
            digest,
            'c10d6ad917b10992b41df1b88acde7cd50903b62953e5084f601150a73d998d4')

    def test_needs_migration(self):
        document = {
            '_storage_path': 'path_1'
        }

        # test
        unit = Unit(Mock(), document)
        unit.new_path = 'path_2'
        needed = unit.needs_migration()

        # validation
        self.assertTrue(needed)

    def test_needs_migration_not(self):
        document = {
            '_storage_path': 'path_1'
        }

        # test
        unit = Unit(Mock(), document)
        unit.new_path = 'path_1'
        needed = unit.needs_migration()

        # validation
        self.assertFalse(needed)

    @patch(MODULE + '.shutil')
    @patch(MODULE + '.mkdir')
    @patch('os.path.exists')
    def test_migrate(self, path_exists, mkdir, shutil):
        unit_id = '123'
        plan = Mock()
        path = '/tmp/old/path_1'
        new_path = '/tmp/new/content/path_2'
        path_exists.return_value = True

        # test
        Unit.migrate(plan, unit_id, path, new_path)

        # validation
        path_exists.assert_called_once_with(path)
        mkdir.assert_called_once_with(os.path.dirname(new_path))
        shutil.move.assert_called_once_with(path, new_path)
        plan.collection.update_one.assert_called_once_with(
            filter={'_id': unit_id},
            update={'$set': {'_storage_path': new_path}})
