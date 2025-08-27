import unittest
from pathlib import Path
from PIL import Image
from shutil import rmtree

try:
    from pytrsplat import MegaPlat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        compare_tests_with_expected,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_megaplats import (
        FILENAME_TO_GENFUNC,
    )
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import MegaPlat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        compare_tests_with_expected,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_megaplats import (
        FILENAME_TO_GENFUNC,
    )

DESC_1 = 'T154N-R97W Sec 14: NE/4'
DESC_2 = 'T154N-R97W Sec 8: Lot 4'
DESC_3 = 'T153N-R96W Sec 9: S/2'


class TestMegaPlatBehavior(unittest.TestCase):

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'megaplat'
    out_dir: Path = TEST_RESULTS_DIR / 'megaplat'

    @classmethod
    def setUpClass(cls):
        prepare_settings()
        if cls.out_dir.exists():
            rmtree(cls.out_dir)
        else:
            cls.out_dir.mkdir(exist_ok=True, parents=True)

    def test_init(self):
        megaplat = MegaPlat()
        self.assertTrue(len(megaplat.queue) == 0)

    def test_save_output(self):
        settings = Settings.preset('megaplat_default')
        mp = MegaPlat(settings=settings)
        mp.add_description(DESC_1)
        mp.add_description(DESC_3)
        mp.execute_queue()
        fp = self.out_dir / 'megaplat_test_default.png'
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


class TestMegaPlatOutput(unittest.TestCase):
    """Test the output results for MegaPlat."""

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'megaplat'
    out_dir: Path = TEST_RESULTS_DIR / 'megaplat_output'

    @classmethod
    def setUpClass(cls):
        prepare_settings()
        if cls.out_dir.exists():
            rmtree(cls.out_dir)
        else:
            cls.out_dir.mkdir(exist_ok=True, parents=True)

    def test_matching_outputs(self):
        """
        Generate test megaplats and compare their output to expected
        results.

        (See ``_gen_test_megaplats.py`` for the inputs/settings for the
        various megaplats.)
        """
        mismatched = compare_tests_with_expected(
            FILENAME_TO_GENFUNC,
            expected_dir=self.expected_dir,
            out_dir=self.out_dir,
        )
        linebreak = '\n\n'
        msg = {f"Mismatched output(s):\n{linebreak.join(mismatched)}"}
        self.assertTrue(len(mismatched) == 0, msg)
        return None


if __name__ == '__main__':
    unittest.main()
