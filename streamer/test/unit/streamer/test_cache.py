from unittest import TestCase

from mock import Mock, patch

from pulp.streamer.cache import Cache, Item, NotCached

MODULE = 'pulp.streamer.cache'


class TestCache(TestCase):

    def test_basic_operation(self):
        t1 = Mock()
        t2 = Mock()
        cache = Cache()
        cache.add('t1', t1)
        cache.add('t2', t2)
        for n in range(10):
            self.assertEqual(t1, cache.get('t1'))
        for n in range(10):
            self.assertEqual(t2, cache.get('t2'))

    @patch(MODULE + '.Item.now')
    def test_add(self, now):
        t1 = Mock()
        cache = Cache()
        cache.add('t1', t1)
        item = cache._inventory['t1']
        self.assertEqual(item.object, t1)
        self.assertEqual(item.ref_count, 1)
        self.assertEqual(item.last_requested, now.return_value)

    def test_purge(self):
        t1 = Mock()
        cache = Cache()
        cache.add('t1', t1)
        self.assertTrue('t1' in cache._inventory)
        cache.purge('t1')
        self.assertFalse('t1' in cache._inventory)

    @patch(MODULE + '.Item.now')
    def test_get(self, now):
        t1 = Mock()
        now.side_effect = [1, 2, 3]
        key = 't1'
        cache = Cache()
        cache.add(key, t1)
        gotten = cache.get(key)
        self.assertEqual(cache._inventory[key].last_requested, 2)
        self.assertEqual(gotten, t1)
        self.assertRaises(NotCached, cache.get, 'xx')

    @patch(MODULE + '.Item.now')
    def test_evict(self, now):
        now.side_effect = [1, 2, 3, 4]
        key = 't1'
        cache = Cache(3)
        cache.add(key, Mock(key=key))
        evicted = cache.evict()
        self.assertTrue('t1' in cache)
        self.assertEqual(evicted, [])
        evicted = cache.evict()
        self.assertTrue('t1' in cache)
        self.assertEqual(evicted, [])
        evicted = cache.evict()
        self.assertFalse('t1' in cache)
        self.assertEqual([obj.key for obj in evicted], [key])

    @patch(MODULE + '.Item.now')
    def test_evict_busy(self, now):
        now.side_effect = [1, 2, 3, 4]
        key = 't1'
        t1 = Mock()  # hold ref to make it busy.
        cache = Cache(0)
        cache.add(key, t1)
        cache.evict()
        self.assertTrue('t1' in cache)


class TestItem(TestCase):

    @patch(MODULE + '.datetime')
    def test_now(self, dt):
        self.assertEqual(Item.now(), dt.utcnow.return_value)

    @patch(MODULE + '.Item.now')
    def test_init(self, now):
        t1 = Mock()
        item = Item(t1)
        self.assertEqual(item.object, t1)
        self.assertEqual(item.last_requested, now.return_value)

    def test_ref_count_and_busy(self):
        item = Item(Mock())
        self.assertEqual(item.ref_count, 0)
        self.assertFalse(item.busy)
        t1 = Mock()
        item = Item(t1)
        self.assertEqual(item.ref_count, 1)
        self.assertTrue(item.busy)
        del t1
        self.assertEqual(item.ref_count, 0)
        self.assertFalse(item.busy)
