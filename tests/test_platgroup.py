import unittest
import os
from pathlib import Path
from PIL import Image
from shutil import rmtree

import pytest

try:
    from pytrsplat import PlatGroup, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        get_expected_subdir,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_platgroups import FILENAME_TO_GENFUNC
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import PlatGroup, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        get_expected_subdir,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_platgroups import FILENAME_TO_GENFUNC

EXPECTED_DIR: Path = RESOURCES_DIR / 'expected_images' / 'platgroup' / get_expected_subdir()
OUT_DIR: Path = TEST_RESULTS_DIR / 'platgroup'
OUTPUT_TEST_OUT_DIR: Path = TEST_RESULTS_DIR / 'platgroup_output'

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


class TestPlatGroupBehavior(unittest.TestCase):

    def test_init(self):
        plat_group = PlatGroup()
        self.assertTrue(len(plat_group.queue) == 0)

    def test_save_output(self):
        settings = Settings.preset('square_s')
        plat = PlatGroup(settings=settings)
        plat.add_description(DESC_1)
        plat.execute_queue()
        fp = OUT_DIR / 'platgroup_test_square_s.png'
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
        settings = Settings.preset('default')
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


def _get_base_filename(fn: str):
    """
    Helper function to convert ``'some_plat 154n97w.png'``
    to ``'some_plat.png'``.
    """
    fn_components = fn[:-4].split(' ')
    base = fn_components[0]
    return f"{base}.png"


class TestPlatGroupOutput:
    """Test the output results for PlatGroup."""

    # Inventory existing .png files
    existing_files = [
        fn for fn in os.listdir(EXPECTED_DIR)
        if fn.lower().endswith('.png')
    ]
    # Count output files per 'base filename'.
    base_fns = {}
    for fn in existing_files:
        base_fn = _get_base_filename(fn)
        base_fns.setdefault(base_fn, 0)
        base_fns[base_fn] += 1

    @pytest.mark.parametrize(
        "fn,gen_func",
        [(fn, gen_func) for fn, gen_func in FILENAME_TO_GENFUNC.items()]
    )
    def test_platgroup_output(self, fn, gen_func):
        """
        Generate test megaplats, and compare their outputs against expected
        results.
        """
        gen_fps = gen_func(fn=fn, out_dir=OUTPUT_TEST_OUT_DIR, override=True)
        # Check correct number of images created.
        error_msg = (
            f"{fn}\n"
            f"({self.base_fns[fn]} images expected, {len(gen_fps)} generated)\n"
            f"{gen_func.__doc__}"
        )
        assert self.base_fns[fn] == len(gen_fps), error_msg

        for gen_fp in gen_fps:
            # The filename can be different than passed to `plat_gen_func`,
            # because a PlatGroup outputs multiple images when not stacked.
            # So pull the actually-generated filepath.
            gen_fp = Path(gen_fp)
            gen_fn = gen_fp.name
            expected_fp = EXPECTED_DIR / gen_fn
            try:
                expected = Image.open(expected_fp)
                generated = Image.open(gen_fp)
            except FileNotFoundError:
                expected = None
                generated = None
            explanation = gen_func.__doc__
            assert images_match(expected, generated), explanation
        return None


if __name__ == '__main__':
    prepare_settings()
    unittest.main()
