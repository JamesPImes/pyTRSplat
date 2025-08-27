import unittest
from pathlib import Path
from PIL import Image

try:
    from pytrsplat import PlatGroup, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected_group,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_platgroups import (
        FILENAME_TO_GENFUNC,
    )
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import PlatGroup, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected_group,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_platgroups import (
        FILENAME_TO_GENFUNC,
    )

DESC_1 = 'T154N-R97W Sec 14: NE/4'
DESC_2 = 'T154N-R97W Sec 8: Lot 4'


class TestPlatGroupBehavior(unittest.TestCase):
    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'platgroup'
    out_dir: Path = TEST_RESULTS_DIR / 'platgroup'

    def test_init(self):
        plat_group = PlatGroup()
        self.assertTrue(len(plat_group.queue) == 0)

    def test_save_output(self):
        settings = Settings.preset('square_s')
        plat = PlatGroup(settings=settings)
        plat.add_description(DESC_1)
        plat.execute_queue()
        fp = self.out_dir / 'platgroup_test_square_s.png'
        returned_images = plat.output(fp)
        returned_im = returned_images[0]
        opened_im = Image.open(fp)
        self.assertEqual(opened_im.size, settings.dim)
        self.assertTrue(images_match(returned_im, opened_im))

    def test_loaded_lotdefinitions(self):
        settings = get_test_settings_for_plat()
        plat_nodefs = PlatGroup(settings=settings)
        plat_nodefs.lot_definer.allow_defaults = True
        plat_nodefs.add_description(DESC_2)
        plat_nodefs.execute_queue()
        plat_nodefs_output = plat_nodefs.output()

        settings = get_test_settings_for_plat()
        plat_withdefs = PlatGroup(settings=settings)
        plat_withdefs.lot_definer.allow_defaults = True
        plat_withdefs.lot_definer.read_csv(
            RESOURCES_DIR / 'test_lot_definitions.csv')
        plat_withdefs.add_description(DESC_2)
        plat_withdefs.execute_queue()
        plat_withdefs_output = plat_withdefs.output()
        self.assertFalse(images_match(plat_nodefs_output[0], plat_withdefs_output[0]))

    def test_dim_preset_default(self):
        settings = Settings.preset('letter')
        pg = PlatGroup(settings=settings)
        pg.add_description(DESC_1)
        pg.execute_queue()
        images = pg.output()
        im = images[0]
        self.assertEqual(im.size, settings.dim)

    def test_dim_preset_small(self):
        settings = Settings.preset('square_s')
        pg = PlatGroup(settings=settings)
        pg.add_description(DESC_1)
        pg.execute_queue()
        images = pg.output()
        im = images[0]
        self.assertEqual(im.size, settings.dim)

    def test_write_lot_numbers(self):
        settings = get_test_settings_for_plat()
        settings.write_lot_numbers = False
        pg_nolots = PlatGroup(settings=settings)
        pg_nolots.lot_definer.allow_defaults = True
        pg_nolots.add_description(DESC_1)
        pg_nolots.execute_queue()
        pg_nolots_output = pg_nolots.output()

        settings.write_lot_numbers = True
        pg_withlots = PlatGroup(settings=settings)
        pg_withlots.add_description(DESC_1)
        pg_withlots.lot_definer.allow_defaults = True
        pg_withlots.execute_queue()
        pg_withlots_output = pg_withlots.output()
        self.assertFalse(images_match(pg_nolots_output[0], pg_withlots_output[0]))

    def test_write_tracts(self):
        settings = get_test_settings_for_plat()
        settings.write_tracts = False
        pg_notractswritten = PlatGroup(settings=settings)
        pg_notractswritten.add_description(DESC_1)
        pg_notractswritten.execute_queue()
        pg_notractswritten_output = pg_notractswritten.output()

        settings.write_tracts = True
        pg_withtractswritten = PlatGroup(settings=settings)
        pg_withtractswritten.add_description(DESC_1)
        pg_withtractswritten.execute_queue()
        pg_withtractswritten_output = pg_withtractswritten.output()
        self.assertFalse(
            images_match(pg_notractswritten_output[0], pg_withtractswritten_output[0]))

    def test_change_rgba(self):
        settings = get_test_settings_for_plat()
        settings.qq_fill_rgba = (0, 0, 255, 100)
        pg_blue = PlatGroup(settings=settings)
        pg_blue.add_description(DESC_1)
        pg_blue.execute_queue()
        pg_blue_output = pg_blue.output()

        settings.qq_fill_rgba = (0, 255, 0, 100)
        pg_green = PlatGroup(settings=settings)
        pg_green.add_description(DESC_1)
        pg_green.execute_queue()
        pg_green_output = pg_green.output()
        self.assertFalse(images_match(pg_green_output[0], pg_blue_output[0]))

    def test_change_secfont(self):
        settings = get_test_settings_for_plat()
        settings.set_font('sec', typeface='Mono (Bold)')
        pg_mono = PlatGroup(settings=settings)
        pg_mono.add_description(DESC_1)
        pg_mono.execute_queue()
        pg_mono_output = pg_mono.output()

        settings.set_font('sec', typeface='Sans-Serif')
        pg_sans = PlatGroup(settings=settings)
        pg_sans.add_description(DESC_1)
        pg_sans.execute_queue()
        pg_sans_output = pg_sans.output()
        self.assertFalse(images_match(pg_mono_output[0], pg_sans_output[0]))

    def test_change_footerfont(self):
        settings = get_test_settings_for_plat()
        settings.write_tracts = True
        settings.set_font('footer', typeface='Mono (Bold)')
        pg_mono = PlatGroup(settings=settings)
        pg_mono.add_description(DESC_1)
        pg_mono.execute_queue()
        pg_mono_output = pg_mono.output()

        settings.set_font('footer', typeface='Sans-Serif')
        pg_sans = PlatGroup(settings=settings)
        pg_sans.add_description(DESC_1)
        pg_sans.execute_queue()
        pg_sans_output = pg_sans.output()
        self.assertFalse(images_match(pg_mono_output[0], pg_sans_output[0]))

    def test_change_headerfont(self):
        settings = get_test_settings_for_plat()
        settings.set_font('header', typeface='Mono (Bold)')
        pg_mono = PlatGroup(settings=settings)
        pg_mono.add_description(DESC_1)
        pg_mono.execute_queue()
        pg_mono_output = pg_mono.output()

        settings.set_font('header', typeface='Sans-Serif')
        pg_sans = PlatGroup(settings=settings)
        pg_sans.add_description(DESC_1)
        pg_sans.execute_queue()
        pg_sans_output = pg_sans.output()
        self.assertFalse(images_match(pg_mono_output[0], pg_sans_output[0]))

    def test_change_lotfont(self):
        settings = get_test_settings_for_plat()
        settings.write_lot_numbers = True
        settings.set_font('lot', typeface='Mono (Bold)')
        pg_mono = PlatGroup(settings=settings)
        pg_mono.lot_definer.allow_defaults = True
        pg_mono.add_description(DESC_1)
        pg_mono.execute_queue()
        pg_mono_output = pg_mono.output()

        settings.set_font('lot', typeface='Sans-Serif')
        pg_sans = PlatGroup(settings=settings)
        pg_sans.lot_definer.allow_defaults = True
        pg_sans.add_description(DESC_1)
        pg_sans.execute_queue()
        pg_sans_output = pg_sans.output()
        self.assertFalse(images_match(pg_mono_output[0], pg_sans_output[0]))


class TestPlatGroupOutput(unittest.TestCase):
    """Test the output results for PlatGroup."""

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'platgroup'
    out_dir: Path = TEST_RESULTS_DIR / 'platgroup'

    @classmethod
    def setUpClass(cls):
        prepare_settings()

    def test_matching_outputs(self):
        """
        Generate test platgroups and compare their output to expected
        results.

        (See ``_gen_test_platgroups.py`` for the inputs/settings for the
        various platgroups.)
        """
        mismatched = compare_tests_with_expected_group(
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
