import unittest
import os
from pathlib import Path

try:
    from pytrsplat import LotDefiner
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import LotDefiner

RESOURCE_DIR = Path(r"_resources")
TEST_RESULTS_DIR = Path(r"_temp")

class LotDefinerTests(unittest.TestCase):

    csv_fp: Path = RESOURCE_DIR / 'test_lot_definitions.csv'
    out_dir: Path = TEST_RESULTS_DIR / 'lot_definer'

    @classmethod
    def _delete_temp(cls):
        try:
            os.unlink(cls.out_dir)
        except FileNotFoundError:
            pass
        except PermissionError:
            pass

    @classmethod
    def setUpClass(cls):
        cls._delete_temp()
        cls.out_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls._delete_temp()

    def test_init(self):
        ld1 = LotDefiner()
        self.assertEqual(ld1.allow_defaults, False)
        self.assertEqual(ld1.standard_lot_size, 40)

        ld2 = LotDefiner(allow_defaults=True, standard_lot_size=80)
        self.assertEqual(ld2.allow_defaults, True)
        self.assertEqual(ld2.standard_lot_size, 80)

    def test_from_csv(self):
        ld = LotDefiner.from_csv(self.csv_fp)
        self.assertEqual(len(ld.definitions.keys()), 2)
        self.assertTrue(ld.definitions.get('154n97w08', None) is not None)
        self.assertTrue(ld.definitions.get('12s58e14', None) is not None)

    def test_read_csv(self):
        ld = LotDefiner()
        ld.define_lot('154n97w07', 1, 'NENE')
        self.assertEqual(len(ld.definitions.keys()), 1)
        ld.read_csv(self.csv_fp)
        self.assertTrue(ld.definitions.get('154n97w07', None) is not None)
        self.assertTrue(ld.definitions.get('154n97w08', None) is not None)
        self.assertTrue(ld.definitions.get('12s58e14', None) is not None)
        self.assertEqual(len(ld.definitions.keys()), 3)

    def test_save_to_csv(self):
        ld_orig = LotDefiner.from_csv(self.csv_fp)
        out_fp = TEST_RESULTS_DIR / 'saved_lot_definitions.csv'
        # Save to temp, then reload it.
        ld_orig.save_to_csv(out_fp)
        ld_reloaded = LotDefiner.from_csv(out_fp)
        self.assertEqual(
            len(ld_reloaded.definitions.keys()), len(ld_orig.definitions.keys()))
        self.assertTrue(ld_reloaded.definitions.get('154n97w08', None) is not None)
        self.assertTrue(ld_reloaded.definitions.get('12s58e14', None) is not None)
        self.assertEqual(ld_reloaded.definitions, ld_orig.definitions)

    def test_define_lot(self):
        ld = LotDefiner()
        ld.define_lot('154n97w11', 1, 'NENE')
        ld.define_lot('154n97w11', 'L2', 'NWNE')
        self.assertEqual(len(ld.definitions.keys()), 1)
        sec_def = ld.definitions['154n97w11']
        self.assertEqual(sec_def['L1'], 'NENE')
        self.assertEqual(sec_def['L2'], 'NWNE')


if __name__ == '__main__':
    unittest.main()
