import gzip
import json
import os
import shutil
import tempfile
from unittest import TestCase

from nectar.config import DownloaderConfig
from nectar.downloaders.local import LocalFileDownloader

from pulp_node import manifest


class TestManifest(TestCase):

    NUM_UNITS = 10
    MANIFEST_ID = '123'

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def verify(self, units_out, units_in):
        self.assertEqual(len(units_out), self.NUM_UNITS)
        self.assertEqual(len(units_in), self.NUM_UNITS)
        for i in range(0, len(units_out)):
            for k, v in units_in[i].items():
                self.assertEqual(units_out[i][k], v)

    def test_validation(self):
        # Setup
        manifest_path = os.path.join(self.tmp_dir, manifest.MANIFEST_FILE_NAME)
        m = manifest.Manifest(manifest_path, self.MANIFEST_ID)
        # Test valid
        self.assertTrue(m.is_valid())
        # Test version mismatch
        m.version += 1
        self.assertFalse(m.is_valid())

    def test_publishing(self):
        # Setup
        units = []
        manifest_path = os.path.join(self.tmp_dir, manifest.MANIFEST_FILE_NAME)
        for i in range(0, self.NUM_UNITS):
            unit = dict(unit_id=i, type_id='T', unit_key={})
            units.append(unit)
        # Test
        units_path = os.path.join(self.tmp_dir, manifest.UNITS_FILE_NAME)
        writer = manifest.UnitWriter(units_path)
        for u in units:
            writer.add(u)
        writer.close()
        m = manifest.Manifest(manifest_path, self.MANIFEST_ID)
        m.units_published(writer)
        m.write()
        # Verify
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path) as fp:
            manifest_in = json.load(fp)
        self.assertEqual(m.id, manifest_in['id'])
        self.assertEqual(m.units[manifest.UNITS_TOTAL], manifest_in['units'][manifest.UNITS_TOTAL])
        self.assertEqual(m.units[manifest.UNITS_TOTAL], writer.total_units)
        self.assertEqual(m.units[manifest.UNITS_TOTAL], len(units))
        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(units_path))
        units_in = []
        fp = gzip.open(units_path)
        while True:
            json_unit = fp.readline()
            if json_unit:
                units_in.append(json.loads(json_unit))
            else:
                break
        fp.close()
        self.verify(units, units_in)

    def test_round_trip(self):
        # Setup
        units = []
        manifest_path = os.path.join(self.tmp_dir, manifest.MANIFEST_FILE_NAME)
        for i in range(0, self.NUM_UNITS):
            unit = dict(unit_id=i, type_id='T', unit_key={})
            units.append(unit)
        units_path = os.path.join(self.tmp_dir, manifest.UNITS_FILE_NAME)
        writer = manifest.UnitWriter(units_path)
        for u in units:
            writer.add(u)
        writer.close()
        m = manifest.Manifest(manifest_path, self.MANIFEST_ID)
        m.units_published(writer)
        m.write()
        # Test
        cfg = DownloaderConfig()
        downloader = LocalFileDownloader(cfg)
        working_dir = os.path.join(self.tmp_dir, 'working_dir')
        os.makedirs(working_dir)
        path = os.path.join(self.tmp_dir, manifest.MANIFEST_FILE_NAME)
        url = 'file://%s' % path
        m = manifest.RemoteManifest(url, downloader, working_dir)
        m.fetch()
        m.fetch_units()
        # Verify
        self.assertTrue(m.is_valid())
        self.assertTrue(m.has_valid_units())
        units_in = []
        for unit, ref in m.get_units():
            units_in.append(unit)
            _unit = ref.fetch()
            self.assertEqual(unit, _unit)
        self.verify(units, units_in)
        # should already be unzipped
        self.assertTrue(m.is_valid())
        self.assertTrue(m.has_valid_units())
        self.assertFalse(m.units_path().endswith('.gz'))
        units_in = []
        for unit, ref in m.get_units():
            units_in.append(unit)
            _unit = ref.fetch()
            self.assertEqual(unit, _unit)
        self.verify(units, units_in)
