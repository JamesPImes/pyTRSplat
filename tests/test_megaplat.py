import unittest
from pathlib import Path
from PIL import Image
from shutil import rmtree

import pytest

try:
    from pytrsplat import MegaPlat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        get_expected_subdir,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_megaplats import FILENAME_TO_GENFUNC
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import MegaPlat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        get_expected_subdir,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_megaplats import FILENAME_TO_GENFUNC

EXPECTED_DIR: Path = RESOURCES_DIR / 'expected_images' / 'megaplat' / get_expected_subdir()
OUT_DIR: Path = TEST_RESULTS_DIR / 'megaplat'
OUTPUT_TEST_OUT_DIR: Path = OUT_DIR / 'megaplat_output'

if OUT_DIR.exists():
    rmtree(OUT_DIR)
else:
    OUT_DIR.mkdir(exist_ok=True, parents=True)

if OUTPUT_TEST_OUT_DIR.exists():
    rmtree(OUTPUT_TEST_OUT_DIR)
else:
    OUTPUT_TEST_OUT_DIR.mkdir(exist_ok=True, parents=True)

DESC_1 = 'T154N-R97W Sec 14: NE/4'
DESC_2 = 'T154N-R97W Sec 8: Lot 4'
DESC_3 = 'T153N-R96W Sec 9: S/2'


class TestMegaPlatBehavior(unittest.TestCase):
    OUT_DIR: Path = TEST_RESULTS_DIR / 'megaplat'

    def test_init(self):
        megaplat = MegaPlat()
        self.assertTrue(len(megaplat.queue) == 0)

    def test_save_output(self):
        settings = Settings.preset('megaplat_default')
        mp = MegaPlat(settings=settings)
        mp.add_description(DESC_1)
        mp.add_description(DESC_3)
        mp.execute_queue()
        fp = OUT_DIR / 'megaplat_test_default.png'
        returned_im = mp.output(fp)
        opened_im = Image.open(fp)
        # Output grid is 2x2 townships.
        expected_dims = (
            settings.sec_length_px * 6 * 2 + settings.body_marg_top_y * 2,
            settings.sec_length_px * 6 * 2 + settings.body_marg_top_y * 2
        )
        self.assertEqual(opened_im.size, expected_dims)
        self.assertTrue(images_match(returned_im, opened_im))

    def test_loaded_lotdefinitions(self):
        settings = get_test_settings_for_megaplat()
        plat_nodefs = MegaPlat(settings=settings)
        plat_nodefs.lot_definer.allow_defaults = True
        plat_nodefs.add_description(DESC_2)
        plat_nodefs.execute_queue()
        plat_nodefs_output = plat_nodefs.output()

        settings = get_test_settings_for_megaplat()
        plat_withdefs = MegaPlat(settings=settings)
        plat_withdefs.lot_definer.allow_defaults = True
        plat_withdefs.lot_definer.read_csv(
            RESOURCES_DIR / 'test_lot_definitions.csv')
        plat_withdefs.add_description(DESC_2)
        plat_withdefs.execute_queue()
        plat_withdefs_output = plat_withdefs.output()
        self.assertFalse(images_match(plat_nodefs_output, plat_withdefs_output))

    def test_dim_preset_default(self):
        settings = Settings.preset('megaplat_default')
        mp = MegaPlat(settings=settings)
        mp.add_description(DESC_1)
        mp.add_description(DESC_3)
        mp.execute_queue()
        im = mp.output()
        # Output grid is 2x2 townships.
        expected_dims = (
            settings.sec_length_px * 6 * 2 + settings.body_marg_top_y * 2,
            settings.sec_length_px * 6 * 2 + settings.body_marg_top_y * 2
        )
        self.assertEqual(im.size, expected_dims)

    def test_dim_preset_small(self):
        settings = Settings.preset('megaplat_s')
        mp = MegaPlat(settings=settings)
        mp.add_description(DESC_1)
        mp.add_description(DESC_3)
        mp.execute_queue()
        im = mp.output()
        # Output grid is 2x2 townships.
        expected_dims = (
            settings.sec_length_px * 6 * 2 + settings.body_marg_top_y * 2,
            settings.sec_length_px * 6 * 2 + settings.body_marg_top_y * 2
        )
        self.assertEqual(im.size, expected_dims)

    def test_write_lot_numbers(self):
        settings = get_test_settings_for_megaplat()
        settings.write_lot_numbers = False
        mp_nolots = MegaPlat(settings=settings)
        mp_nolots.lot_definer.allow_defaults = True
        mp_nolots.add_description(DESC_1)
        mp_nolots.add_description(DESC_3)
        mp_nolots.execute_queue()
        mp_nolots_output = mp_nolots.output()

        settings.write_lot_numbers = True
        mp_withlots = MegaPlat(settings=settings)
        mp_withlots.add_description(DESC_1)
        mp_withlots.lot_definer.allow_defaults = True
        mp_withlots.execute_queue()
        mp_withlots_output = mp_withlots.output()
        self.assertFalse(images_match(mp_nolots_output, mp_withlots_output))

    def test_change_rgba(self):
        settings = get_test_settings_for_megaplat()
        settings.qq_fill_rgba = (0, 0, 255, 100)
        mp_blue = MegaPlat(settings=settings)
        mp_blue.add_description(DESC_1)
        mp_blue.add_description(DESC_3)
        mp_blue.execute_queue()
        mp_blue_output = mp_blue.output()

        settings.qq_fill_rgba = (0, 255, 0, 100)
        mp_green = MegaPlat(settings=settings)
        mp_green.add_description(DESC_1)
        mp_green.add_description(DESC_3)
        mp_green.execute_queue()
        mp_green_output = mp_green.output()
        self.assertFalse(images_match(mp_green_output, mp_blue_output))

    def test_change_secfont(self):
        settings = get_test_settings_for_megaplat()
        settings.set_font('sec', typeface='Mono (Bold)')
        mp_mono = MegaPlat(settings=settings)
        mp_mono.add_description(DESC_1)
        mp_mono.add_description(DESC_3)
        mp_mono.execute_queue()
        mp_mono_output = mp_mono.output()

        settings.set_font('sec', typeface='Sans-Serif')
        mp_sans = MegaPlat(settings=settings)
        mp_sans.add_description(DESC_1)
        mp_sans.add_description(DESC_3)
        mp_sans.execute_queue()
        mp_sans_output = mp_sans.output()
        self.assertFalse(images_match(mp_mono_output, mp_sans_output))

    def test_change_headerfont(self):
        settings = get_test_settings_for_megaplat()
        settings.set_font('header', typeface='Mono (Bold)')
        mp_mono = MegaPlat(settings=settings)
        mp_mono.add_description(DESC_1)
        mp_mono.add_description(DESC_3)
        mp_mono.execute_queue()
        mp_mono_output = mp_mono.output()

        settings.set_font('header', typeface='Sans-Serif')
        mp_sans = MegaPlat(settings=settings)
        mp_sans.add_description(DESC_1)
        mp_sans.add_description(DESC_3)
        mp_sans.execute_queue()
        mp_sans_output = mp_sans.output()
        self.assertFalse(images_match(mp_mono_output, mp_sans_output))

    def test_change_lotfont(self):
        settings = get_test_settings_for_megaplat()
        settings.write_lot_numbers = True
        settings.set_font('lot', typeface='Mono (Bold)')
        mp_mono = MegaPlat(settings=settings)
        mp_mono.lot_definer.allow_defaults = True
        mp_mono.add_description(DESC_1)
        mp_mono.add_description(DESC_3)
        mp_mono.execute_queue()
        mp_mono_output = mp_mono.output()

        settings.set_font('lot', typeface='Sans-Serif')
        mp_sans = MegaPlat(settings=settings)
        mp_sans.lot_definer.allow_defaults = True
        mp_sans.add_description(DESC_1)
        mp_sans.add_description(DESC_3)
        mp_sans.execute_queue()
        mp_sans_output = mp_sans.output()
        self.assertFalse(images_match(mp_mono_output, mp_sans_output))

    def test_find_undefined_lots(self):
        mega = MegaPlat()
        mega.add_description(DESC_2)
        undef = mega.find_undefined_lots()
        self.assertEqual(len(undef), 1)
        for trs, lots in undef.items():
            self.assertEqual('154n97w08', trs)
            self.assertEqual(['L4'], lots)

    def test_find_unplattable_tracts_yes(self):
        mega = MegaPlat()
        mega.add_description(DESC_1)
        mega.add_description(DESC_2)
        unplattable = mega.find_unplattable_tracts()
        self.assertEqual(len(unplattable), 1)
        for tract in unplattable:
            self.assertEqual('154n97w08', tract.trs)
            self.assertEqual(['L4'], tract.lots)

    def test_find_unplattable_tracts_no(self):
        mega = MegaPlat()
        mega.add_description(DESC_1)
        unplattable = mega.find_unplattable_tracts()
        self.assertEqual(len(unplattable), 0)


class TestMegaPlatOutput:

    @pytest.mark.parametrize(
        "fn,gen_func",
        [(fn, gen_func) for fn, gen_func in FILENAME_TO_GENFUNC.items()]
    )
    def test_megaplat_output(self, fn, gen_func):
        """
        Generate test megaplats, and compare their outputs against expected
        results.
        """
        expected_fp = EXPECTED_DIR / fn
        gen_fp = gen_func(fn=fn, out_dir=OUTPUT_TEST_OUT_DIR, override=True)
        try:
            expected = Image.open(expected_fp)
            generated = Image.open(gen_fp)
        except FileNotFoundError:
            expected = None
            generated = None
        explanation = gen_func.__doc__
        assert images_match(expected, generated), explanation


if __name__ == '__main__':
    prepare_settings()
    unittest.main()
