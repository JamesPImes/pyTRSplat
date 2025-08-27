import unittest
from pathlib import Path
from PIL import Image
from shutil import rmtree

try:
    from pytrsplat import Plat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_plats import (
        FILENAME_TO_GENFUNC,
    )
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Plat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_plats import (
        FILENAME_TO_GENFUNC,
    )

DESC_1 = 'T154N-R97W Sec 14: NE/4'
DESC_2 = 'T154N-R97W Sec 8: Lot 4'


class TestPlatBehavior(unittest.TestCase):

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'plat'
    out_dir: Path = TEST_RESULTS_DIR / 'plat'

    @classmethod
    def setUpClass(cls):
        prepare_settings()
        if cls.out_dir.exists():
            rmtree(cls.out_dir)
        else:
            cls.out_dir.mkdir(exist_ok=True, parents=True)

    def test_init(self):
        plat = Plat('154n', '97w')
        self.assertEqual(plat.twp, '154n')
        self.assertEqual(plat.rge, '97w')

    def test_save_output(self):
        settings = Settings.preset('square_s')
        plat = Plat(settings=settings)
        plat.add_description(DESC_1)
        plat.execute_queue()
        fp = self.out_dir / 'plat_test_square_s.png'
        returned_im = plat.output(fp)
        opened_im = Image.open(fp)
        self.assertEqual(opened_im.size, settings.dim)
        self.assertTrue(images_match(returned_im, opened_im))

    def test_loaded_lotdefinitions(self):
        settings = get_test_settings_for_plat()
        plat_nodefs = Plat(settings=settings)
        plat_nodefs.lot_definer.allow_defaults = True
        plat_nodefs.add_description(DESC_2)
        plat_nodefs.execute_queue()
        plat_nodefs_output = plat_nodefs.output()

        settings = get_test_settings_for_plat()
        plat_withdefs = Plat(settings=settings)
        plat_withdefs.lot_definer.allow_defaults = True
        plat_withdefs.lot_definer.read_csv(
            RESOURCES_DIR / 'test_lot_definitions.csv')
        plat_withdefs.add_description(DESC_2)
        plat_withdefs.execute_queue()
        plat_withdefs_output = plat_withdefs.output()
        self.assertFalse(images_match(plat_nodefs_output, plat_withdefs_output))

    def test_dim_preset_default(self):
        settings = Settings.preset('default')
        plat = Plat(settings=settings)
        plat.add_description(DESC_1)
        plat.execute_queue()
        im = plat.output()
        self.assertEqual(im.size, settings.dim)

    def test_dim_preset_small(self):
        settings = Settings.preset('square_s')
        plat = Plat(settings=settings)
        plat.add_description(DESC_1)
        plat.execute_queue()
        im = plat.output()
        self.assertEqual(im.size, settings.dim)

    def test_write_lot_numbers(self):
        settings = get_test_settings_for_plat()
        settings.write_lot_numbers = False
        plat_nolots = Plat(settings=settings)
        plat_nolots.lot_definer.allow_defaults = True
        plat_nolots.add_description(DESC_1)
        plat_nolots.execute_queue()
        plat_nolots_output = plat_nolots.output()

        settings.write_lot_numbers = True
        plat_withlots = Plat(settings=settings)
        plat_withlots.add_description(DESC_1)
        plat_withlots.lot_definer.allow_defaults = True
        plat_withlots.execute_queue()
        plat_withlots_output = plat_withlots.output()
        self.assertFalse(images_match(plat_nolots_output, plat_withlots_output))

    def test_write_tracts(self):
        settings = get_test_settings_for_plat()
        settings.write_tracts = False
        plat_notractswritten = Plat(settings=settings)
        plat_notractswritten.add_description(DESC_1)
        plat_notractswritten.execute_queue()
        plat_notractswritten_output = plat_notractswritten.output()

        settings.write_tracts = True
        plat_withtractswritten = Plat(settings=settings)
        plat_withtractswritten.add_description(DESC_1)
        plat_withtractswritten.execute_queue()
        plat_withtractswritten_output = plat_withtractswritten.output()
        self.assertFalse(
            images_match(plat_notractswritten_output, plat_withtractswritten_output))

    def test_change_rgba(self):
        settings = get_test_settings_for_plat()
        settings.qq_fill_rgba = (0, 0, 255, 100)
        plat_blue = Plat(settings=settings)
        plat_blue.add_description(DESC_1)
        plat_blue.execute_queue()
        plat_blue_output = plat_blue.output()

        settings.qq_fill_rgba = (0, 255, 0, 100)
        plat_green = Plat(settings=settings)
        plat_green.add_description(DESC_1)
        plat_green.execute_queue()
        plat_green_output = plat_green.output()
        self.assertFalse(images_match(plat_green_output, plat_blue_output))

    def test_change_secfont(self):
        settings = get_test_settings_for_plat()
        settings.set_font('sec', typeface='Mono (Bold)')
        plat_mono = Plat(settings=settings)
        plat_mono.add_description(DESC_1)
        plat_mono.execute_queue()
        plat_mono_output = plat_mono.output()

        settings.set_font('sec', typeface='Sans-Serif')
        plat_sans = Plat(settings=settings)
        plat_sans.add_description(DESC_1)
        plat_sans.execute_queue()
        plat_sans_output = plat_sans.output()
        self.assertFalse(images_match(plat_mono_output, plat_sans_output))

    def test_change_footerfont(self):
        settings = get_test_settings_for_plat()
        settings.write_tracts = True
        settings.set_font('footer', typeface='Mono (Bold)')
        plat_mono = Plat(settings=settings)
        plat_mono.add_description(DESC_1)
        plat_mono.execute_queue()
        plat_mono_output = plat_mono.output()

        settings.set_font('footer', typeface='Sans-Serif')
        plat_sans = Plat(settings=settings)
        plat_sans.add_description(DESC_1)
        plat_sans.execute_queue()
        plat_sans_output = plat_sans.output()
        self.assertFalse(images_match(plat_mono_output, plat_sans_output))

    def test_change_headerfont(self):
        settings = get_test_settings_for_plat()
        settings.set_font('header', typeface='Mono (Bold)')
        plat_mono = Plat(settings=settings)
        plat_mono.add_description(DESC_1)
        plat_mono.execute_queue()
        plat_mono_output = plat_mono.output()

        settings.set_font('header', typeface='Sans-Serif')
        plat_sans = Plat(settings=settings)
        plat_sans.add_description(DESC_1)
        plat_sans.execute_queue()
        plat_sans_output = plat_sans.output()
        self.assertFalse(images_match(plat_mono_output, plat_sans_output))

    def test_change_lotfont(self):
        settings = get_test_settings_for_plat()
        settings.write_lot_numbers = True
        settings.set_font('lot', typeface='Mono (Bold)')
        plat_mono = Plat(settings=settings)
        plat_mono.lot_definer.allow_defaults = True
        plat_mono.add_description(DESC_1)
        plat_mono.execute_queue()
        plat_mono_output = plat_mono.output()

        settings.set_font('lot', typeface='Sans-Serif')
        plat_sans = Plat(settings=settings)
        plat_sans.lot_definer.allow_defaults = True
        plat_sans.add_description(DESC_1)
        plat_sans.execute_queue()
        plat_sans_output = plat_sans.output()
        self.assertFalse(images_match(plat_mono_output, plat_sans_output))


class TestPlatOutput(unittest.TestCase):
    """Test the output results for Plat."""

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'plat'
    out_dir: Path = TEST_RESULTS_DIR / 'plat_output'

    @classmethod
    def setUpClass(cls):
        prepare_settings()
        if cls.out_dir.exists():
            rmtree(cls.out_dir)
        else:
            cls.out_dir.mkdir(exist_ok=True, parents=True)

    def test_matching_outputs(self):
        """
        Generate test plats and compare their output to expected results.

        (See ``_gen_test_plats.py`` for the inputs/settings for the
        various plats.)
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
