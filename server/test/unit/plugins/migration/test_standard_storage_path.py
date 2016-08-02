import os

from unittest import TestCase
from itertools import izip, chain

from mock import patch, Mock, call

from pulp.plugins.migration.standard_storage_path import Batch, Plan, Migration, Unit, Item


MODULE = 'pulp.plugins.migration.standard_storage_path'


class TestBatch(TestCase):

    def test_add(self):
        unit = Mock(plan=1, id=2, storage_path='3', new_path='4', files=['4', '5'])

        # test
        batch = Batch()
        batch.add(unit)

        # validation
        item = batch.items[0]
        self.assertEqual(len(batch), 1)
        self.assertEqual(
            sorted(batch.paths.keys()),
            sorted([unit.storage_path] + [os.path.join(unit.storage_path, f) for f in unit.files]))
        self.assertEqual(batch.paths.values(), [item, item, item])
        self.assertEqual(item.plan, unit.plan)
        self.assertEqual(item.unit_id, unit.id)
        self.assertEqual(item.storage_path, unit.storage_path)

    def test_reset(self):
        # test
        batch = Batch()
        batch.items = [1]
        batch.paths = {'A': 1}
        batch.reset()

        # validation
        self.assertEqual(batch.items, [])
        self.assertEqual(batch.paths, {})

    @patch('os.walk')
    @patch('os.readlink')
    @patch('os.unlink')
    @patch('os.symlink')
    def test_relink(self, symlink, unlink, readlink, walk):
        links = {
            '/pub/zoo/cat/lion/f1': '/content/a/f1',
            '/pub/zoo/cat/tiger/f2': '/content/b/f2',
            '/pub/zoo/zebra/f3': '/content/c/f3',
            '/pub/zoo/bear/f4': '/content/d/f4',
            '/pub/zoo/wolf/f5': '/content/e/f5',
            '/pub/zoo/wolf/.f5': '/content/e/.f5',
            '/pub/zoo/wolf/f6': '/content/e/f6',
            '/pub/unknown/f0': '/content/unknown/f0',
        }

        def read_link(path):
            try:
                return links[path]
            except KeyError:
                raise OSError()

        readlink.side_effect = read_link

        items = [
            Item(1, '1', '/content/a/f1', '/content/new/a/f1', []),
            Item(2, '2', '/content/b/f2', '/content/new/b/f2', []),
            Item(3, '3', '/content/c/f3', '/content/new/c/f3', []),
            Item(4, '4', '/content/d/f4', '/content/new/d/f4', []),
            Item(5, '5', '/content/e', '/content/new/e', ['f5', '.f5', 'f6']),
        ]

        paths = {}
        for i in items:
            paths[i.storage_path] = i
            for f in i.files:
                paths[os.path.join(i.storage_path, f)] = i

        walk.return_value = [
            ('/pub', ['zoo', 'other'], []),
            ('/pub/zoo', ['cat'], []),
            ('/pub/zoo/cat', ['lion', 'tiger'], []),
            ('/pub/zoo/cat/lion', [], ['f1']),
            ('/pub/zoo/cat/tiger', [], ['f2']),
            ('/pub/zoo/zebra', [], ['f3']),
            ('/pub/zoo/bear', [], ['f4']),
            ('/pub/zoo/wolf', [], ['.f5', 'f5', 'f6']),
            ('/pub/unknown', [], ['f0', 'f1']),
        ]

        # test
        batch = Batch()
        batch.paths = paths
        batch._relink()

        # validation
        self.assertEqual(
            unlink.call_args_list,
            [
                call('/pub/zoo/cat/lion/f1'),
                call('/pub/zoo/cat/tiger/f2'),
                call('/pub/zoo/zebra/f3'),
                call('/pub/zoo/bear/f4'),
                call('/pub/zoo/wolf/.f5'),
                call('/pub/zoo/wolf/f5'),
                call('/pub/zoo/wolf/f6'),
            ])
        self.assertEqual(
            symlink.call_args_list,
            [
                call('/content/new/a/f1', '/pub/zoo/cat/lion/f1'),
                call('/content/new/b/f2', '/pub/zoo/cat/tiger/f2'),
                call('/content/new/c/f3', '/pub/zoo/zebra/f3'),
                call('/content/new/d/f4', '/pub/zoo/bear/f4'),
                call('/content/new/e/.f5', '/pub/zoo/wolf/.f5'),
                call('/content/new/e/f5', '/pub/zoo/wolf/f5'),
                call('/content/new/e/f6', '/pub/zoo/wolf/f6'),
            ])

    def test_migrate(self):
        plan = Mock()
        items = [
            Item(plan, '1', 'path-1', 'new-path-1', []),
            Item(plan, '2', 'path-2', 'new-path-2', []),
            Item(plan, '3', 'path-3', 'new-path-3', []),
        ]

        # test
        batch = Batch()
        batch.items = items
        batch._migrate()

        # validate
        self.assertEqual(
            plan.migrate.call_args_list,
            [
                call(i.unit_id, i.storage_path, i.new_path) for i in items
            ])

    @patch(MODULE + '.Batch.reset')
    @patch(MODULE + '.Batch._relink')
    @patch(MODULE + '.Batch._migrate')
    def test_call(self, relink, migrate, reset):
        # test
        batch = Batch()
        batch.items = [12]
        batch()

        # validate
        relink.assert_called_once_with()
        migrate.assert_called_once_with()
        reset.assert_called_once_with()

    def test_len(self):
        # test
        batch = Batch()
        batch.items = [1, 2]

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
    def test_new_unit(self, unit):
        document = Mock()

        # test
        plan = Plan(Mock(), tuple(), False)
        created = plan._new_unit(document)

        # validation
        unit.assert_called_once_with(plan, document)
        self.assertEqual(created, unit.return_value)

    @patch(MODULE + '.shutil')
    @patch(MODULE + '.mkdir')
    @patch('os.path.exists')
    def test_migrate(self, path_exists, mkdir, shutil):
        unit_id = '123'
        path = '/tmp/old/path_1'
        new_path = '/tmp/new/content/path_2'
        path_exists.return_value = True

        # test
        plan = Plan(Mock(), tuple(), False)
        plan.migrate(unit_id, path, new_path)

        # validation
        path_exists.assert_called_once_with(path)
        mkdir.assert_called_once_with(os.path.dirname(new_path))
        shutil.move.assert_called_once_with(path, new_path)
        plan.collection.update_one.assert_called_once_with(
            filter={'_id': unit_id},
            update={'$set': {'_storage_path': new_path}})

    @patch(MODULE + '.Plan._new_unit')
    @patch(MODULE + '.Plan._new_path')
    def test_iter(self, new_path, new_unit):
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
        new_unit.side_effect = units
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
            new_unit.call_args_list,
            [
                call(d) for d in documents
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
        self.assertEqual(unit.files, tuple())

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
