import unittest
import os
from pathlib import Path

import pytrs

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

    def test_defaults_40ac(self):
        ld = LotDefiner(allow_defaults=True, standard_lot_size=40)
        defaults = ld.defaults('154n', '97w')
        self.assertEqual(len(defaults.keys()), 11)
        expected = {
            '154n97w01',
            '154n97w02',
            '154n97w03',
            '154n97w04',
            '154n97w05',
            '154n97w06',
            '154n97w07',
            '154n97w18',
            '154n97w19',
            '154n97w30',
            '154n97w31',
        }
        self.assertEqual(set(defaults.keys()), expected)
        expected_defs = {
            (1, 2, 3, 4, 5): LotDefiner.DEF_01_THRU_05_40AC,
            (6,): LotDefiner.DEF_06_40AC,
            (7, 18, 19, 30, 31): LotDefiner.DEF_07_18_19_30_31_40AC,
        }
        for group, defs in expected_defs.items():
            for sec_num in group:
                self.assertEqual(
                    defs,
                    defaults[f"154n97w{str(sec_num).rjust(2, '0')}"]
                )

    def test_defaults_80ac(self):
        ld = LotDefiner(allow_defaults=True, standard_lot_size=80)
        defaults = ld.defaults('154n', '97w')
        self.assertEqual(len(defaults.keys()), 11)
        expected = {
            '154n97w01',
            '154n97w02',
            '154n97w03',
            '154n97w04',
            '154n97w05',
            '154n97w06',
            '154n97w07',
            '154n97w18',
            '154n97w19',
            '154n97w30',
            '154n97w31',
        }
        self.assertEqual(set(defaults.keys()), expected)
        expected_defs = {
            (1, 2, 3, 4, 5): LotDefiner.DEF_01_THRU_05_80AC,
            (6,): LotDefiner.DEF_06_80AC,
            (7, 18, 19, 30, 31): LotDefiner.DEF_07_18_19_30_31_80AC,
        }
        for group, defs in expected_defs.items():
            for sec_num in group:
                self.assertEqual(
                    defs,
                    defaults[f"154n97w{str(sec_num).rjust(2, '0')}"]
                )

    def test_convert_lots(self):
        # Row 1 of csv file:  154n,97w,8,4,S2SE
        ld = LotDefiner.from_csv(self.csv_fp)
        lots = ['L4', 'L5']
        trs = '154n97w08'
        converted, undefined = ld.convert_lots(lots, trs)
        self.assertEqual(converted, ['SESE', 'SWSE'])
        self.assertEqual(undefined, ['L5'])

    def test_convert_lots_allow_defaults(self):
        ld = LotDefiner.from_csv(self.csv_fp, allow_defaults=True, standard_lot_size=40)
        lots = ['L1', 'L5']
        trs = '154n97w01'
        converted, undefined = ld.convert_lots(lots, trs)
        self.assertEqual(converted, ['NENE'])
        self.assertEqual(undefined, ['L5'])

    def test_find_undefined_lots(self):
        ld = LotDefiner.from_csv(self.csv_fp, allow_defaults=True, standard_lot_size=40)
        plss = pytrs.PLSSDesc('T154N-R97W Sec 1: Lots 1, 5', parse_qq=True)
        undefined = ld.find_undefined_lots(plss.tracts)
        self.assertEqual(undefined, {'154n97w01': ['L5']})

    def test_get_all_definitions(self):
        ld = LotDefiner.from_csv(self.csv_fp, allow_defaults=True, standard_lot_size=40)
        all_definitions = ld.get_all_definitions(mandatory_twprges=['12n34w'])
        # Check actually defined lots.
        self.assertEqual(all_definitions['154n97w08'], {'L4': 'S2SE'})
        self.assertEqual(all_definitions['12s58e14'], {'L1': 'SWSE'})
        # Check defaults in existing twprges + mandated twprges.
        expected_defs = {
            (1, 2, 3, 4, 5): LotDefiner.DEF_01_THRU_05_40AC,
            (6,): LotDefiner.DEF_06_40AC,
            (7, 18, 19, 30, 31): LotDefiner.DEF_07_18_19_30_31_40AC,
        }
        for group, defs in expected_defs.items():
            for twprge in ('154n97w', '12s58e', '12n34w'):
                for sec_num in group:
                    trs = f"{twprge}{str(sec_num).rjust(2, '0')}"
                    self.assertEqual(
                        defs,
                        all_definitions[trs]
                )

    def test_process_tract(self):
        tract = pytrs.Tract('Lots 1, 5', '154n97w01', parse_qq=True)
        ld = LotDefiner(allow_defaults=True, standard_lot_size=40)

        converted, undefined = ld.process_tract(tract, commit=False)
        self.assertEqual(converted, ['NENE'])
        self.assertEqual(undefined, ['L5'])
        # Ad-hoc attributes NOT added with `commit=False`.
        self.assertFalse(hasattr(tract, 'lots_as_qqs'))
        self.assertFalse(hasattr(tract, 'undefined_lots'))

        converted, undefined = ld.process_tract(tract, commit=True)
        self.assertEqual(converted, ['NENE'])
        self.assertEqual(undefined, ['L5'])
        # Check ad-hoc attributes, added with `commit=True`.
        self.assertEqual(tract.lots_as_qqs, ['NENE'])
        self.assertEqual(tract.undefined_lots, ['L5'])


if __name__ == '__main__':
    unittest.main()
