import unittest
import platform
from pathlib import Path
from PIL import Image
from shutil import rmtree

import pytest

try:
    from pytrsplat import Plat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        get_expected_subdir,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_plats import FILENAME_TO_GENFUNC
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Plat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        get_expected_subdir,
        images_match,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_plats import FILENAME_TO_GENFUNC

EXPECTED_DIR: Path = RESOURCES_DIR / 'expected_images' / 'plat' / get_expected_subdir()
OUT_DIR: Path = TEST_RESULTS_DIR / 'plat'
OUTPUT_TEST_OUT_DIR: Path = OUT_DIR / 'plat_output'

if OUT_DIR.exists():
    rmtree(OUT_DIR)
OUT_DIR.mkdir(exist_ok=True, parents=True)

if OUTPUT_TEST_OUT_DIR.exists():
    rmtree(OUTPUT_TEST_OUT_DIR)
OUTPUT_TEST_OUT_DIR.mkdir(exist_ok=True, parents=True)

DESC_1 = 'T154N-R97W Sec 14: NE/4'
DESC_2 = 'T154N-R97W Sec 8: Lot 4'

LOREM_IPSUM_LINES = [
    """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin euismod a 
    est sit amet tincidunt. Proin ligula nulla, pellentesque ac velit placerat, 
    vestibulum blandit velit. In mollis eros ac mauris luctus, vel tristique 
    augue facilisis. Integer vulputate tempor ex, in eleifend lacus commodo ac. 
    Fusce tristique nec quam quis scelerisque. Aenean tristique porta commodo. 
    Integer ut felis eu lorem eleifend fermentum. Donec ultrices tristique 
    neque, at tempor ligula congue et. Vivamus in tincidunt mi, id finibus enim.
    Nullam vestibulum viverra pretium. Sed risus purus, finibus vitae sodales
    eget, pretium ac leo. Nunc luctus quis nisi eu viverra. Duis sollicitudin
    quam ac ipsum cursus, ac blandit magna ullamcorper.""",

    """Duis eu lacinia diam. Praesent non velit posuere, ullamcorper est in,
    varius elit. Sed et nisi ac leo ullamcorper blandit. Lorem ipsum dolor sit
    amet, consectetur adipiscing elit. Suspendisse potenti. Mauris dolor metus,
    vestibulum et rutrum at, ornare sed felis. Mauris eget ante id est tempor 
    sollicitudin. Vivamus in tristique arcu. Cras ut aliquet ipsum. In accumsan 
    fringilla leo, sed blandit enim dapibus ac. Donec mattis ipsum vel rutrum 
    fermentum. Aliquam tempor sodales porta. In consectetur iaculis magna, id 
    commodo quam tempor at.""",

    """Etiam vitae leo est. Praesent lacinia in velit in malesuada. Curabitur 
    aliquam sem tincidunt feugiat auctor. Etiam finibus elit rutrum, elementum 
    lacus ac, semper ex. Sed et risus vitae erat accumsan aliquet. Donec 
    porttitor luctus placerat. Donec in luctus eros. Etiam convallis magna vel 
    porttitor volutpat. Aliquam mauris velit, venenatis sit amet tortor eu, 
    eleifend aliquet erat. Aliquam lacinia augue id pulvinar efficitur.""",

    """Pellentesque habitant morbi tristique senectus et netus et malesuada 
    fames ac turpis egestas. Etiam a arcu nec ipsum facilisis feugiat. Nulla 
    quis malesuada felis, in porta eros. Phasellus viverra tempus sapien, a 
    scelerisque orci tempus ac. Duis molestie lobortis pulvinar. Vivamus est 
    quam, auctor ut ante mattis, convallis sollicitudin arcu. Vestibulum 
    bibendum, risus eu condimentum hendrerit, sem nibh bibendum diam, non 
    pharetra urna purus eu tellus. Interdum et malesuada fames ac ante ipsum 
    primis in faucibus. Ut ipsum mi, ullamcorper vel purus eu, sollicitudin 
    consectetur felis. Cras in commodo erat. Vestibulum aliquam felis ut nunc 
    sodales elementum ut ut elit. Aliquam et enim sed lacus vulputate molestie. 
    In dolor nulla, porttitor eget ultrices vel, auctor at massa. Nulla 
    bibendum, felis sed sodales accumsan, lacus magna vestibulum mi, ut posuere 
    nibh eros eu sapien. Fusce sit amet metus nec urna ultricies bibendum.""",

    """Aenean sit amet elit purus. Praesent eget quam non ligula gravida 
    ultrices in at nulla. Praesent aliquam tellus nisl, a eleifend ligula luctus
    et. Nulla eget mauris imperdiet, dictum mauris quis, mattis lacus. Donec
    iaculis vel nibh non accumsan. Vestibulum aliquet iaculis odio. Maecenas
    eget nunc nisi. Suspendisse ut arcu tincidunt, varius eros sit amet, ornare
    ex. Orci varius natoque penatibus et magnis dis parturient montes, nascetur
    ridiculus mus.""",
]


class TestPlatBehavior(unittest.TestCase):

    def test_init(self):
        plat = Plat('154n', '97w')
        self.assertEqual(plat.twp, '154n')
        self.assertEqual(plat.rge, '97w')

    def test_save_output(self):
        settings = Settings.preset('square_s')
        plat = Plat(settings=settings)
        plat.add_description(DESC_1)
        plat.execute_queue()
        fp = OUT_DIR / 'plat_test_square_s.png'
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

    def test_write_footer_text_nopartial(self):
        """
        Test ``.write_footer_text()`` with default behavior (i.e.,
        ``write_partial=False``).
        """
        plat = Plat(settings=Settings.preset('letter'))
        plat.settings.write_tracts = False
        plat.add_description("T154N-R97W Sec 14: NE/4")
        plat.execute_queue()
        # Handle platform-specific font rendering.
        expected_linux = {
            0: None,
            1: None,
            2: None,
            3: LOREM_IPSUM_LINES[3],
            4: None,
        }
        expected_winmac = {
            0: None,
            1: None,
            2: None,
            3: LOREM_IPSUM_LINES[3],
            4: LOREM_IPSUM_LINES[4],
        }
        expected = expected_linux
        if platform.system() in ('Windows', 'Darwin'):
            expected = expected_winmac
        for i, line in enumerate(LOREM_IPSUM_LINES):
            # write_partial = False is default behavior.
            unwritten_txt = plat.write_footer_text(line)
            assert unwritten_txt == expected[i]

    def test_write_footer_text_partial(self):
        """Test ``.write_footer_text(..., write_partial=True)``"""
        plat = Plat(settings=Settings.preset('letter'))
        plat.settings.write_tracts = False
        plat.add_description("T154N-R97W Sec 14: NE/4")
        plat.execute_queue()
        # Handle platform-specific font rendering.
        expected_unwrit_wordcount_linux = {
            0: 0,
            1: 0,
            2: 0,
            3: 72,
            4: 69,
        }
        expected_unwrit_wordcount_winmac = {
            0: 0,
            1: 0,
            2: 0,
            3: 90,
            4: 69,
        }
        expected_unwrit_wordcount = expected_unwrit_wordcount_linux
        if platform.system() in ('Windows', 'Darwin'):
            expected_unwrit_wordcount = expected_unwrit_wordcount_winmac
        for i, line in enumerate(LOREM_IPSUM_LINES):
            unwritten_txt = plat.write_footer_text(line, write_partial=True)
            unwrit_wordcount = 0
            if unwritten_txt is not None:
                unwrit_wordcount = len(unwritten_txt.split())
            assert unwrit_wordcount == expected_unwrit_wordcount[i]

    def test_find_undefined_lots(self):
        plat = Plat()
        plat.add_description(DESC_2)
        undef = plat.find_undefined_lots()
        self.assertEqual(len(undef), 1)
        for trs, lots in undef.items():
            self.assertEqual('154n97w08', trs)
            self.assertEqual(['L4'], lots)

    def test_find_unplattable_tracts_yes(self):
        plat = Plat()
        plat.add_description(DESC_1)
        plat.add_description(DESC_2)
        unplattable = plat.find_unplattable_tracts()
        self.assertEqual(len(unplattable), 1)
        for tract in unplattable:
            self.assertEqual('154n97w08', tract.trs)
            self.assertEqual(['L4'], tract.lots)

    def test_find_unplattable_tracts_no(self):
        plat = Plat()
        plat.add_description(DESC_1)
        unplattable = plat.find_unplattable_tracts()
        self.assertEqual(len(unplattable), 0)


class TestPlatOutput:

    @pytest.mark.parametrize(
        "fn,gen_func",
        [(fn, gen_func) for fn, gen_func in FILENAME_TO_GENFUNC.items()]
    )
    def test_plat_output(self, fn, gen_func):
        """
        Generate test plats, and compare their outputs against expected results.
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
